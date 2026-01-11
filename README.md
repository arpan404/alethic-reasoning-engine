# Alethic ARE - Alethic Reasoning Engine

AI-powered ATS reasoning engine built with FastAPI, Google ADK agents, and Celery for async processing.

## Tech Stack

- **API Framework**: FastAPI + Uvicorn (ASGI)
- **AI Agents**: Google ADK (Gemini 2.0)
- **Task Queue**: Celery + Redis
- **Database**: PostgreSQL + pgvector + SQLAlchemy 2.0
- **Storage**: AWS S3 (via aioboto3)
- **Auth**: JWT with python-jose

## Project Structure

```
are/
├── api/                    # FastAPI application
│   ├── routes/            # API endpoints
│   │   ├── v1/           # v1 API routes
│   │   └── health.py     # Health check
│   ├── schemas/          # Pydantic models
│   ├── middleware/       # Custom middleware
│   ├── dependencies.py   # FastAPI dependencies
│   └── main.py          # FastAPI app initialization
├── agents/               # Google ADK agents
│   ├── common/          # Shared agent utilities ✨
│   │   ├── tools.py     # Common extraction tools
│   │   ├── prompts.py   # Shared prompt templates
│   │   └── utils.py     # Utility functions
│   ├── resume/          # Resume parsing agent
│   ├── screening/       # Application screening
│   ├── evaluation/      # Candidate evaluation ✨
│   ├── chat/            # Conversational agent
│   ├── email/           # Email generation
│   ├── base.py         # Base agent class
│   └── registry.py     # Agent registry
├── workers/             # Celery workers
│   ├── tasks/          # Celery tasks
│   │   ├── documents.py   # Document processing
│   │   ├── emails.py      # Email sending
│   │   ├── embeddings.py  # Vector embeddings
│   │   ├── evaluations.py # AI evaluations
│   │   └── webhooks.py    # Webhook delivery
│   └── celery_app.py   # Celery configuration
├── core/                # Core utilities
│   ├── middleware/     # Custom middleware ✨
│   ├── storage/        # File storage abstraction
│   ├── parsers/        # Document parsers
│   ├── integrations/   # Third-party integrations
│   ├── utils/          # Utility functions
│   └── config.py       # Pydantic settings
├── database/            # Database layer
│   ├── models/         # SQLAlchemy models
│   └── engine.py       # Database engine
├── alembic/            # Database migrations
├── tests/              # Test suite ✨
│   ├── unit/          # Unit tests
│   │   ├── api/       # API tests
│   │   ├── agents/    # Agent tests
│   │   ├── workers/   # Worker tests
│   │   └── core/      # Core tests
│   └── integration/   # Integration tests
└── docs/              # Documentation ✨
    ├── ARCHITECTURE.md      # System architecture guide
    ├── FOLDER_STRUCTURE.md  # Project organization
    ├── MIGRATION_GUIDE.md   # Usage guide & examples
    └── QUICKSTART.md        # Getting started guide
```

✨ = Recently added/enhanced

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 14+ with pgvector
- Redis 6+
- AWS S3 account (or compatible service)
- Google AI API key

### Installation

1. **Clone and install dependencies:**

```bash
cd /Users/arpanbhandari/Code/koru/apps/are
poetry install
```

2. **Set up environment variables:**

```bash
cp .env.example .env
# Edit .env with your actual configuration
```

3. **Set up database:**

```bash
# Create database and extensions
createdb alethic_db
psql alethic_db -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Run migrations
make upgrade
```

4. **Start Redis:**

```bash
redis-server
```

### Running the Application

#### Option 1: Development (all services)

```bash
# Terminal 1: API server
make dev

# Terminal 2: Celery worker
make worker

# Terminal 3: (optional) Celery with beat scheduler
make celery
```

#### Option 2: Individual services

```bash
# FastAPI server (port 8000)
poetry run uvicorn api.main:app --reload

# Celery worker
poetry run celery -A workers.celery_app worker --loglevel=info

# Celery with scheduler
poetry run celery -A workers.celery_app worker --beat --loglevel=info
```

