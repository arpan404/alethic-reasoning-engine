# Quick Start Guide - Koru ATS

## What We Built

Complete restructuring of Koru ATS with:
- ✅ FastAPI for REST API endpoints
- ✅ Google ADK for AI agents
- ✅ Celery for async job processing
- ✅ PostgreSQL with 140+ optimized indexes
- ✅ Comprehensive folder structure

## 5-Minute Setup

### 1. Install Dependencies

```bash
cd /Users/arpanbhandari/Code/koru/apps/are
poetry install
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with:
- PostgreSQL credentials
- Redis URL
- Google API key
- AWS S3 credentials

### 3. Setup Database

```bash
# Create database with pgvector
createdb alethic_db
psql alethic_db -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Run migrations
make upgrade
```

### 4. Start Services

**Terminal 1 - API Server:**
```bash
make dev
# Runs: uvicorn api.main:app --reload
# Visit: http://localhost:8000/docs
```

**Terminal 2 - Celery Worker:**
```bash
make worker
# Runs: celery -A workers.celery_app worker
```

**Terminal 3 - (Optional) Redis:**
```bash
redis-server
```

## Testing the Setup

### 1. Check Health

```bash
curl http://localhost:8000/health
# Expected: {"status":"healthy","version":"0.1.0"}
```

### 2. View API Docs

Open browser: http://localhost:8000/docs

### 3. Test an Agent

```python
from agents.registry import registry

# Get resume parsing agent
agent = registry.get("resume")

# Process a resume
result = await agent.process({
    "resume_text": "John Doe\nSoftware Engineer\n..."
})
```

### 4. Queue a Task

```python
from workers.tasks.documents import parse_resume

# Queue resume parsing
task = parse_resume.delay(
    file_path="s3://bucket/resume.pdf",
    candidate_id="uuid",
    organization_id="uuid",
)

# Check status
print(f"Task ID: {task.id}")
```

## Project Structure

```
are/
├── api/              # FastAPI routes, schemas, dependencies
├── agents/           # Google ADK agents (resume, screening)
├── workers/          # Celery tasks (documents, emails, etc.)
├── core/             # Config, storage, parsers, integrations
├── database/         # SQLAlchemy models with 140+ indexes
├── docs/             # Documentation
├── alembic/          # Database migrations
└── tests/            # Test files
```

## Key Files Created

### Core Application
- `api/main.py` - FastAPI app with CORS, routes, lifespan
- `core/config.py` - Pydantic Settings from environment
- `database/engine.py` - Async SQLAlchemy engine (existing, updated)

### API Layer
- `api/routes/health.py` - Health check endpoints
- `api/routes/v1/candidates.py` - Example CRUD endpoints
- `api/schemas/common.py` - Pagination, timestamps, errors
- `api/schemas/candidates.py` - Candidate request/response models
- `api/dependencies.py` - Auth and DB dependencies

### Agent Layer
- `agents/base.py` - Base agent class with Google ADK
- `agents/registry.py` - Agent discovery and management
- `agents/resume/agent.py` - Resume parsing agent
- `agents/screening/agent.py` - Application screening agent

### Worker Layer
- `workers/celery_app.py` - Celery config with 5 queues
- `workers/tasks/documents.py` - Resume parsing, file processing
- `workers/tasks/emails.py` - Email sending, campaigns
- `workers/tasks/embeddings.py` - Vector embedding generation
- `workers/tasks/evaluations.py` - AI candidate scoring
- `workers/tasks/webhooks.py` - Webhook delivery

### Documentation
- `ARCHITECTURE.md` - Complete architecture guide
- `README.md` - Project documentation
- `docs/IMPLEMENTATION_SUMMARY.md` - What we built
- `docs/database.md` - Database schema documentation
- `.env.example` - Environment variables template
- `Makefile` - Development commands

## Common Commands

```bash
# Development
make dev          # Start API server with auto-reload
make worker       # Start Celery worker
make celery       # Start Celery with beat scheduler

# Database
make migrate message="description"  # Create migration
make upgrade                        # Apply migrations
make downgrade                      # Rollback migration

# Code Quality
make test         # Run tests
make lint         # Run linters
make format       # Format code
make clean        # Clean cache files

