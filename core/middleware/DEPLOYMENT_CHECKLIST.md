# Middleware Deployment Checklist

Use this checklist before deploying to production to ensure all middleware components are properly configured and secured.

## Pre-Deployment Checklist

### 1. Dependencies ✓

- [ ] All dependencies installed: `pip install -e .`
- [ ] Redis package available: `python -c "import redis.asyncio"`
- [ ] FastAPI version >= 0.115.0
- [ ] Redis server accessible

### 2. Environment Configuration ✓

- [ ] `.env` file created from template
- [ ] `DEBUG=false` in production
- [ ] `LOG_LEVEL=WARNING` or `INFO` in production
- [ ] `JSON_LOGS=true` in production
- [ ] `LOG_REQUEST_BODY=false` in production
- [ ] `LOG_RESPONSE_BODY=false` in production
- [ ] `RATE_LIMIT_ENABLED=true` in production
- [ ] Rate limits configured appropriately
- [ ] `REDIS_URL` points to production Redis

### 3. Security Configuration ✓

- [ ] No sensitive data in environment variables committed to git
- [ ] Redis connection secured (password/TLS if accessible externally)
- [ ] Rate limits reviewed and tested
- [ ] Error messages don't expose system internals
- [ ] Logging doesn't capture sensitive data

### 4. Redis Setup ✓

- [ ] Redis server running and accessible
- [ ] Redis version >= 5.0
- [ ] Redis persistence configured (AOF or RDB)
- [ ] Redis memory limit configured
- [ ] Redis password set (if exposed)
- [ ] Redis monitoring enabled
- [ ] Test connection: `redis-cli ping`

### 5. Testing ✓

- [ ] Unit tests pass: `pytest tests/unit/core/test_middleware.py -v`
- [ ] Integration tests completed
- [ ] Load testing performed
- [ ] Rate limiting tested under load
- [ ] Error handling tested with various error types
- [ ] Logging verified in production-like environment
- [ ] No sensitive data in logs confirmed

### 6. Monitoring Setup ✓

- [ ] Log aggregation configured (ELK/Datadog/CloudWatch)
- [ ] Error rate alerts configured (>1% for 5 min)
- [ ] Response time alerts configured (P95 > 1s)
- [ ] Rate limit hit alerts configured
- [ ] Redis health monitoring configured
- [ ] Dashboards created for key metrics

### 7. Performance Verification ✓

- [ ] Response time overhead acceptable (<2ms per request)
- [ ] Memory usage within limits
- [ ] Redis latency acceptable (<2ms)
- [ ] No log volume issues
- [ ] Health check endpoints responding quickly

### 8. Documentation ✓

- [ ] Team trained on middleware functionality
- [ ] Runbook created for common issues
- [ ] Alert response procedures documented
- [ ] Rate limit configuration documented
- [ ] Log format and fields documented

## Production Environment Variables

Create a `.env.production` with these recommended settings:

```bash
# Application
APP_ENV=production
DEBUG=false

# Logging
LOG_LEVEL=WARNING
JSON_LOGS=true
LOG_REQUEST_BODY=false
LOG_RESPONSE_BODY=false
LOG_MAX_BODY_SIZE=1024

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_SECOND=10
RATE_LIMIT_PER_MINUTE=100
RATE_LIMIT_PER_HOUR=1000

# Redis (use your production Redis URL)
REDIS_URL=redis://:password@prod-redis.example.com:6379/0
```

## Deployment Steps

1. **Backup current configuration:**
   ```bash
   cp .env .env.backup
   ```

2. **Update environment variables:**
   ```bash
   cp .env.production .env
   # Verify settings
   cat .env
   ```

3. **Test configuration:**
   ```bash
   # Test Redis connection
   redis-cli -u $REDIS_URL ping
   
   # Test Python imports
   python -c "from core.middleware import *; print('OK')"
   ```

4. **Deploy application:**
   ```bash
   # Your deployment process here
   # e.g., docker build, kubernetes apply, etc.
   ```

5. **Verify deployment:**
   ```bash
   # Check health endpoint
   curl https://your-domain.com/health
   
   # Check rate limiting (should return headers)
   curl -I https://your-domain.com/api/v1/candidates
   
   # Verify logs are structured JSON
   tail -f /var/log/app.log | jq
   ```

6. **Monitor for issues:**
   - Watch error rates in monitoring dashboard
   - Check Redis connection stability
   - Verify rate limits are working
   - Confirm no sensitive data in logs

