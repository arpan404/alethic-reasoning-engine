# Docker Setup for ARE (Alethic Reasoning Engine)

This document describes the Docker setup for the ARE service in the Koru monorepo.

## Files Created

1. **apps/are/Dockerfile** - Multi-stage build for FastAPI API server
2. **apps/are/Dockerfile.worker** - Celery worker container
3. **apps/are/.dockerignore** - Optimization for Docker build context

## Docker Compose Configuration

Add the following services to `/docker-compose.yml` (root of koru monorepo):

### ARE API Service

```yaml
  # ARE (Alethic Reasoning Engine) - FastAPI + Google ADK
  are-api:
    build:
      context: .
      dockerfile: apps/are/Dockerfile
    ports:
      - "8000:8000"
    environment:
      - PYTHONUNBUFFERED=1
      - DATABASE_URL=postgresql+asyncpg://koru:koru_dev_password@postgres:5432/koru_db
      - REDIS_URL=redis://redis:6379
      - AWS_ENDPOINT_URL=http://minio:9000
      - AWS_ACCESS_KEY_ID=koru
      - AWS_SECRET_ACCESS_KEY=koru_dev_password
      - AWS_REGION=us-east-1
      - S3_BUCKET=koru-uploads
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY:-dev_secret_key_change_in_production}
      - ENVIRONMENT=development
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      minio:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    volumes:
      - ./apps/are:/app:ro  # Read-only mount for hot reload (dev only)
```

### ARE Celery Worker Service

```yaml
  # ARE Celery Workers - Document processing, AI tasks
  are-worker:
    build:
      context: .
      dockerfile: apps/are/Dockerfile.worker
    environment:
      - PYTHONUNBUFFERED=1
      - DATABASE_URL=postgresql+asyncpg://koru:koru_dev_password@postgres:5432/koru_db
      - REDIS_URL=redis://redis:6379
      - AWS_ENDPOINT_URL=http://minio:9000
      - AWS_ACCESS_KEY_ID=koru
      - AWS_SECRET_ACCESS_KEY=koru_dev_password
      - AWS_REGION=us-east-1
      - S3_BUCKET=koru-uploads
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      minio:
        condition: service_healthy
    restart: unless-stopped
    deploy:
      replicas: 2  # Run 2 worker instances
    volumes:
      - ./apps/are:/app:ro
```

### ARE Celery Beat Service (Scheduled Tasks)

```yaml
  # ARE Celery Beat - Scheduled tasks
  are-beat:
    build:
      context: .
      dockerfile: apps/are/Dockerfile.worker
    command: ["celery", "-A", "workers.celery_app", "beat", "--loglevel=info"]
    environment:
      - PYTHONUNBUFFERED=1
      - DATABASE_URL=postgresql+asyncpg://koru:koru_dev_password@postgres:5432/koru_db
      - REDIS_URL=redis://redis:6379
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
    depends_on:
      redis:
        condition: service_healthy
    restart: unless-stopped
    volumes:
      - ./apps/are:/app:ro
```

## Usage

### Start All Services

```bash
# From koru root directory
docker-compose up -d
```

### Start Specific Services

```bash
# Just ARE services
docker-compose up -d are-api are-worker are-beat

# With dependencies
docker-compose up -d postgres redis minio are-api are-worker
```

### View Logs

```bash
# All ARE services
docker-compose logs -f are-api are-worker are-beat

# Specific service
docker-compose logs -f are-api
```

### Run Database Migrations

```bash
# Inside the are-api container
docker-compose exec are-api alembic upgrade head
```

### Scale Workers

```bash
# Run 4 worker instances
docker-compose up -d --scale are-worker=4
```

### Rebuild After Code Changes

```bash
# Rebuild and restart
docker-compose up -d --build are-api are-worker are-beat
```

## Environment Variables

### Required Environment Variables

Create a `.env` file in the koru root directory:

```bash
# Google AI
GOOGLE_API_KEY=your_google_api_key_here

# Security
JWT_SECRET_KEY=your_production_jwt_secret_key

# Optional - Override defaults
DATABASE_URL=postgresql+asyncpg://koru:koru_dev_password@postgres:5432/koru_db
REDIS_URL=redis://redis:6379
AWS_ENDPOINT_URL=http://minio:9000
AWS_ACCESS_KEY_ID=koru
AWS_SECRET_ACCESS_KEY=koru_dev_password
```

### Production Considerations

For production deployments:

1. **Remove volume mounts** - Don't mount source code
2. **Use secrets management** - Don't use plain text env vars
3. **Enable SSL/TLS** - Use HTTPS with proper certificates
4. **Resource limits** - Add CPU and memory limits
5. **Horizontal scaling** - Scale workers based on load
6. **Monitoring** - Add logging, metrics, and health checks

Example production resource limits:

```yaml
are-api:
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 4G
      reservations:
        cpus: '1'
        memory: 2G
```

## Service Ports

- **are-api**: 8000 - FastAPI REST API
- **postgres**: 5432 - PostgreSQL database
- **redis**: 6379 - Redis cache/broker
- **minio**: 9000 (API), 9001 (Console) - S3-compatible storage
- **rabbitmq**: 5672 (AMQP), 15672 (Management UI)

## Accessing Services

- **API Docs**: http://localhost:8000/docs
- **API Health**: http://localhost:8000/health
- **MinIO Console**: http://localhost:9001 (user: koru, pass: koru_dev_password)
- **RabbitMQ Console**: http://localhost:15672 (user: koru, pass: koru_dev_password)

## Troubleshooting

### Container won't start

```bash
# Check logs
docker-compose logs are-api

# Check health
docker-compose ps
```

### Database connection issues

```bash
# Verify postgres is healthy
docker-compose ps postgres

# Test connection
docker-compose exec are-api python -c "from database.engine import engine; print('OK')"
```

### Worker not processing tasks

```bash
# Check worker logs
docker-compose logs -f are-worker

# Verify Redis connection
docker-compose exec are-worker redis-cli -h redis ping
```

### Build failures

```bash
# Clean rebuild
docker-compose down
docker-compose build --no-cache are-api are-worker
docker-compose up -d
```

## Development Workflow

1. **Start services**:
   ```bash
   docker-compose up -d postgres redis minio
   ```

2. **Run API locally** (faster for development):
   ```bash
   cd apps/are
   poetry run uvicorn api.main:app --reload
   ```

3. **Run worker locally**:
   ```bash
   cd apps/are
   poetry run celery -A workers.celery_app worker --loglevel=info
   ```

4. **When ready to test full stack**:
   ```bash
   docker-compose up -d --build
   ```

## Next Steps

1. Add `are-api`, `are-worker`, and `are-beat` services to `/docker-compose.yml`
2. Create `.env` file with required keys
3. Run `docker-compose up -d` to start all services
4. Access API at http://localhost:8000/docs
