# 🔐 BioAttend Ultimate v3.0

> **The best of both worlds** — production-grade biometric attendance system combining the rich features of `bioattend-pro` with the clean async architecture of `bioattend-full-project`.

---

## ✨ What's Combined

| Feature | bioattend-pro | bioattend-full | Ultimate v3 |
|---|---|---|---|
| Async SQLAlchemy | ❌ | ✅ | ✅ |
| UUID primary keys | ❌ | ✅ | ✅ |
| TypeScript frontend | ❌ | ✅ | ✅ |
| Face Recognition (DeepFace) | ✅ | Partial | ✅ Facenet512 |
| Fingerprint support | ✅ | ❌ | ✅ |
| Face kiosk (base64) | ✅ | ❌ | ✅ |
| JWT Refresh tokens | ✅ | ❌ | ✅ |
| Rate limiting (SlowAPI) | ✅ | ❌ | ✅ |
| GZip middleware | ✅ | ❌ | ✅ |
| Prometheus metrics | ✅ | ❌ | ✅ |
| Celery + Beat scheduler | ✅ | ❌ | ✅ |
| Absent auto-marking task | ✅ | ❌ | ✅ |
| Report generation (CSV) | ✅ | ❌ | ✅ |
| Leave management | ✅ | ❌ | ✅ |
| Holiday calendar | ✅ | ❌ | ✅ |
| Audit logging model | ✅ | ❌ | ✅ |
| Employee detail page | ❌ | ✅ | ✅ |
| Department/Shift routes | ❌ | ✅ | ✅ |
| Monthly summary endpoint | ❌ | ✅ | ✅ |
| pgvector face embeddings | ❌ | ✅ | ✅ |
| MinIO storage support | ❌ | ✅ | ✅ |
| Test suite (pytest-asyncio) | ❌ | ✅ | ✅ |
| Shift overtime calculation | ✅ | ❌ | ✅ |
| Half-day detection | ✅ | ❌ | ✅ |
| Dashboard charts (Recharts) | ✅ | ❌ | ✅ |
| Settings page | ✅ | ❌ | ✅ |
| Zustand auth store | ✅ | ❌ | ✅ |
| Makefile commands | ❌ | ✅ | ✅ |

---

## 🏗 Architecture

```
bioattend-ultimate/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── dependencies.py       # JWT guards, role deps
│   │   │   └── routes/
│   │   │       ├── auth.py           # Login, refresh, change-pw
│   │   │       ├── employees.py      # CRUD + face enrollment
│   │   │       ├── attendance.py     # Face/FP check-in, manual, logs
│   │   │       ├── departments.py    # Departments + Shifts
│   │   │       └── dashboard.py      # Stats, trend, dept breakdown
│   │   ├── core/
│   │   │   ├── config.py             # Pydantic Settings v2
│   │   │   ├── database.py           # Async SQLAlchemy engine
│   │   │   └── security.py           # JWT + bcrypt
│   │   ├── models/                   # SQLAlchemy ORM (UUID PKs)
│   │   ├── schemas/                  # Pydantic v2 schemas
│   │   ├── services/
│   │   │   ├── attendance_service.py # Shift-aware check-in/out
│   │   │   ├── face_service.py       # DeepFace 1:N + 1:1
│   │   │   └── storage_service.py    # Local / S3 / MinIO
│   │   ├── workers/
│   │   │   ├── celery_app.py         # Celery + Beat config
│   │   │   └── tasks.py              # Report, absent-mark, notify
│   │   └── main.py                   # FastAPI app + middleware
│   ├── alembic/                      # Async migrations
│   ├── scripts/seed.py               # Database seeder
│   ├── tests/                        # pytest-asyncio test suite
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── DashboardPage.tsx     # Stats + Recharts
│       │   ├── EmployeesPage.tsx     # Table + CRUD modal
│       │   ├── EmployeeDetailPage.tsx# Profile + face enroll + history
│       │   ├── AttendancePage.tsx    # Filters + manual entry
│       │   ├── FaceKioskPage.tsx     # Camera + auto-scan
│       │   ├── ReportsPage.tsx       # Charts + CSV export
│       │   └── SettingsPage.tsx      # Depts, shifts, security
│       ├── services/api.ts           # Typed axios client
│       └── store/authStore.ts        # Zustand + persist
├── nginx/nginx.conf                  # Reverse proxy + rate limits
├── docker-compose.yml                # Full production stack
└── Makefile                          # Developer commands
```

---

## 🚀 Quick Start

### Prerequisites
- Docker + Docker Compose
- Git

### 1. Clone and configure
```bash
git clone <your-repo-url> bioattend-ultimate
cd bioattend-ultimate
cp backend/.env.example backend/.env
# Edit backend/.env with your values (SECRET_KEY, POSTGRES_PASSWORD, etc.)
```

### 2. Start everything
```bash
make build
make up
make migrate
make seed
```

### 3. Access
| Service | URL | Credentials |
|---|---|---|
| Frontend | http://localhost | — |
| API Docs | http://localhost:8000/api/docs | — |
| Admin Login | http://localhost | admin@bioattend.app / Admin@1234 |
| Flower (Celery) | http://localhost:5555 | admin / flowerpass |
| MinIO Console | http://localhost:9001 | minioadmin / minioadmin |
| Prometheus | http://localhost:8000/metrics | — |

---

## 🛠 Development Commands

```bash
make dev-backend     # FastAPI with hot-reload
make dev-frontend    # Vite dev server
make dev-worker      # Celery worker
make test            # Run pytest suite
make lint            # Ruff linting
make format          # Black + isort
make seed            # Populate DB
make migrate         # Apply migrations
make migrate-auto    # Auto-generate migration
make logs-backend    # Tail API logs
make health          # Check all services
```

