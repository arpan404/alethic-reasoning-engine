# Application Architecture

## Overview
ATS (Applicant Tracking System) with AI-powered agents using Google ADK, FastAPI for APIs/webhooks, and Celery for async job processing.

## Technology Stack
- **API Layer**: FastAPI + Uvicorn
- **AI Agents**: Google ADK (Agent Development Kit)
- **Task Queue**: Celery + Redis
- **Database**: PostgreSQL + SQLAlchemy 2.0
- **Vector Search**: pgvector

---

## Folder Structure

```
are/
├── api/                          # FastAPI application
│   ├── __init__.py
│   ├── main.py                   # FastAPI app initialization
│   ├── dependencies.py           # Dependency injection (DB, auth, etc.)
│   ├── middleware/               # Custom middleware
│   │   ├── __init__.py
│   │   ├── auth.py               # Authentication middleware
│   │   ├── cors.py               # CORS configuration
│   │   └── logging.py            # Request logging
│   ├── routes/                   # API endpoints
│   │   ├── __init__.py
│   │   ├── v1/                   # API version 1
│   │   │   ├── __init__.py
│   │   │   ├── applications.py   # Application endpoints
│   │   │   ├── candidates.py     # Candidate endpoints
│   │   │   ├── jobs.py           # Job endpoints
│   │   │   ├── offers.py         # Offer endpoints
│   │   │   ├── users.py          # User/auth endpoints
│   │   │   ├── webhooks.py       # Webhook handlers
│   │   │   └── agents.py         # Agent interaction endpoints
│   │   └── health.py             # Health check endpoints
│   └── schemas/                  # Pydantic models for API
│       ├── __init__.py
│       ├── requests.py           # Request schemas
│       ├── responses.py          # Response schemas
│       └── common.py             # Shared schemas
│
├── agents/                       # Google ADK agents
│   ├── __init__.py
│   ├── base.py                   # Base agent class
│   ├── registry.py               # Agent registry
│   ├── resume/                   # Resume parsing agent
│   │   ├── __init__.py
│   │   ├── agent.py              # Resume agent implementation
│   │   └── tools.py              # Resume-specific tools
│   ├── chat/                     # Chat/conversation agent
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   └── tools.py
│   ├── evaluation/               # Candidate evaluation agent
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   └── tools.py
│   ├── email/                    # Email generation agent
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   └── tools.py
│   └── screening/                # Application screening agent
│       ├── __init__.py
│       ├── agent.py
│       └── tools.py
│
├── workers/                      # Celery workers
│   ├── __init__.py
│   ├── celery_app.py             # Celery application
│   ├── celery_config.py          # Celery configuration
│   ├── worker.py                 # Worker startup
│   └── tasks/                    # Celery tasks
│       ├── __init__.py
│       ├── documents.py          # Document processing tasks
│       ├── emails.py             # Email sending tasks
│       ├── embeddings.py         # Vector embedding tasks
│       ├── evaluations.py        # AI evaluation tasks
│       ├── s3.py                 # S3 operations
│       └── webhooks.py           # Webhook delivery tasks
│
├── database/                     # Database layer
│   ├── __init__.py
│   ├── engine.py                 # SQLAlchemy engine & session
│   ├── security.py               # Audit & compliance
│   └── models/                   # SQLAlchemy models
│       ├── __init__.py
│       ├── applications.py
│       ├── candidates.py
│       ├── jobs.py
│       ├── offers.py
│       ├── users.py
│       └── ... (50+ model files)
│
├── core/                         # Core utilities & services
│   ├── __init__.py
│   ├── config.py                 # Application configuration
│   ├── security.py               # Auth, JWT, passwords
│   ├── storage/                  # File storage
│   │   ├── __init__.py
│   │   ├── s3.py                 # S3 client
│   │   └── local.py              # Local storage (dev)
│   ├── parsers/                  # Document parsers
│   │   ├── __init__.py
│   │   ├── pdf.py                # PDF parser
│   │   ├── docx.py               # Word parser
│   │   └── resume.py             # Resume parser
│   ├── integrations/             # Third-party integrations
│   │   ├── __init__.py
│   │   ├── email.py              # Email provider (SendGrid, SES)
│   │   ├── calendar.py           # Calendar (Google, Outlook)
│   │   └── zoom.py               # Video conferencing
│   └── utils/                    # Utility functions
│       ├── __init__.py
│       ├── datetime.py
│       ├── formatting.py
│       └── validators.py
│
├── tests/                        # Test suite
│   ├── __init__.py
│   ├── conftest.py               # Pytest fixtures
│   ├── unit/                     # Unit tests
│   │   ├── test_agents.py
│   │   ├── test_parsers.py
│   │   └── test_models.py
│   ├── integration/              # Integration tests
│   │   ├── test_api.py
│   │   ├── test_workers.py
│   │   └── test_database.py
│   └── fixtures/                 # Test data
│       ├── resumes/
│       └── documents/
│
├── docs/                         # Documentation
│   ├── database.md               # Database schema reference
│   ├── api.md                    # API documentation
│   ├── agents.md                 # Agent documentation
│   └── deployment.md             # Deployment guide
│
├── alembic/                      # Database migrations
│   ├── versions/
│   └── env.py
│
├── .env.example                  # Environment variables template
├── .gitignore
├── pyproject.toml                # Project dependencies
├── README.md
└── Makefile                      # Common commands
```