## Post-Deployment Verification

### 1. Error Handling Test
```bash
# Test non-existent endpoint
curl https://your-domain.com/nonexistent

# Expected: Sanitized 404 error
# Should NOT contain: stack traces, file paths, sensitive data
```

### 2. Rate Limiting Test
```bash
# Make rapid requests
for i in {1..150}; do
  curl -s -o /dev/null -w "%{http_code}\n" https://your-domain.com/api/v1/endpoint
done

# Expected: 200s initially, then 429s
# Check for X-RateLimit-* headers
```

### 3. Logging Test
```bash
# Make a request
curl https://your-domain.com/api/v1/endpoint

# Check logs
tail -n 20 /var/log/app.log | jq

# Verify:
# - Logs are JSON formatted
# - request_id present
# - No sensitive data (passwords, tokens, etc.)
# - Performance metrics included (duration_ms)
```

### 4. Performance Test
```bash
# Check response times
curl -w "@curl-format.txt" -o /dev/null -s https://your-domain.com/api/v1/endpoint

# Expected overhead: <2ms per request
```

### 5. Redis Health Test
```bash
# Check Redis connection
redis-cli -u $REDIS_URL INFO stats

# Check rate limit keys
redis-cli -u $REDIS_URL KEYS "are:ratelimit:*" | head -n 10
```

## Rollback Plan

If issues occur after deployment:

1. **Immediate actions:**
   ```bash
   # Disable rate limiting if causing issues
   export RATE_LIMIT_ENABLED=false
   # Restart application
   
   # Reduce log verbosity if too much volume
   export LOG_LEVEL=ERROR
   # Restart application
   ```

2. **Restore previous version:**
   ```bash
   # Restore backup configuration
   cp .env.backup .env
   
   # Redeploy previous version
   # (use your deployment process)
   ```

3. **Investigate issues:**
   - Check application logs for errors
   - Review Redis logs for connection issues
   - Verify environment variables
   - Test middleware components individually

## Common Issues and Solutions

### Issue: High error rate after deployment

**Solution:**
1. Check logs for specific error types
2. Verify all environment variables are set
3. Confirm Redis is accessible
4. Check for code errors in middleware integration

### Issue: Rate limiting too strict

**Solution:**
```bash
# Adjust limits in .env
RATE_LIMIT_PER_MINUTE=200
RATE_LIMIT_PER_HOUR=2000
# Restart application
```

### Issue: Too many logs / high costs

**Solution:**
```bash
# Increase log level
LOG_LEVEL=ERROR
# Skip more endpoints in should_log_request()
# Restart application
```

### Issue: Redis connection failures

**Solution:**
1. Verify Redis is running: `redis-cli ping`
2. Check Redis URL in `.env`
3. Verify network connectivity
4. Check Redis logs
5. Temporarily disable rate limiting if needed

## Success Criteria

Deployment is successful when:

- ✅ Error rate < 0.1%
- ✅ P95 response time < 500ms
- ✅ Rate limiting working (429s returned when appropriate)
- ✅ No sensitive data in logs (audit sample of logs)
- ✅ Redis healthy and accepting connections
- ✅ Monitoring alerts configured and working
- ✅ No customer-facing issues reported

## Monitoring Dashboard

Create a dashboard with these metrics:

1. **Error Rate**
   - Query: `status_code:5*` count per minute
   - Alert: > 1% for 5 minutes

2. **Response Time**
   - Query: P50, P95, P99 of `duration_ms`
   - Alert: P95 > 1000ms for 5 minutes

3. **Rate Limit Hits**
   - Query: `status_code:429` count per minute
   - Alert: > 100 per minute (investigate traffic)

4. **Redis Health**
   - Query: Redis connection errors
   - Alert: Any connection failure

5. **Request Volume**
   - Query: Total requests per minute
   - Info: Trend analysis

## Contact Information

In case of issues:

- **Runbook**: `docs/runbooks/middleware.md` (create this)
- **On-call**: (your on-call process)
- **Escalation**: (your escalation process)

## Sign-off

Before marking as complete, confirm:

- [ ] Reviewed by: _____________________ Date: _______
- [ ] Tested by: _____________________ Date: _______
- [ ] Approved by: _____________________ Date: _______

## Notes

Additional deployment notes:
```
(Add any environment-specific notes here)
```
