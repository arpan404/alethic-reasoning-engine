# Middleware Quick Start Guide

This guide will help you quickly set up and use the middleware components in your application.

## Prerequisites

1. Redis server running (for rate limiting)
2. Environment variables configured
3. Python 3.13+ with dependencies installed

## Quick Setup

### 1. Install Dependencies

All required dependencies are already in `pyproject.toml`. If you need to reinstall:

```bash
pip install -e .
```

### 2. Configure Environment Variables

Copy the template and configure:

```bash
cp core/middleware/.env.template .env
```

Edit `.env` with your settings:

```bash
# Essential settings
LOG_LEVEL=INFO
JSON_LOGS=true
DEBUG=false

RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=100
RATE_LIMIT_PER_HOUR=1000

# Redis connection (required for rate limiting)
REDIS_URL=redis://localhost:6379/0
```

### 3. Start Redis (if not already running)

```bash
# Using Docker
docker run -d -p 6379:6379 redis:7-alpine

# Or using Homebrew on macOS
brew services start redis
```

### 4. The Middleware is Already Integrated!

The middleware has been integrated into `/api/main.py`. You can start the application:

```bash
# Development mode
uvicorn api.main:app --reload --port 8000

# Or using the Makefile (if available)
make run
```

## Verify It's Working

### Test Error Handling

```bash
# This should return a sanitized error response
curl http://localhost:8000/nonexistent-endpoint
```

Expected response:
```json
{
  "error": {
    "code": "HTTP_EXCEPTION",
    "message": "Not Found",
    "path": "/nonexistent-endpoint",
    "method": "GET"
  }
}
```

### Test Rate Limiting

```bash
# Make multiple rapid requests
for i in {1..150}; do
  curl -s http://localhost:8000/api/v1/candidates | head -n 1
done
```

You should see rate limit headers:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1640000000
```

And eventually a 429 error:
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Please try again later.",
    "retry_after": 45
  }
}
```

### Test Logging

Check your application logs - you should see structured JSON logs:

```json
{
  "event": "request_started",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "method": "GET",
  "path": "/api/v1/candidates",
  "client_ip": "192.168.1.xxx",
  "timestamp": "2026-01-12T10:30:00Z"
}
```

## Configuration Examples

### Development Environment

```bash
# .env for development
LOG_LEVEL=DEBUG
JSON_LOGS=false
LOG_REQUEST_BODY=true
LOG_RESPONSE_BODY=true
DEBUG=true
RATE_LIMIT_ENABLED=false
```

### Production Environment

```bash
# .env for production
LOG_LEVEL=WARNING
JSON_LOGS=true
LOG_REQUEST_BODY=false
LOG_RESPONSE_BODY=false
DEBUG=false
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_SECOND=10
RATE_LIMIT_PER_MINUTE=100
RATE_LIMIT_PER_HOUR=1000
```

## Custom Rate Limit Rules

To modify rate limiting rules, edit `api/main.py`:

```python
# Add a custom rule for a specific endpoint
RateLimitRule(
    strategy=RateLimitStrategy.IP_ADDRESS,
    window=RateLimitWindow.MINUTE,
    max_requests=5,
    paths=['/api/v1/expensive-operation'],
    methods=['POST'],
)
```

## Monitoring

### Key Metrics to Watch

1. **Error Rate**: Monitor 5xx errors in logs
2. **Response Time**: Check `duration_ms` in logs
3. **Rate Limit Hits**: Track 429 responses
4. **Redis Health**: Monitor rate limiter Redis connection

### Example Log Query (for JSON logs)

```bash
# Find slow requests (>1 second)
grep "request_completed" app.log | jq 'select(.duration_ms > 1000)'

# Find rate limit hits
grep "RATE_LIMIT_EXCEEDED" app.log | jq

# Find errors
grep "error" app.log | jq 'select(.level == "ERROR")'
```

## Testing

Run the middleware tests:

```bash
pytest tests/unit/core/test_middleware.py -v
```

## Troubleshooting

### Rate Limiting Not Working

1. **Check Redis connection:**
   ```bash
   redis-cli ping
   # Should return: PONG
   ```

2. **Verify Redis URL in .env:**
   ```bash
   echo $REDIS_URL
   ```

3. **Check logs for Redis errors:**
   ```bash
   grep "Redis" app.log
   ```

### Logs Not Appearing

1. **Check LOG_LEVEL setting:**
   ```bash
   echo $LOG_LEVEL
   ```

2. **Verify logging is initialized:**
   Check that `setup_logging()` is called before any other code

3. **Check for third-party library logging:**
   Some libraries may override logging config

### Sensitive Data Appearing in Logs

1. **Add custom patterns** to `SENSITIVE_FIELD_PATTERNS` in `logging.py`
2. **Verify JSON_LOGS=true** for proper masking
3. **Check that masking functions are working** - run tests

## Advanced Usage

### Custom Error Handler

Add custom error handling for specific exceptions:

```python
from fastapi import HTTPException

@app.exception_handler(CustomException)
async def custom_exception_handler(request, exc):
    # Your custom handling
    return JSONResponse(
        status_code=400,
        content={"error": {"code": "CUSTOM_ERROR", "message": str(exc)}}
    )
```

### Custom Rate Limit Strategy

Implement custom rate limiting logic:

```python
# In rate_limiting.py, add to _generate_key method
elif rule.strategy == RateLimitStrategy.CUSTOM:
    # Your custom key generation
    custom_key = generate_custom_key(request)
    parts.append(custom_key)
```

### Custom Log Formatting

Modify the `StructuredFormatter` class in `logging.py` to change log format.

## Security Checklist

✅ DEBUG mode disabled in production  
✅ Request/response body logging disabled in production  
✅ JSON logs enabled for proper masking  
✅ Rate limiting enabled  
✅ Redis connection secured  
✅ Appropriate rate limits set per endpoint  
✅ Log retention policy configured  

## Performance Optimization

1. **Reduce log volume** - Increase LOG_LEVEL to WARNING or ERROR in production
2. **Skip health checks** - Already configured to skip `/health` endpoints
3. **Optimize Redis** - Use connection pooling and persistence
4. **Monitor memory** - Redis rate limiter uses ~100 bytes per active key

## Support

For issues or questions:

1. Check the comprehensive README: `core/middleware/README.md`
2. Review example integration: `core/middleware/example_integration.py`
3. Run tests: `pytest tests/unit/core/test_middleware.py -v`
4. Check logs for detailed error messages

## What's Next?

- Set up log aggregation (ELK, Datadog, CloudWatch)
- Configure alerts for error rates and rate limits
- Implement custom rate limit rules per client tier
- Add metrics export (Prometheus, StatsD)
- Set up distributed tracing (Jaeger, Zipkin)
