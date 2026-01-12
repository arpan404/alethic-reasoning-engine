# Middleware Documentation

This directory contains production-ready middleware components for the FastAPI application with enterprise-grade security, monitoring, and rate limiting capabilities.

## Overview

The middleware stack provides:

1. **Error Handling**: Comprehensive exception handling with sensitive data sanitization
2. **Structured Logging**: PII-masked request/response logging with performance metrics
3. **Rate Limiting**: Redis-based distributed rate limiting with multiple strategies

## Components

### 1. Error Handling Middleware

**File**: `error_handling.py`

#### Features

- ✅ Automatic sensitive data sanitization (passwords, tokens, API keys, etc.)
- ✅ Structured error responses with appropriate HTTP status codes
- ✅ Comprehensive exception handling (SQLAlchemy, Redis, HTTP, validation errors)
- ✅ Detailed logging with appropriate severity levels
- ✅ Development vs production mode (detailed errors only in dev)
- ✅ Security compliance (no stack traces or sensitive data in production)

#### Security Features

- **Regex-based sensitive data detection**: Automatically redacts passwords, tokens, API keys, secrets, SSNs, credit cards
- **Safe error details**: Only exposes safe information to clients
- **Validation error sanitization**: Cleans user input from error messages
- **Stack trace control**: Only included in development mode

#### Usage

```python
from core.middleware.error_handling import ErrorHandlingMiddleware, setup_error_handlers

# Add to FastAPI app
app.add_middleware(ErrorHandlingMiddleware, debug=settings.debug)

# Or use exception handlers
setup_error_handlers(app)
```

#### Error Response Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "path": "/api/v1/users",
    "method": "POST",
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "details": [
      {
        "field": "body.email",
        "message": "value is not a valid email address",
        "type": "value_error.email"
      }
    ]
  }
}
```

### 2. Structured Logging Middleware

**File**: `logging.py`

#### Features

- ✅ Structured JSON logging for easy parsing and analysis
- ✅ Automatic PII masking (emails, phones, SSNs, credit cards, IPs)
- ✅ Request/response timing and performance metrics
- ✅ Request ID tracking for distributed tracing
- ✅ Sensitive header masking (Authorization, Cookies, etc.)
- ✅ Configurable body logging with size limits
- ✅ Skip logging for health check endpoints

#### Security Features

- **PII Pattern Detection**: Automatically masks emails, phones, SSNs, credit cards
- **Sensitive Field Detection**: Masks any field containing password, token, secret, etc.
- **Header Sanitization**: Redacts authorization headers while preserving auth type
- **IP Masking**: Masks last octet of IP addresses for privacy
- **Recursive Masking**: Deep inspection of nested objects and arrays

#### Usage

```python
from core.middleware.logging import StructuredLoggingMiddleware, setup_logging

# Setup logging first
setup_logging(log_level="INFO", json_logs=True)

# Add middleware
app.add_middleware(
    StructuredLoggingMiddleware,
    log_request_body=False,  # Enable in development only
    log_response_body=False,  # Enable in development only
    max_body_size=1024,  # Maximum bytes to log
)
```

#### Log Output Example

```json
{
  "event": "request_started",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "method": "POST",
  "path": "/api/v1/users",
  "query_params": {},
  "client_ip": "192.168.1.xxx",
  "user_agent": "Mozilla/5.0...",
  "headers": {
    "authorization": "Bearer [REDACTED]",
    "content-type": "application/json"
  }
}

{
  "event": "request_completed",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "method": "POST",
  "path": "/api/v1/users",
  "duration_ms": 125.45,
  "status_code": 201,
  "performance": "fast"
}
```

### 3. Rate Limiting Middleware

**File**: `rate_limiting.py`

#### Features

- ✅ Redis-based distributed rate limiting
- ✅ Sliding window algorithm (precise and memory-efficient)
- ✅ Multiple strategies: IP, User ID, API Key, Endpoint, Global, Combined
- ✅ Per-endpoint custom rules
- ✅ Configurable time windows (second, minute, hour, day)
- ✅ Graceful degradation (fail open if Redis unavailable)
- ✅ Rate limit headers in responses
- ✅ Exemption lists (IPs, user IDs)
- ✅ Method-specific limits

#### Rate Limiting Strategies

1. **IP_ADDRESS**: Rate limit by client IP address
2. **USER_ID**: Rate limit by authenticated user ID
3. **API_KEY**: Rate limit by API key
4. **ENDPOINT**: Rate limit per endpoint
5. **GLOBAL**: Global rate limit across all requests
6. **COMBINED**: Combines IP + User + Endpoint

#### Usage

```python
from core.middleware.rate_limiting import (
    RateLimitMiddleware,
    RateLimitRule,
    RateLimitStrategy,
    RateLimitWindow,
)

