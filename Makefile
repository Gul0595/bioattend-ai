.PHONY: help up down build dev seed migrate shell logs test lint format clean

# ── Config ────────────────────────────────────────────────────────────────────
COMPOSE        = docker compose
BACKEND_SVC    = backend
FRONTEND_SVC   = frontend
WORKER_SVC     = celery_worker

## help   : Show this help
help:
	@grep -E '^## ' Makefile | sed 's/## //'

# ── Docker Lifecycle ──────────────────────────────────────────────────────────
## up     : Start all services (detached)
up:
	$(COMPOSE) up -d

## down   : Stop all services
down:
	$(COMPOSE) down

## build  : Rebuild all images
build:
	$(COMPOSE) build --no-cache

## restart: Restart backend and worker only (fast cycle)
restart:
	$(COMPOSE) restart $(BACKEND_SVC) $(WORKER_SVC)

## logs   : Tail logs from all services
logs:
	$(COMPOSE) logs -f

## logs-backend : Tail backend logs only
logs-backend:
	$(COMPOSE) logs -f $(BACKEND_SVC)

## logs-worker  : Tail celery worker logs
logs-worker:
	$(COMPOSE) logs -f $(WORKER_SVC)

# ── Database ──────────────────────────────────────────────────────────────────
## migrate    : Run Alembic migrations (inside container)
migrate:
	$(COMPOSE) exec $(BACKEND_SVC) alembic upgrade head

## migrate-auto : Auto-generate a new migration from model changes
migrate-auto:
	@read -p "Migration message: " msg; \
	$(COMPOSE) exec $(BACKEND_SVC) alembic revision --autogenerate -m "$$msg"

## migrate-down : Downgrade one revision
migrate-down:
	$(COMPOSE) exec $(BACKEND_SVC) alembic downgrade -1

## seed   : Run database seed script
seed:
	$(COMPOSE) exec $(BACKEND_SVC) python -m scripts.seed

## psql   : Connect to PostgreSQL
psql:
	$(COMPOSE) exec postgres psql -U postgres -d attendance_db

# ── Development (local, no Docker) ────────────────────────────────────────────
## dev-backend : Run FastAPI backend locally with hot-reload
dev-backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

## dev-frontend : Run Vite dev server
dev-frontend:
	cd frontend && npm run dev

## dev-worker  : Run Celery worker locally
dev-worker:
	cd backend && celery -A app.workers.celery_app worker -Q face,attendance,notifications,reports -c 2 -l info

## dev-beat    : Run Celery beat scheduler locally
dev-beat:
	cd backend && celery -A app.workers.celery_app beat -l info

# ── Install ───────────────────────────────────────────────────────────────────
## install-backend  : Install Python deps
install-backend:
	cd backend && pip install -r requirements.txt

## install-frontend : Install Node deps
install-frontend:
	cd frontend && npm install

## install : Install all deps locally
install: install-backend install-frontend

# ── Testing ───────────────────────────────────────────────────────────────────
## test   : Run backend tests
test:
	$(COMPOSE) exec $(BACKEND_SVC) pytest tests/ -v --tb=short

## test-local : Run backend tests locally
test-local:
	cd backend && pytest tests/ -v --tb=short

# ── Code Quality ──────────────────────────────────────────────────────────────
## lint   : Lint Python code (ruff)
lint:
	cd backend && ruff check app/ --fix

## format : Format Python code (black + isort)
format:
	cd backend && black app/ scripts/ && isort app/ scripts/

## type-check : Run mypy type checks
type-check:
	cd backend && mypy app/ --ignore-missing-imports

## tsc    : TypeScript type check frontend
tsc:
	cd frontend && npx tsc --noEmit

# ── Utilities ─────────────────────────────────────────────────────────────────
## shell  : Open shell in backend container
shell:
	$(COMPOSE) exec $(BACKEND_SVC) /bin/bash

## shell-db : Open Python shell with app context
shell-db:
	$(COMPOSE) exec $(BACKEND_SVC) python -c "import asyncio; from app.core.database import AsyncSessionLocal; print('Session ready')"

## clean  : Remove all containers, volumes and images (⚠ destructive)
clean:
	$(COMPOSE) down -v --remove-orphans
	docker image prune -f

## health : Check all service health
health:
	@echo "Backend:"; curl -s http://localhost:8000/health | python3 -m json.tool
	@echo "\nNginx:";  curl -sI http://localhost | head -5

## flower : Open Flower task monitor
flower:
	@echo "Flower UI: http://localhost:5555"
	@open http://localhost:5555 2>/dev/null || xdg-open http://localhost:5555 2>/dev/null || true

## docs   : Open API docs (debug mode only)
docs:
	@echo "API Docs: http://localhost:8000/api/docs"
	@open http://localhost:8000/api/docs 2>/dev/null || xdg-open http://localhost:8000/api/docs 2>/dev/null || true
