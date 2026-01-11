# Docker Setup for ARE (Alethic Reasoning Engine)

This document describes the Docker setup for the ARE service in the Alethic monorepo.

## Files Created

### Development Mode
1. **apps/are/infra/Dockerfile** - Development build with hot-reload
2. **apps/are/infra/Dockerfile.worker** - Development worker with auto-restart
3. **apps/are/infra/docker-compose.dev.yml** - Development stack configuration

### Production Mode
4. **apps/are/infra/Dockerfile.prod** - Production build with multiple workers
5. **apps/are/infra/Dockerfile.worker.prod** - Production worker optimized
6. **apps/are/infra/docker-compose.prod.yml** - Production stack configuration

### Common
7. **apps/are/infra/.dockerignore** - Optimization for Docker build context

## Modes

### Development Mode 🔧
- **Hot-reload** enabled for API and workers
- Volume mounts for live code sync
- Dev dependencies installed
- Single instance of each service
- User: `alethic` / Pass: `alethic_dev_password`

### Production Mode 🚀
- **Multiple workers** for high availability
- No volume mounts (code baked into image)
- Production dependencies only
- Resource limits configured
- Horizontal scaling ready
- Secrets via environment variables

## Quick Start

### Development (Recommended for local work)

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
```bash
# From apps/are directory
docker-compose -f docker-compose.dev.yml up -d

# Watch logs
docker-compose -f docker-compose.dev.yml logs -f are-api are-worker

# Edit code in apps/are/ - changes auto-reload!
```

### Production

```bash
# Create .env.prod file first (see Environment Variables section)
# From apps/are/infra directory
docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d

# Scale workers
docker-compose -f docker-compose.prod.yml up -d --scale are-worker=8
```

## Usage

### Development Mode

```bash
# Start all services
cd apps/are/infra
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f

# Stop services
docker-compose -f docker-compose.dev.yml down

# Rebuild after dependency changes
docker-compose -f docker-compose.dev.yml up -d --build
```

### Production Mode

```bash
# Start all services
cd apps/are/infra
docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d
Database Migrations

```bash
# Development
docker-compose -f docker-compose.dev.yml exec are-api alembic upgrade head

# Production
docker-compose -f docker-compose.prod.yml exec are-api alembic upgrade headrker
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

### Development (.env file - optional)

Create `.env` in `apps/are/infra/` directory:

```bash
# Google AI
GOOGLE_API_KEY=your_google_api_key_here

# Security (optional in dev, defaults provided)
JWT_SECRET_KEY=dev_secret_key
```

### Production (.env.prod file - REQUIRED)

Create `.env.prod` in `apps/are/infra/` directory:

```bash
# Database
POSTGRES_USER=alethic
POSTGRES_PASSWOBest Practices

✅ Already configured in `docker-compose.prod.yml`:
- Multiple API workers (uvicorn with 4 workers)
- No volume mounts (code baked into image)
- Resource limits (CPU and memory)
- Health checks for all services
- Restart policies (always)
- Horizontal scaling support

🔒 Additional security recommendations:
1. **Use secrets management** - AWS Secrets Manager, Vault, etc.
2. **Enable SSL/TLS** - Use reverse proxy (nginx, traefik)
3. **Network isolation** - Use internal networks
4. **Regular updates** - Keep base images updated
5. **Monitoring** - Add Prometheus, Grafana, ELK stack
6. **Backups** - Automated database and volume backups
1. **Remove `--reload` flag** - Create production Dockerfile variant:
   ```dockerfile
   CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
   ```
2. **Remove volume mounts** - Don't mount source code in production
3. **Remove watchmedo** - Use standard celery worker command
4. **Use secrets management** - Don't use plain text env vars
5. **Enable SSL/TLS** - Use HTTPS with proper certificates
6. **Resource limits** - Add CPU and memory limits
7. **Horizontal scaling** - Scale workers based on load
8. **Monitoring** - Add logging, metrics, and health checks

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
### Development
- **are-api**: 8000 - FastAPI REST API
- **postgres**: 5432 - PostgreSQL database  
- **redis**: 6379 - Redis cache/broker
- **minio**: 9000 (API), 9001 (Console) - S3-compatible storage

### Production
- Ports configured via `.env.prod` file
- Typically run behind reverse proxy (nginx/traefik)

## Accessing Services

### Development
- **API Docs**: http://localhost:8000/docs
- **API Health**: http://localhost:8000/health
- **MinIO Console**: http://localhost:9001 (user: alethic, pass: alethic_dev_password)

### Production
- Development
docker-compose -f docker-compose.dev.yml logs are-api
docker-compose -f docker-compose.dev.yml ps

# Production
docker-compose -f docker-compose.prod.yml logs are-api
docker-compose -f docker-compose.prod.yml ps
```