# Define custom rules
rules = [
    # Strict auth endpoint limits
    RateLimitRule(
        strategy=RateLimitStrategy.IP_ADDRESS,
        window=RateLimitWindow.MINUTE,
        max_requests=5,
        paths=['/api/v1/auth/login'],
        methods=['POST'],
    ),
    # User-based limits
    RateLimitRule(
        strategy=RateLimitStrategy.USER_ID,
        window=RateLimitWindow.MINUTE,
        max_requests=100,
    ),
    # Expensive operations
    RateLimitRule(
        strategy=RateLimitStrategy.COMBINED,
        window=RateLimitWindow.MINUTE,
        max_requests=10,
        paths=['/api/v1/resume/parse'],
    ),
]

# Add middleware
app.add_middleware(
    RateLimitMiddleware,
    redis_url="redis://localhost:6379/0",
    rules=rules,
    key_prefix="myapp:ratelimit",
    enable_headers=True,
)
```

#### Rate Limit Response Headers

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1640000000
Retry-After: 45  (only when rate limited)
```

#### Rate Limit Error Response

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Please try again later.",
    "retry_after": 45
  }
}
```

## Configuration

Add these environment variables to your `.env` file:

```bash
# Logging
LOG_LEVEL=INFO
JSON_LOGS=true
LOG_REQUEST_BODY=false
LOG_RESPONSE_BODY=false
LOG_MAX_BODY_SIZE=1024

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_SECOND=10
RATE_LIMIT_PER_MINUTE=100
RATE_LIMIT_PER_HOUR=1000

# Redis (required for rate limiting)
REDIS_URL=redis://localhost:6379/0
```

## Integration Example

See `example_integration.py` for a complete working example:

```python
from core.middleware.example_integration import create_app

app = create_app()
```

## Best Practices

### Error Handling

1. **Never log sensitive data**: The middleware automatically sanitizes, but be careful in custom handlers
2. **Use appropriate status codes**: The middleware handles common cases, but verify custom exceptions
3. **Test error scenarios**: Ensure errors are properly sanitized in production

### Logging

1. **Use structured logging**: Always use JSON logs in production for easy parsing
2. **Don't log request bodies in production**: Only enable for debugging
3. **Monitor log volume**: Adjust what's logged based on traffic
4. **Use request IDs**: Always include request IDs for tracing

### Rate Limiting

1. **Set appropriate limits**: Start conservative and adjust based on metrics
2. **Use multiple strategies**: Combine IP and user-based limits
3. **Monitor Redis**: Ensure Redis is healthy and has enough memory
4. **Test fail-open behavior**: Verify graceful degradation when Redis is down
5. **Exempt health checks**: Don't rate limit monitoring endpoints
6. **Consider costs**: Use higher costs for expensive operations

## Security Considerations

### What is Protected

✅ Passwords, tokens, API keys, secrets  
✅ Credit card numbers, SSNs  
✅ Email addresses, phone numbers  
✅ IP addresses (last octet masked)  
✅ Authorization headers  
✅ Stack traces (production)  
✅ Database connection strings  

### What to Watch For

⚠️ Custom sensitive fields (add to patterns if needed)  
⚠️ Third-party library logs (configure separately)  
⚠️ Application-specific PII  
⚠️ Nested or encoded sensitive data  

## Performance Considerations

### Error Handling
- Minimal overhead (only on errors)
- Regex compilation is done once at module load

### Logging
- JSON serialization has small overhead (~1-2ms per request)
- Body logging can be expensive for large payloads
- Skip health checks to reduce noise

### Rate Limiting
- Redis latency: ~1-2ms per check
- Pipeline operations minimize round trips
- Sliding window more accurate than fixed window
- Memory: ~100 bytes per active key

## Monitoring and Alerts

### Key Metrics to Monitor

1. **Error Rate**: Track 5xx errors from error middleware
2. **Response Time**: Monitor duration_ms from logging middleware
3. **Rate Limit Hits**: Track 429 responses
4. **Redis Health**: Monitor rate limiter Redis connection

### Recommended Alerts

- Error rate > 1% for 5 minutes
- P95 response time > 1000ms for 5 minutes
- Rate limit hits > 100/minute (investigate traffic)
- Redis connection failures

## Testing

```python
# Test error handling
def test_error_sanitization():
    message = "Error: password=secret123"
    sanitized = sanitize_error_message(message)
    assert "secret123" not in sanitized
    assert "[REDACTED]" in sanitized

# Test rate limiting
async def test_rate_limit():
    # Make requests up to limit
    for _ in range(100):
        response = await client.get("/api/endpoint")
        assert response.status_code == 200
    
    # Next request should be rate limited
    response = await client.get("/api/endpoint")
    assert response.status_code == 429
    assert "retry_after" in response.json()["error"]
```

## Troubleshooting

### Common Issues

**Q: Rate limiting not working**
- Check Redis connection
- Verify `RATE_LIMIT_ENABLED=true`
- Check middleware order (rate limit should be innermost)

**Q: Too many logs**
- Adjust `LOG_LEVEL`
- Skip health check endpoints
- Reduce body logging

**Q: Sensitive data still appearing in logs**
- Add custom patterns to `SENSITIVE_FIELD_PATTERNS`
- Check third-party library logging
- Verify JSON_LOGS=true for proper masking

**Q: Rate limit too strict**
- Adjust limits in config
- Add exemptions for internal IPs
- Use different strategies per endpoint

## License

Part of the ATS application. All rights reserved.