---

## 🛡 Liveness Detection (Anti-Spoofing)

BioAttend Ultimate uses a **5-layer defense** to ensure only a real, live person can mark attendance — not a printed photo, phone screen, or recorded video.

```
Layer 1 — Blink Challenge (Frontend)
   Client captures 15 frames over 1.5s after showing "Blink now" prompt.
   → Static photos CANNOT blink
   → Pre-recorded videos cannot predict timing
   → MediaPipe facial landmarks detect Eye Aspect Ratio (EAR) dip = blink

Layer 2 — DeepFace Anti-Spoof CNN (Backend)
   Silent-Face model classifies the image as real or spoof.
   → Trained on thousands of real vs. photo/screen samples
   → Catches high-quality prints and digital screens

Layer 3 — LBP Texture Analysis (Backend)
   Laplacian variance + local block standard deviation.
   → Real skin has natural micro-texture variation
   → Printed paper/screens are unnaturally flat (variance too low)

Layer 4 — Specular Reflection Check (Backend)
   Counts bright pixel fraction + large uniform bright patches.
   → Screens create rectangular specular highlights
   → Glossy prints have unnatural reflection hotspots

Layer 5 — FFT Frequency Analysis (Backend)
   Fourier transform reveals unnatural high-frequency patterns.
   → Halftone dots in printed photos appear as FFT peaks
   → Screen pixels create regular grid artifacts

Bonus — YCrCb Skin Tone Check (Backend)
   Verifies that natural skin-tone pixels are present in expected distribution.
   → Uniform synthetic colors lack natural skin hue spread
```

### Confidence scoring
All layers produce a 0–1 score. Weighted composite:

| Layer | Weight |
|---|---|
| DeepFace CNN | 40% |
| LBP Texture | 25% |
| Specular | 15% |
| Frequency | 10% |
| Skin Tone | 10% |

**Overall threshold: 0.55** — below this, attendance is blocked regardless of face match.

### API endpoints
| Endpoint | Purpose |
|---|---|
| `POST /api/v1/attendance/face-checkin` | Full flow: liveness + face match + check-in/out |
| `POST /api/v1/attendance/blink-challenge` | Standalone blink verification (15 frames) |
| `POST /api/v1/attendance/liveness-check` | Standalone liveness score (debug/testing) |

---

## 🔐 Security Features

- **JWT** — Access tokens (60 min) + refresh tokens (30 days)
- **bcrypt** — Password hashing
- **SlowAPI** — Rate limiting: 60 req/min per IP on API, 120/min on kiosk
- **GZip** — All responses ≥ 1 KB compressed
- **Prometheus** — Metrics at `/metrics` (restricted to internal IPs via nginx)
- **Loguru** — Structured request logging with timing
- **Audit logging** — Model for all admin actions (extend as needed)
- **CORS** — Configurable via `CORS_ORIGINS` env var
- **Role-based access** — `admin`, `hr`, `manager`, `employee`, `viewer`

---

## 🤖 Face Recognition

Uses **DeepFace** with **Facenet512** model + **RetinaFace** detector.

| Setting | Default | Description |
|---|---|---|
| `FACE_MODEL` | `Facenet512` | Embedding model |
| `FACE_DETECTOR` | `retinaface` | Face detector backend |
| `FACE_DISTANCE_THRESHOLD` | `0.40` | Cosine distance match threshold |
| `MAX_FACE_IMAGE_SIZE_MB` | `5` | Max upload size |

### Kiosk flow
1. Edge device captures frame → sends base64 to `POST /api/v1/attendance/face-checkin`
2. Backend builds gallery of enrolled employees
3. 1:N match via cosine distance on 512-dim Facenet512 embeddings
4. Returns matched employee + check-in / check-out action + lateness info

---

## 💾 Storage Backends

Configure via `STORAGE_BACKEND` env var:

| Value | Config needed |
|---|---|
| `local` | `LOCAL_STORAGE_PATH` |
| `s3` | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_BUCKET_NAME` |
| `minio` | `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY` |

---

## 📦 Tech Stack

**Backend**
- FastAPI 0.111 + Uvicorn
- SQLAlchemy 2 (async) + asyncpg + Alembic
- DeepFace (Facenet512 + RetinaFace)
- Celery + Redis + Flower
- SlowAPI + Prometheus + Loguru
- Pydantic v2 + pydantic-settings

**Frontend**
- React 18 + TypeScript + Vite
- TanStack Query v5 (React Query)
- Zustand (auth store + persist)
- Recharts (dashboard charts)
- Tailwind CSS v3 + custom design tokens
- React Router v6 + react-hot-toast

**Infrastructure**
- PostgreSQL 16
- Redis 7
- MinIO (optional S3-compatible storage)
- Nginx (reverse proxy + rate limiting)
- Docker Compose

---

## 🔄 Scheduled Tasks (Celery Beat)

| Task | Schedule | Description |
|---|---|---|
| `mark_absent_employees` | 22:00 daily | Marks employees without check-in as absent |
| `send_late_notifications` | 09:00 daily | Trigger notifications for late employees |

---

## 📝 Environment Variables

See `backend/.env.example` for the full list.  
Key variables:

```env
SECRET_KEY=          # 32+ char random string — CHANGE THIS
DATABASE_URL=        # postgresql+asyncpg://...
REDIS_URL=           # redis://...
STORAGE_BACKEND=     # local | s3 | minio
FACE_MODEL=          # Facenet512 (recommended)
CORS_ORIGINS=        # Comma-separated allowed origins
```

---

## 📄 License

MIT — free to use, modify, and distribute.
