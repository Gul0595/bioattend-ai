from contextlib import asynccontextmanager
import os
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from loguru import logger
from slowapi import _rate_limit_exceeded_handler, Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from prometheus_fastapi_instrumentator import Instrumentator

from app.core.config import settings
from app.core.database import init_db
from app.services.storage_service import ensure_storage_dirs

from app.api.routes import (
    auth,
    employees,
    attendance,
    departments,
    dashboard,
    geofence,
    leaves,
    password_reset,
)

# =========================
# RATE LIMITER
# =========================
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"],
)

# =========================
# LIFESPAN (STARTUP / SHUTDOWN)
# =========================
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"🚀 Starting {settings.APP_NAME} ...")

    await init_db()
    ensure_storage_dirs()

    # Redis check
    try:
        import redis
        r = redis.from_url(settings.REDIS_URL, socket_connect_timeout=3)
        r.ping()
        logger.info("✅ Redis connected")
    except Exception as e:
        logger.warning("⚠️ Redis unavailable: %s", e)

    # Face model warmup
    try:
        import asyncio, concurrent.futures

        def _warmup():
            from app.services.face_service import _get_deepface
            _get_deepface()

        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            await loop.run_in_executor(pool, _warmup)

        logger.info("✅ Face model loaded")

    except Exception as e:
        logger.warning("⚠️ Face model warmup failed: %s", e)

    logger.info("✅ DB initialised, storage ready")
    yield
    logger.info("👋 Shutting down")


# =========================
# FASTAPI APP
# =========================
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

app = FastAPI(
    title="BioAttend Ultimate",
    version="3.0.0",
    description="Production-grade Biometric Attendance System API",
)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }

    openapi_schema["security"] = [{"BearerAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# =========================
# ✅ BEARER AUTH FIX (SWAGGER)
# =========================
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }

    openapi_schema["security"] = [{"BearerAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# =========================
# MIDDLEWARES
# =========================
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# =========================
# REQUEST LOGGER
# =========================
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = round((time.time() - start) * 1000, 2)

    logger.info(f"{request.method} {request.url.path} → {response.status_code} ({duration}ms)")
    response.headers["X-Process-Time"] = str(duration)

    return response

# =========================
# METRICS
# =========================
Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

# =========================
# STATIC FILES
# =========================
if os.path.exists(settings.LOCAL_STORAGE_PATH):
    app.mount("/storage", StaticFiles(directory=settings.LOCAL_STORAGE_PATH), name="storage")

# =========================
# ROUTERS
# =========================
app.include_router(auth.router, prefix="/api/v1")
app.include_router(employees.router, prefix="/api/v1")
app.include_router(attendance.router, prefix="/api/v1")
app.include_router(departments.dept_router, prefix="/api/v1")
app.include_router(departments.shift_router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(leaves.router, prefix="/api/v1")
app.include_router(geofence.router, prefix="/api/v1")
app.include_router(password_reset.router, prefix="/api/v1")

# =========================
# HEALTH
# =========================
@app.get("/health", include_in_schema=False)
async def health():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": "3.0.0",
    }

@app.get("/", include_in_schema=False)
async def root():
    return {
        "message": f"{settings.APP_NAME} API is running",
        "docs": "/api/docs",
    }

# =========================
# GLOBAL ERROR HANDLER
# =========================
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})