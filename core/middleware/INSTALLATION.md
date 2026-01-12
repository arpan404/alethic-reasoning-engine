# Installation Notes

## Important: Redis Package

The middleware requires the `redis` package with async support. While it's listed in `pyproject.toml`, you may need to install it:

```bash
# Install all dependencies
pip install -e .

# Or install redis specifically
pip install "redis>=5.0.0"
```

## Verify Installation

Run these checks to ensure everything is installed:

```bash
# Check Redis
python -c "import redis.asyncio; print('✓ Redis async support available')"

# Check FastAPI
python -c "import fastapi; print('✓ FastAPI available')"

# Check Pydantic Settings
python -c "from pydantic_settings import BaseSettings; print('✓ Pydantic settings available')"
```

## If Redis is Not Installed

If you see `ModuleNotFoundError: No module named 'redis'`, install it:

```bash
pip install "redis>=5.0.0"
```

## Redis Server

The rate limiting middleware requires a running Redis server. Options:

### Option 1: Docker (Recommended)
```bash
docker run -d -p 6379:6379 --name are-redis redis:7-alpine
```

### Option 2: Local Installation

**macOS (Homebrew):**
```bash
brew install redis
brew services start redis
```

**Ubuntu/Debian:**
```bash
sudo apt-get install redis-server
sudo systemctl start redis-server
```

**Verify Redis is running:**
```bash
redis-cli ping
# Should return: PONG
```

## Disabling Rate Limiting

If you don't want to use rate limiting (not recommended for production), you can disable it:

```bash
# In .env
RATE_LIMIT_ENABLED=false
```

This will allow the application to run without Redis, but you'll lose rate limiting protection.

## Full Installation Steps

1. **Install Python dependencies:**
   ```bash
   cd /Users/arpanbhandari/Code/are
   pip install -e .
   ```

2. **Start Redis:**
   ```bash
   docker run -d -p 6379:6379 redis:7-alpine
   ```

3. **Configure environment:**
   ```bash
   cp core/middleware/.env.template .env
   # Edit .env with your settings
   ```

4. **Verify setup:**
   ```bash
   python -c "import redis.asyncio; print('Ready!')"
   redis-cli ping
   ```

5. **Run the application:**
   ```bash
   uvicorn api.main:app --reload --port 8000
   ```

## Troubleshooting

### "ModuleNotFoundError: No module named 'redis'"
```bash
pip install "redis>=5.0.0"
```

### "ConnectionRefusedError: [Errno 61] Connection refused"
Redis server is not running. Start it:
```bash
docker run -d -p 6379:6379 redis:7-alpine
```

### "RedisConnectionError"
Check Redis URL in `.env`:
```bash
REDIS_URL=redis://localhost:6379/0
```

### Rate limiting not working but no errors
The middleware fails open by design. Check logs for Redis connection warnings.