# Manual commands
poetry install                      # Install dependencies
uvicorn api.main:app --reload      # Run API server
celery -A workers.celery_app worker # Run worker
```

## Environment Variables (Required)

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/db

# Redis (for Celery)
REDIS_URL=redis://localhost:6379/0

# Google AI
GOOGLE_API_KEY=your_api_key

# AWS S3
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
S3_BUCKET_NAME=your_bucket

# JWT
JWT_SECRET_KEY=your_secret_key

# SMTP (optional)
SMTP_HOST=smtp.gmail.com
SMTP_USER=your@email.com
SMTP_PASSWORD=your_password
```

## API Examples

### Create a Candidate

```bash
curl -X POST http://localhost:8000/api/v1/candidates \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Doe"
  }'
```

### Trigger Resume Parsing

```bash
curl -X POST http://localhost:8000/api/v1/candidates/{id}/parse-resume \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## What's Implemented

✅ Complete folder structure
✅ FastAPI app with routes
✅ Google ADK agent framework
✅ Celery task queue with 5 queues
✅ Pydantic Settings configuration
✅ Database with 140+ indexes
✅ Health check endpoints
✅ Example CRUD route (candidates)
✅ Resume and screening agents
✅ Document, email, embedding, evaluation, webhook tasks
✅ Development tooling (Makefile, .env.example)
✅ Comprehensive documentation

## What Needs Implementation

The scaffold is complete. To finish:

1. **API Routes** - Implement remaining CRUD endpoints in `api/routes/v1/`
2. **Schemas** - Complete Pydantic models in `api/schemas/`
3. **Authentication** - Implement JWT token generation/validation
4. **Agent Logic** - Complete tool implementations in `agents/*/tools.py`
5. **Task Logic** - Fill in TODO sections in `workers/tasks/*.py`
6. **Storage** - Complete S3 and local storage implementations
7. **Parsers** - Enhance document parsing logic
8. **Integrations** - Implement email, calendar, zoom services
9. **Tests** - Add comprehensive test coverage

## Architecture Highlights

### Async-First Design
All API routes and database operations use `async/await` for high concurrency.

### Queue-Based Processing
5 Celery queues with priority levels:
- `high_priority` (10) - Critical evaluations
- `webhooks` (8) - Webhook delivery
- `documents` (7) - Resume parsing
- `emails` (6) - Email sending
- `default` (5) - General tasks

### Agent Framework
Extensible agent system with:
- Base agent class for common functionality
- Registry for agent discovery
- Tool integration for specialized tasks
- Google Gemini 2.0 for AI capabilities

### Database Optimization
140+ strategic indexes:
- Basic indexes for foreign keys
- Composite indexes for common queries
- GIN indexes for JSONB and arrays
- Partial indexes for filtered queries
- HNSW indexes for vector similarity

## Next Steps

1. **Start Development**: Choose a component (API routes, agents, tasks)
2. **Implement Logic**: Fill in TODO sections with actual logic
3. **Add Tests**: Write tests for implemented functionality
4. **Deploy**: Use Docker for containerization (see ARCHITECTURE.md)

## Resources

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **Database**: [docs/database.md](docs/database.md)
- **Implementation**: [docs/IMPLEMENTATION_SUMMARY.md](docs/IMPLEMENTATION_SUMMARY.md)

## Troubleshooting

### "Connection refused" on port 8000
```bash
# Check if port is in use
lsof -i :8000

# Kill process if needed
kill -9 <PID>
```

### "Can't connect to database"
```bash
# Check PostgreSQL is running
pg_isready

# Verify credentials in .env
cat .env | grep DATABASE_URL
```

### "Redis connection failed"
```bash
# Start Redis
redis-server

# Or check if running
redis-cli ping
# Expected: PONG
```

### Import errors
```bash
# Reinstall dependencies
poetry install

# Check Python version
python --version  # Should be 3.11+
```

## Support

For detailed architecture information, see [ARCHITECTURE.md](ARCHITECTURE.md).

For database schema details, see [docs/database.md](docs/database.md).

For implementation details, see [docs/IMPLEMENTATION_SUMMARY.md](docs/IMPLEMENTATION_SUMMARY.md).

---

**Ready to start building!** 🚀