### API Documentation

Once the server is running, visit:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## Development

### Creating Database Migrations

```bash
# Auto-generate migration from model changes
make migrate message="add new field"

# Apply migrations
make upgrade

# Rollback last migration
make downgrade
```

### Running Tests

```bash
make test
```

### Code Quality

```bash
# Run linters
make lint

# Auto-format code
make format
```

## Architecture

### API Layer (FastAPI)

The API layer handles HTTP requests and responses. Key features:

- **Async/await**: All routes are async for high concurrency
- **Dependency injection**: Database sessions, auth, pagination
- **Pydantic validation**: Request/response validation
- **OpenAPI docs**: Auto-generated documentation

Example route:

```python
@router.get("/candidates", response_model=PaginatedResponse[CandidateResponse])
async def list_candidates(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_active_user),
):
    # Implementation
    pass
```

### Agent Layer (Google ADK)

AI agents powered by Google's Gemini models:

- **Resume Agent**: Parse and extract structured data from resumes
- **Screening Agent**: Evaluate candidates against job requirements
- **Evaluation Agent**: Comprehensive candidate assessment with scoring
- **Chat Agent**: Conversational interface for candidates and recruiters
- **Email Agent**: Generate professional emails and communications

**Shared Utilities** (`agents/common/`):
- Common extraction tools (email, phone, URLs)
- Shared prompt templates
- Utility functions for validation and processing

Example agent usage:

```python
from agents.registry import registry

agent = registry.get("resume")
result = await agent.process({"resume_text": text})
```

### Worker Layer (Celery)

Async task processing with Celery:

- **Document tasks**: Resume parsing, file processing
- **Email tasks**: Campaign emails, notifications
- **Embedding tasks**: Vector embedding generation
- **Evaluation tasks**: AI-powered candidate scoring
- **Webhook tasks**: Outbound webhook delivery

Example task:

```python
from workers.tasks.documents import parse_resume

# Queue task
task = parse_resume.delay(
    file_path="s3://bucket/resume.pdf",
    candidate_id="uuid",
    organization_id="uuid",
)

# Check status
result = task.get(timeout=10)
```

## Database

The database layer uses SQLAlchemy 2.0 with async support:

- **140+ indexes** for optimal query performance
- **pgvector** for semantic search with embeddings
- **Comprehensive relationships** between entities
- **Audit trail** for compliance

## Configuration

All configuration is managed through environment variables using Pydantic Settings.

Key settings (see `.env.example` for full list):

- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `GOOGLE_API_KEY`: Google AI API key
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`: S3 credentials
- `JWT_SECRET_KEY`: JWT signing key

## Documentation

For detailed information, see:

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - System architecture and deployment guide
- [docs/FOLDER_STRUCTURE.md](docs/FOLDER_STRUCTURE.md) - Project organization and best practices
- [docs/MIGRATION_GUIDE.md](docs/MIGRATION_GUIDE.md) - Usage examples and migration guide
- [docs/QUICKSTART.md](docs/QUICKSTART.md) - Quick start guide

## Deployment

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed deployment guide covering:

- Docker containerization
- Environment configuration
- Database migration strategy
- Monitoring and logging
- Scaling considerations

## API Examples

### Create Candidate

```bash
curl -X POST http://localhost:8000/api/v1/candidates \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "email": "candidate@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "resume_url": "s3://bucket/resume.pdf"
  }'
```

### Trigger Resume Parsing

```bash
curl -X POST http://localhost:8000/api/v1/candidates/{candidate_id}/parse-resume \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Screen Application

```python
from workers.tasks.evaluations import screen_application

task = screen_application.delay(application_id="uuid")
result = task.get()
```

## Contributing

1. Create a feature branch
2. Make changes with tests
3. Run linters: `make lint`
4. Format code: `make format`
5. Submit pull request

## License

Proprietary - Koru Technologies

## Support

For issues or questions, contact the development team.