### Database connection issues

```bash
# Verify postgres is healthy
docker-compose -f docker-compose.dev.yml ps postgres

# Test connection
docker-compose -f docker-compose.dev.yml exec are-api python -c "from database.engine import engine; print('OK')"
```

### Worker not processing tasks

```bash
# Check worker logs
docker-compose -f docker-compose.dev.yml logs -f are-worker

# Verify Redis connection (dev)
docker-compose -f docker-compose.dev.yml exec are-worker redis-cli -h redis ping

# Verify Redis connection (prod with auth)
docker-compose -f docker-compose.prod.yml exec are-worker redis-cli -h redis -a YOUR_REDIS_PASSWORD ping
```

### Build failures

```bash
# Development - clean rebuild
cd apps/are
docker-compose -f docker-compose.dev.yml down
docker-compose -f docker-compose.dev.yml build --no-cache
docker-compose -f docker-compose.dev.yml up -d

# Production - clean rebuild
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d
```
Comparison: Dev vs Production

| Feature | Development | Production |
|---------|------------|------------|
| **Hot Reload** | ✅ Enabled | ❌ Disabled |
| **Volume Mounts** | ✅ Yes | ❌ No |
| **Workers** | 1 API, 1 Worker | 2 API, 4 Workers |
| **Resource Limits** | ❌ None | ✅ CPU/Memory limits |
| **Dependencies** | All (dev + test) | Production only |
| **Uvicorn Workers** | 1 (--reload) | 4 (multi-process) |
| **Celery Config** | Watchmedo restart | Standard worker |
| **Credentials** | Hardcoded | From .env.prod |
| **Scaling** | Manual | Auto-scalable |
| **Security** | Relaxed | Hardened |

## Next Steps

### For Development
1. Ensure `GOOGLE_API_KEY` is in your environment
2. Run `cd apps/are/infra && docker-compose -f docker-compose.dev.yml up -d`
3. Access API at http://localhost:8000/docs
4. Start coding - changes auto-reload!

### For Production
1. Create `.env.prod` in `apps/are/infra/` with all required secrets
2. Review resource limits in `docker-compose.prod.yml`
3. Set up reverse proxy (nginx/traefik) for SSL
4. Configure monitoring and logging
5. Run `cd apps/are/infra && docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d`
6. Test thoroughly before going livenfig | grep volumes -A 5

# Check if watchdog is installed
docker-compose -f docker-compose.dev.yml exec are-worker pip list | grep watchdog

# Restart services
docker-compose -f docker-compose.dev.yml restart are-api are-worker
# Make code changes in apps/are/
# Services automatically restart!

# View logs
docker-compose logs -f are-api are-worker
```

### Alternative: Hybrid Approach

If you prefer running Python locally:

1. **Start services**:
   ```bash
   docker-compose up -d postgres redis minio
   ```

cd apps/are
docker-compose -f docker-compose.dev.yml up -d

# Make code changes in apps/are/
# Services automatically restart!

# View logs in real-time
docker-compose -f docker-compose.dev.yml logs -f are-api are-worker
```

### Alternative: Hybrid Approach (Services in Docker, Python Local)

```bash
# Start only infrastructure services
cd apps/are/infra
docker-compose -f docker-compose.dev.yml up -d postgres redis minio

# Run API locally (if you prefer)
cd ../../  # Go back to are directory
poetry run uvicorn api.main:app --reload

# Run worker locally
poetry run celery -A workers.celery_app worker --loglevel=info
