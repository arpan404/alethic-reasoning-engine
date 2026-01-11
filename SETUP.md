# Alethic ARE - Setup Guide

## Repository Migration Complete ✅

The Alethic Reasoning Engine (ARE) has been successfully extracted to its own repository at `~/code/are` with full git history preserved (35 commits).

## Quick Start

### 1. Install Dependencies

```bash
cd ~/code/are
poetry install
```

### 2. Set Up Environment

```bash
# Copy example env file
cp .env.example .env

# Edit with your keys
export GOOGLE_API_KEY=your_key_here
export JWT_SECRET_KEY=your_secret_here
```

### 3. Start Development Environment

**Option A: Full Docker Stack (Recommended)**
```bash
cd infra
docker-compose -f docker-compose.dev.yml up -d

# Watch logs
docker-compose -f docker-compose.dev.yml logs -f are-api are-worker
```

**Option B: Local Development**
```bash
# Start infrastructure only
cd infra
docker-compose -f docker-compose.dev.yml up -d postgres redis minio

# Run API locally
cd ..
poetry run uvicorn api.main:app --reload

# Run worker in another terminal
poetry run celery -A workers.celery_app worker --loglevel=info
```

### 4. Run Database Migrations

```bash
# If using Docker
cd infra
docker-compose -f docker-compose.dev.yml exec are-api alembic upgrade head

# If running locally
alembic upgrade head
```

### 5. Access Services

- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **MinIO Console**: http://localhost:9001 (user: alethic, pass: alethic_dev_password)

## Project Structure

```
are/
├── agents/           # Google ADK AI agents (resume, screening, evaluation)
├── api/             # FastAPI routes and schemas
├── core/            # Utilities, parsers, integrations
├── database/        # SQLAlchemy models
├── workers/         # Celery tasks
├── infra/           # Docker configs (dev & prod)
├── docs/            # Documentation
├── tests/           # Test suite
└── alembic/         # Database migrations
```

## Documentation

- [Architecture Guide](docs/ARCHITECTURE.md)
- [Docker Setup](docs/DOCKER.md)
- [Folder Structure](docs/FOLDER_STRUCTURE.md)
- [Migration Guide](docs/MIGRATION_GUIDE.md)

## Development

### Running Tests
```bash
poetry run pytest
```

### Code Quality
```bash
# Format code
poetry run black .

# Lint
poetry run ruff check .
```

### Creating Migrations
```bash
# Auto-generate from model changes
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head
```

## Production Deployment

See [docs/DOCKER.md](docs/DOCKER.md) for production setup with:
- Multiple workers (2 API, 4 Celery workers)
- Resource limits
- Secrets management
- Horizontal scaling

```bash
cd infra
docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d
```

## Next Steps

1. **Set up GitHub/GitLab remote**:
   ```bash
   git remote add origin <your-repo-url>
   git push -u origin main
   ```

2. **Configure CI/CD** (GitHub Actions, GitLab CI, etc.)

3. **Set up production environment** with proper secrets management

4. **Enable monitoring** (Prometheus, Grafana, Sentry)

## Features

- ✅ FastAPI + Uvicorn (async API)
- ✅ Google ADK agents (Gemini 2.0)
- ✅ Celery + Redis (async tasks)
- ✅ PostgreSQL + pgvector (vector search)
- ✅ 140+ optimized database indexes
- ✅ Docker dev & prod configs
- ✅ Hot-reload in dev mode
- ✅ Comprehensive documentation

## Support

For issues or questions, check the documentation in `/docs` or create an issue in the repository.