---

## Component Responsibilities

### 1. API Layer (`api/`)
**Purpose**: HTTP interface for all client interactions

**Key Components**:
- **main.py**: FastAPI app, middleware setup, route registration
- **dependencies.py**: Dependency injection (DB sessions, current user, etc.)
- **routes/**: REST endpoints organized by domain
- **schemas/**: Pydantic models for request/response validation

**Example Flow**:
```
Client Request → Middleware → Route Handler → Service/Agent → Response
```

---

### 2. Agents (`agents/`)
**Purpose**: AI-powered autonomous agents using Google ADK

**Key Components**:
- **base.py**: Base agent class with common functionality
- **registry.py**: Agent discovery and initialization
- **Domain agents**: Resume, Chat, Evaluation, Email, Screening

**Agent Responsibilities**:
- **Resume Agent**: Parse and extract structured data from resumes
- **Evaluation Agent**: Score and rank candidates using AI
- **Chat Agent**: Handle conversational queries about jobs/candidates
- **Email Agent**: Generate personalized email content
- **Screening Agent**: Evaluate screening questionnaire responses

**Example Agent Flow**:
```
API Request → Agent Runner → Agent Tools → Database/LLM → Response
```

---

### 3. Workers (`workers/`)
**Purpose**: Async job processing with Celery

**Key Components**:
- **celery_app.py**: Celery application initialization
- **celery_config.py**: Broker, backend, routing config
- **tasks/**: Task definitions organized by domain

**Task Categories**:
- **Document Processing**: Resume parsing, file conversion
- **Email Sending**: Bulk emails, notifications
- **Embeddings**: Vector generation for semantic search
- **Evaluations**: AI-powered candidate scoring
- **Webhooks**: Outbound webhook delivery

**Example Task Flow**:
```
API/Trigger → Celery Task → Process → Database Update → Callback
```

---

### 4. Database (`database/`)
**Purpose**: Data persistence layer

**Key Components**:
- **engine.py**: SQLAlchemy engine, session management
- **security.py**: Audit decorators, compliance mixins
- **models/**: 50+ SQLAlchemy ORM models

**Design**:
- Async SQLAlchemy 2.0
- BigInteger IDs for scale
- Comprehensive indexes (140+)
- GDPR/SOC2 compliance
- Audit trails on all changes

---

### 5. Core (`core/`)
**Purpose**: Shared utilities and business logic

**Key Components**:
- **config.py**: Pydantic settings from environment
- **security.py**: JWT, password hashing, permissions
- **storage/**: File storage abstraction (S3, local)
- **parsers/**: Document parsing utilities
- **integrations/**: Third-party service clients

---

## Data Flow Examples

### 1. Application Submission
```
1. POST /api/v1/applications
2. API validates request (Pydantic schema)
3. Store resume file (S3)
4. Create application record (DB)
5. Enqueue resume parsing task (Celery)
6. Return application ID (immediate response)

Background:
7. Resume parsing task runs (Worker)
8. Resume agent extracts data (Google ADK)
9. Update application with parsed data (DB)
10. Enqueue evaluation task (Celery)
11. Evaluation agent scores candidate (Google ADK)
12. Update application with score (DB)
13. Trigger webhook to external system (Celery)
```

### 2. Candidate Evaluation
```
1. Application received (existing record)
2. Evaluation task triggered (Celery)
3. Load job requirements (DB)
4. Load candidate data (DB)
5. Evaluation agent analyzes match (Google ADK)
   - Uses tools: get_job_requirements, calculate_match_score
6. Generate AI recommendation (LLM)
7. Store evaluation results (DB)
8. Send notification to recruiter (Email task)
```

### 3. Chat Query
```
1. POST /api/v1/agents/chat
2. Load conversation history (DB)
3. Chat agent processes query (Google ADK)
   - Uses tools: search_jobs, search_candidates, get_application_status
4. Generate response (LLM)
5. Store message in history (DB)
6. Return response to client
```

---

## Configuration

### Environment Variables

```bash
# App
APP_ENV=development
APP_NAME=kie-ats
DEBUG=true

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/ats

# Redis
REDIS_URL=redis://localhost:6379/0

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# S3
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
AWS_REGION=us-east-1
AWS_S3_BUCKET=ats-files

# Google ADK / Gemini
GOOGLE_API_KEY=xxx
GOOGLE_PROJECT_ID=xxx

# Auth
JWT_SECRET_KEY=xxx
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Email
SENDGRID_API_KEY=xxx
FROM_EMAIL=noreply@example.com

# External APIs
ZOOM_CLIENT_ID=xxx
ZOOM_CLIENT_SECRET=xxx
```

---

## Running the Application

### Development

```bash
# Install dependencies
uv sync

# Run database migrations
alembic upgrade head

# Start FastAPI server
uvicorn api.main:app --reload --port 8000

# Start Celery worker
celery -A workers.celery_app worker --loglevel=info

# Start Celery beat (scheduled tasks)
celery -A workers.celery_app beat --loglevel=info
```

### Production

```bash
# FastAPI with multiple workers
gunicorn api.main:app -w 4 -k uvicorn.workers.UvicornWorker

# Celery with concurrency
celery -A workers.celery_app worker --concurrency=4 --loglevel=warning

# Celery beat
celery -A workers.celery_app beat --loglevel=warning
```

---

## API Endpoints

### Applications
- `POST /api/v1/applications` - Submit application
- `GET /api/v1/applications/{id}` - Get application
- `PATCH /api/v1/applications/{id}` - Update status
- `GET /api/v1/applications` - List applications (with filters)

### Jobs
- `POST /api/v1/jobs` - Create job
- `GET /api/v1/jobs/{id}` - Get job details
- `PATCH /api/v1/jobs/{id}` - Update job
- `GET /api/v1/jobs` - List jobs

### Candidates
- `GET /api/v1/candidates/{id}` - Get candidate profile
- `PATCH /api/v1/candidates/{id}` - Update candidate
- `GET /api/v1/candidates` - Search candidates

### Agents
- `POST /api/v1/agents/chat` - Chat with AI agent
- `POST /api/v1/agents/evaluate` - Trigger evaluation
- `POST /api/v1/agents/parse-resume` - Parse resume

### Webhooks
- `POST /api/v1/webhooks/github` - GitHub integration
- `POST /api/v1/webhooks/linkedin` - LinkedIn integration
- `POST /api/v1/webhooks/zoom` - Zoom callbacks

---

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test types
pytest tests/unit/
pytest tests/integration/

# Run specific test file
pytest tests/unit/test_agents.py
```

---

## Deployment

### Docker Compose (Development)

```yaml
version: '3.8'
services:
  api:
    build: .
    command: uvicorn api.main:app --host 0.0.0.0 --port 8000
    ports:
      - "8000:8000"
    depends_on:
      - db
      - redis
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@db/ats
      - REDIS_URL=redis://redis:6379/0

  worker:
    build: .
    command: celery -A workers.celery_app worker --loglevel=info
    depends_on:
      - db
      - redis

  db:
    image: pgvector/pgvector:pg16
    environment:
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=ats
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

### Production (Kubernetes/Cloud Run)
- API: Cloud Run / ECS / Kubernetes
- Workers: ECS / Kubernetes
- Database: RDS PostgreSQL with pgvector
- Redis: ElastiCache / Cloud Memorystore
- Files: S3 / Cloud Storage

---

## Best Practices

### API Development
- Use Pydantic for validation
- Implement proper error handling
- Add request/response logging
- Use dependency injection
- Version your APIs

### Agent Development
- Keep agents focused on single responsibility
- Use tools for reusable functionality
- Implement proper error handling
- Add logging for debugging
- Test with mock LLM responses

### Worker Development
- Make tasks idempotent
- Use task retries for failures
- Implement timeouts
- Log task execution
- Monitor task queue length

### Database
- Always use async sessions
- Use indexes for queries
- Implement proper transactions
- Handle connection pooling
- Monitor query performance

---

**Last Updated**: January 10, 2026
