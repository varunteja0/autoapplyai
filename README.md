# AutoApplyAI

A production-grade SaaS automation platform that helps users automatically apply to jobs across company career portals (Workday, Greenhouse, Lever, Taleo) with intelligent autofill and AI customization.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   React UI  │────▶│  FastAPI API  │────▶│ PostgreSQL  │
│  (Vite+TS)  │     │   (Python)    │     │  Database   │
└─────────────┘     └──────┬───────┘     └─────────────┘
                           │
                    ┌──────┴───────┐
                    │    Redis     │
                    │  (Queue)     │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ Worker:  │ │ Worker:  │ │ Worker:  │
        │  Apply   │ │  Scrape  │ │   AI     │
        │(Playwright)│ │          │ │(OpenAI)  │
        └──────────┘ └──────────┘ └──────────┘
```

## Features

- **Multi-platform support**: Workday, Greenhouse, Lever, Taleo
- **AI-powered**: Custom answers, tailored resume bullets via OpenAI
- **Queue-based processing**: Celery workers for async job application
- **Smart autofill**: Profile data auto-populates application forms
- **CAPTCHA detection**: Pauses and notifies user when CAPTCHA encountered
- **Retry logic**: Automatic retries with exponential backoff
- **Anti-detection**: Stealth browser settings, human-like delays
- **Rate limiting**: Per-user daily limits, API rate limiting
- **Multi-resume management**: Upload and manage multiple resumes
- **Real-time tracking**: Application status with detailed logs

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend API | FastAPI (Python 3.12) |
| Database | PostgreSQL 16 |
| Queue/Cache | Redis 7 |
| Task Workers | Celery |
| Browser Automation | Playwright |
| AI | OpenAI GPT-4 |
| Frontend | React 18 + TypeScript + Tailwind CSS |
| Auth | JWT (access + refresh tokens) |
| Containerization | Docker + Docker Compose |
| CI/CD | GitHub Actions |

## Project Structure

```
autoapplyai/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # API route handlers
│   │   ├── automation/       # Playwright bots per platform
│   │   │   └── platforms/    # Workday, Greenhouse, Lever, Taleo
│   │   ├── core/             # Security, rate limiting, exceptions
│   │   ├── models/           # SQLAlchemy ORM models
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   ├── services/         # Business logic layer
│   │   ├── workers/tasks/    # Celery async tasks
│   │   └── utils/            # Logging, helpers
│   ├── alembic/              # Database migrations
│   ├── tests/                # Pytest test suite
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── pages/            # Page views
│   │   ├── services/         # API client
│   │   ├── hooks/            # Auth store (Zustand)
│   │   └── types/            # TypeScript types
│   ├── Dockerfile
│   └── package.json
├── nginx/                    # Reverse proxy config
├── scripts/                  # Setup & seed scripts
├── docker-compose.yml
├── .github/workflows/ci.yml
└── .env.example
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- (Optional) OpenAI API key for AI features

### Setup

```bash
# 1. Clone the repository
cd autoapplyai

# 2. Create environment file
cp .env.example .env
# Edit .env with your configuration (especially JWT_SECRET_KEY and OPENAI_API_KEY)

# 3. Run automated setup
./scripts/setup.sh

# OR manually:
docker compose build
docker compose up -d
docker compose exec backend alembic upgrade head
```

### Access

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| API Docs (ReDoc) | http://localhost:8000/redoc |
| Flower (Celery Monitor) | http://localhost:5555 |

### Seed Test Data

```bash
docker compose exec backend python -m scripts.seed_data
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login
- `POST /api/v1/auth/refresh` - Refresh JWT token

### Users
- `GET /api/v1/users/me` - Get current user
- `PATCH /api/v1/users/me` - Update user info
- `GET /api/v1/users/me/profile` - Get autofill profile
- `PUT /api/v1/users/me/profile` - Create/update profile

### Jobs
- `POST /api/v1/jobs/` - Add job URL (auto-detects platform)
- `POST /api/v1/jobs/bulk` - Add multiple job URLs
- `GET /api/v1/jobs/` - List jobs
- `GET /api/v1/jobs/{id}` - Get job details
- `DELETE /api/v1/jobs/{id}` - Remove job

### Applications
- `POST /api/v1/applications/` - Queue application
- `GET /api/v1/applications/` - List with status filter
- `GET /api/v1/applications/stats` - Get statistics
- `GET /api/v1/applications/{id}` - Get details
- `GET /api/v1/applications/{id}/logs` - Get activity logs
- `POST /api/v1/applications/{id}/retry` - Retry failed
- `POST /api/v1/applications/{id}/cancel` - Cancel

### Resumes
- `POST /api/v1/resumes/` - Upload resume (multipart)
- `GET /api/v1/resumes/` - List resumes
- `GET /api/v1/resumes/{id}` - Get resume
- `PATCH /api/v1/resumes/{id}/default` - Set as default
- `DELETE /api/v1/resumes/{id}` - Delete resume

## Database Schema

### Tables
- **users** - User accounts with auth and rate limiting
- **user_profiles** - Autofill data (contact, professional, links, stored answers)
- **resumes** - Uploaded resume files with parsed data
- **jobs** - Job postings with platform detection
- **applications** - Application tracking with status machine
- **application_logs** - Detailed activity logs per application

### Application State Machine
```
QUEUED → IN_PROGRESS → SUBMITTED
                     → FAILED → RETRYING → (back to IN_PROGRESS)
                     → CAPTCHA_REQUIRED
         CANCELLED (from QUEUED, IN_PROGRESS)
```

## Development

### Backend (local without Docker)

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# Set environment variables
export DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/autoapplyai
export REDIS_URL=redis://localhost:6379/0

uvicorn app.main:app --reload
```

### Frontend (local)

```bash
cd frontend
npm install
npm run dev
```

### Run Tests

```bash
cd backend
pytest tests/ -v
```

## Scaling

The system is designed for 100K+ users:

- **Horizontal scaling**: Stateless API servers behind a load balancer
- **Worker scaling**: Add more Celery workers per queue (applications, scraping, ai)
- **Database**: Connection pooling, read replicas for queries
- **Queue isolation**: Separate Redis queues for different task types
- **Rate limiting**: Per-user daily limits + API rate limiting via Redis

```bash
# Scale workers
docker compose up -d --scale celery-worker=8
```

## Monitoring

- **Flower**: Celery task monitoring at `:5555`
- **Structured logging**: JSON-formatted logs via structlog
- **Sentry**: Error tracking (set `SENTRY_DSN` in `.env`)
- **Health check**: `GET /health` endpoint

## Security

- JWT authentication with access + refresh token rotation
- Bcrypt password hashing
- CORS origin restrictions
- Rate limiting (Redis-backed)
- Input validation via Pydantic
- Anti-bot detection (stealth browser, human-like behavior)
- File upload validation (type, size)
- SQL injection prevention (SQLAlchemy ORM)
- No credentials stored in plain text

## License

Proprietary - All Rights Reserved
