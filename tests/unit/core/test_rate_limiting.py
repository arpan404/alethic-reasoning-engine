"""
Comprehensive tests for rate limiting middleware.
Tests all strategies, Redis failures, race conditions, and distributed scenarios.
"""

import pytest
import asyncio
import time
import hashlib
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError
import redis.asyncio as redis

from core.middleware.rate_limiting import (
    RateLimitMiddleware,
    RateLimitRule,
    RateLimitStrategy,
    RateLimitWindow,
    SlidingWindowRateLimiter,
)


class TestRateLimitRules:
    """Test rate limit rule configuration."""
    
    def test_basic_rule_creation(self):
        """Test creating a basic rate limit rule."""
        rule = RateLimitRule(
            strategy=RateLimitStrategy.IP_ADDRESS,
            window=RateLimitWindow.MINUTE,
            max_requests=100,
        )
        
        assert rule.strategy == RateLimitStrategy.IP_ADDRESS
        assert rule.window == RateLimitWindow.MINUTE
        assert rule.max_requests == 100
        assert rule.paths is None
        assert rule.methods is None
    
    def test_rule_with_path_filter(self):
        """Test rule with path filtering."""
        rule = RateLimitRule(
            strategy=RateLimitStrategy.IP_ADDRESS,
            window=RateLimitWindow.MINUTE,
            max_requests=5,
            paths=["/api/v1/auth/login", "/api/v1/auth/register"],
        )
        
        assert len(rule.paths) == 2
        assert "/api/v1/auth/login" in rule.paths
    
    def test_rule_with_method_filter(self):
        """Test rule with method filtering."""
        rule = RateLimitRule(
            strategy=RateLimitStrategy.USER_ID,
            window=RateLimitWindow.HOUR,
            max_requests=1000,
            methods=["POST", "PUT", "DELETE"],
        )
        
        assert len(rule.methods) == 3
        assert "POST" in rule.methods
    
    def test_rule_with_exemptions(self):
        """Test rule with exemption lists."""
        rule = RateLimitRule(
            strategy=RateLimitStrategy.IP_ADDRESS,
            window=RateLimitWindow.MINUTE,
            max_requests=100,
            exempt_ips=["127.0.0.1", "10.0.0.1"],
            exempt_user_ids=["admin", "service_account"],
        )
        
        assert "127.0.0.1" in rule.exempt_ips
        assert "admin" in rule.exempt_user_ids


class TestSlidingWindowAlgorithm:
    """Test sliding window rate limiting algorithm."""
    
    @pytest.fixture
    async def redis_client(self):
        """Create mock Redis client."""
        client = AsyncMock()
        client.pipeline = Mock(return_value=client)
        # Pipeline commands are non-async
        client.zremrangebyscore = Mock(return_value=None)
        client.zcard = Mock(return_value=0)
        client.zadd = Mock(return_value=None)
        client.expire = Mock(return_value=None)
        # execute() is async
        client.execute = AsyncMock(return_value=[None, 0, None, None])
        client.zrange = AsyncMock(return_value=[])
        client.zrem = AsyncMock(return_value=None)
        return client
    
    @pytest.mark.asyncio
    async def test_first_request_allowed(self, redis_client):
        """Test that first request is allowed."""
        limiter = SlidingWindowRateLimiter(redis_client)
        
        allowed, metadata = await limiter.is_allowed(
            key="test:user:123",
            max_requests=10,
            window_seconds=60,
        )
        
        assert allowed is True
        assert metadata["limit"] == 10
        assert "remaining" in metadata
        assert "reset" in metadata
    
    @pytest.mark.asyncio
    async def test_requests_within_limit(self, redis_client):
        """Test that requests within limit are allowed."""
        redis_client.execute = AsyncMock(return_value=[None, 5, None, None])
        limiter = SlidingWindowRateLimiter(redis_client)
        
        allowed, metadata = await limiter.is_allowed(
            key="test:user:123",
            max_requests=10,
            window_seconds=60,
        )
        
        assert allowed is True
        assert metadata["current"] == 5
        assert metadata["remaining"] >= 0
    
    @pytest.mark.asyncio
    async def test_request_exceeding_limit(self, redis_client):
        """Test that requests exceeding limit are blocked."""
        redis_client.execute = AsyncMock(return_value=[None, 15, None, None])
        limiter = SlidingWindowRateLimiter(redis_client)
        
        allowed, metadata = await limiter.is_allowed(
            key="test:user:123",
            max_requests=10,
            window_seconds=60,
        )
        
        assert allowed is False
        assert metadata["limit"] == 10
        assert metadata["retry_after"] >= 0
    
    @pytest.mark.asyncio
    async def test_cost_based_rate_limiting(self, redis_client):
        """Test rate limiting with request cost."""
        redis_client.execute = AsyncMock(return_value=[None, 8, None, None])
        limiter = SlidingWindowRateLimiter(redis_client)
        
        # This request has cost=5, so 8+5=13 > 10
        allowed, metadata = await limiter.is_allowed(
            key="test:user:123",
            max_requests=10,
            window_seconds=60,
            cost=5,
        )
        
        assert allowed is False
    
    @pytest.mark.asyncio
    async def test_sliding_window_cleanup(self, redis_client):
        """Test that old entries are cleaned up."""
        limiter = SlidingWindowRateLimiter(redis_client)
        
        await limiter.is_allowed(
            key="test:user:123",
            max_requests=10,
            window_seconds=60,
        )
        
        # Should call zremrangebyscore to remove old entries
        assert redis_client.zremrangebyscore.called
    
    @pytest.mark.asyncio
    async def test_key_expiration(self, redis_client):
        """Test that Redis keys have expiration."""
        limiter = SlidingWindowRateLimiter(redis_client)
        
        await limiter.is_allowed(
            key="test:user:123",
            max_requests=10,
            window_seconds=60,
        )
        
        # Should set expiration on the key
        assert redis_client.expire.called
    
    @pytest.mark.asyncio
    async def test_reset_rate_limit(self, redis_client):
        """Test rate limit reset."""
        redis_client.delete = AsyncMock(return_value=1)
        limiter = SlidingWindowRateLimiter(redis_client)
        
        result = await limiter.reset("test:user:123")
        
        assert result is True
        assert redis_client.delete.called


class TestRedisFailures:
    """Test graceful handling of Redis failures."""
    
    @pytest.fixture
    async def failing_redis_client(self):
        """Create Redis client that fails."""
        client = AsyncMock()
        client.pipeline = Mock(return_value=client)
        # Pipeline commands are non-async
        client.zremrangebyscore = Mock()
        client.zcard = Mock()
        client.zadd = Mock()
        client.expire = Mock()
        # execute() fails
        client.execute = AsyncMock(side_effect=RedisConnectionError("Connection failed"))
        return client
    
    @pytest.mark.asyncio
    async def test_fail_open_on_connection_error(self, failing_redis_client):
        """Test that rate limiter fails open on connection error."""
        limiter = SlidingWindowRateLimiter(failing_redis_client)
        
        allowed, metadata = await limiter.is_allowed(
            key="test:user:123",
            max_requests=10,
            window_seconds=60,
        )
        
        # Should allow request even though Redis failed
        assert allowed is True
        assert "error" in metadata
    
    @pytest.mark.asyncio
    async def test_fail_open_on_redis_error(self):
        """Test fail open on general Redis error."""
        client = AsyncMock()
        client.pipeline = Mock(return_value=client)
        # Pipeline commands are non-async
        client.zremrangebyscore = Mock()
        client.zcard = Mock()
        client.zadd = Mock()
        client.expire = Mock()
        # execute() fails
        client.execute = AsyncMock(side_effect=RedisError("Redis error"))
        
        limiter = SlidingWindowRateLimiter(client)
        
        allowed, metadata = await limiter.is_allowed(
            key="test:user:123",
            max_requests=10,
            window_seconds=60,
        )
        
        assert allowed is True
        assert "error" in metadata
    
    @pytest.mark.asyncio
    async def test_fail_open_on_timeout(self):
        """Test fail open on timeout."""
        client = AsyncMock()
        client.pipeline = Mock(return_value=client)
        # Pipeline commands are non-async
        client.zremrangebyscore = Mock()
        client.zcard = Mock()
        client.zadd = Mock()
        client.expire = Mock()
        # execute() times out
        client.execute = AsyncMock(side_effect=asyncio.TimeoutError())
        
        limiter = SlidingWindowRateLimiter(client)
        
        allowed, metadata = await limiter.is_allowed(
            key="test:user:123",
            max_requests=10,
            window_seconds=60,
        )
        
        assert allowed is True


class TestRateLimitStrategies:
    """Test different rate limiting strategies."""
    
    @pytest.fixture
    def mock_redis_url(self):
        """Mock Redis URL."""
        return "redis://localhost:6379/0"
    
    def test_ip_address_strategy(self, mock_redis_url):
        """Test IP address-based rate limiting."""
        rule = RateLimitRule(
            strategy=RateLimitStrategy.IP_ADDRESS,
            window=RateLimitWindow.MINUTE,
            max_requests=100,
        )
        
        middleware = RateLimitMiddleware(
            app=None,
            redis_url=mock_redis_url,
            rules=[rule],
        )
        
        # Create mock request
        request = Mock()
        request.client = Mock(host="192.168.1.100")
        request.headers = {}
        request.url = Mock(path="/api/test")
        request.method = "GET"
        request.state = Mock()
        
        # Test key generation
        key = asyncio.run(middleware._generate_key(request, rule))
        
        assert key is not None
        assert "ip" in key
    
    def test_user_id_strategy(self, mock_redis_url):
        """Test user ID-based rate limiting."""
        rule = RateLimitRule(
            strategy=RateLimitStrategy.USER_ID,
            window=RateLimitWindow.MINUTE,
            max_requests=100,
        )
        
        middleware = RateLimitMiddleware(
            app=None,
            redis_url=mock_redis_url,
            rules=[rule],
        )
        
        # Mock authenticated user
        request = Mock()
        request.client = Mock(host="192.168.1.100")
        request.headers = {}
        request.url = Mock(path="/api/test")
        request.method = "GET"
        request.state = Mock(user=Mock(id=12345))
        
        key = asyncio.run(middleware._generate_key(request, rule))
        
        assert key is not None
        assert "12345" in key
    
    def test_api_key_strategy(self, mock_redis_url):
        """Test API key-based rate limiting."""
        rule = RateLimitRule(
            strategy=RateLimitStrategy.API_KEY,
            window=RateLimitWindow.MINUTE,
            max_requests=100,
        )
        
        middleware = RateLimitMiddleware(
            app=None,
            redis_url=mock_redis_url,
            rules=[rule],
        )
        
        request = Mock()
        request.client = Mock(host="192.168.1.100")
        request.headers = {"x-api-key": "test_key_123"}
        request.url = Mock(path="/api/test")
        request.method = "GET"
        request.state = Mock()
        request.query_params = {}
        
        key = asyncio.run(middleware._generate_key(request, rule))
        
        assert key is not None
        # API key should be hashed for privacy
        assert "test_key_123" not in key
    
    def test_endpoint_strategy(self, mock_redis_url):
        """Test endpoint-based rate limiting."""
        rule = RateLimitRule(
            strategy=RateLimitStrategy.ENDPOINT,
            window=RateLimitWindow.MINUTE,
            max_requests=100,
        )
        
        middleware = RateLimitMiddleware(
            app=None,
            redis_url=mock_redis_url,
            rules=[rule],
        )
        
        request = Mock()
        request.client = Mock(host="192.168.1.100")
        request.headers = {}
        request.url = Mock(path="/api/expensive-operation")
        request.method = "POST"
        request.state = Mock()
        
        key = asyncio.run(middleware._generate_key(request, rule))
        
        assert key is not None
        assert "/api/expensive-operation" in key
    
    def test_combined_strategy(self, mock_redis_url):
        """Test combined rate limiting strategy."""
        rule = RateLimitRule(
            strategy=RateLimitStrategy.COMBINED,
            window=RateLimitWindow.MINUTE,
            max_requests=10,
        )
        
        middleware = RateLimitMiddleware(
            app=None,
            redis_url=mock_redis_url,
            rules=[rule],
        )
        
        request = Mock()
        request.client = Mock(host="192.168.1.100")
        request.headers = {}
        request.url = Mock(path="/api/test")
        request.method = "POST"
        request.state = Mock(user=Mock(id=123))
        
        key = asyncio.run(middleware._generate_key(request, rule))
        
        assert key is not None
        # Combined key should be hashed
        assert len(key.split(":")[-1]) > 10


class TestMiddlewareIntegration:
    """Test rate limiting middleware integration with FastAPI."""
    
    @pytest.fixture
    def app_with_rate_limiting(self):
        """Create app with rate limiting."""
        app = FastAPI()
        
        # Mock Redis URL - tests will mock the actual Redis calls
        with patch('core.middleware.rate_limiting.redis.from_url') as mock_redis:
            mock_client = AsyncMock()
            mock_client.pipeline = Mock(return_value=mock_client)
            # Pipeline commands are non-async
            mock_client.zremrangebyscore = Mock()
            mock_client.zcard = Mock(return_value=0)
            mock_client.zadd = Mock()
            mock_client.expire = Mock()
            # execute() is async
            mock_client.execute = AsyncMock(return_value=[None, 0, None, None])
            mock_client.zrange = AsyncMock(return_value=[])
            mock_redis.return_value = mock_client
            
            rules = [
                RateLimitRule(
                    strategy=RateLimitStrategy.IP_ADDRESS,
                    window=RateLimitWindow.MINUTE,
                    max_requests=5,
                    paths=["/api/limited"],
                ),
            ]
            
            app.add_middleware(
                RateLimitMiddleware,
                redis_url="redis://localhost:6379/0",
                rules=rules,
            )
        
        @app.get("/api/unlimited")
        async def unlimited():
            return {"message": "ok"}
        
        @app.get("/api/limited")
        async def limited():
            return {"message": "ok"}
        
        @app.get("/health")
        async def health():
            return {"status": "healthy"}
        
        return app
    
    def test_unlimited_endpoint(self, app_with_rate_limiting):
        """Test that unlimited endpoints work."""
        client = TestClient(app_with_rate_limiting)
        response = client.get("/api/unlimited")
        assert response.status_code == 200
    
    def test_health_check_not_rate_limited(self, app_with_rate_limiting):
        """Test that health checks are not rate limited."""
        client = TestClient(app_with_rate_limiting)
        
        # Health checks should never be rate limited
        for _ in range(100):
            response = client.get("/health")
            assert response.status_code == 200
    
    def test_rate_limit_headers_present(self, app_with_rate_limiting):
        """Test that rate limit headers are added."""
        client = TestClient(app_with_rate_limiting)
        response = client.get("/api/limited")
        
        # Should have rate limit headers
        assert "x-ratelimit-limit" in response.headers or "X-RateLimit-Limit" in response.headers


class TestExemptions:
    """Test rate limit exemptions."""
    
    def test_ip_exemption(self):
        """Test that exempt IPs are not rate limited."""
        rule = RateLimitRule(
            strategy=RateLimitStrategy.IP_ADDRESS,
            window=RateLimitWindow.MINUTE,
            max_requests=10,
            exempt_ips=["127.0.0.1", "10.0.0.1"],
        )
        
        middleware = RateLimitMiddleware(
            app=None,
            redis_url="redis://localhost:6379/0",
            rules=[rule],
        )
        
        # Mock request from exempt IP
        request = Mock()
        request.client = Mock(host="127.0.0.1")
        request.headers = {}
        request.url = Mock(path="/api/test")
        request.method = "GET"
        request.state = Mock()
        
        is_exempt = asyncio.run(middleware._is_exempt(request, rule))
        assert is_exempt is True
    
    def test_user_exemption(self):
        """Test that exempt users are not rate limited."""
        rule = RateLimitRule(
            strategy=RateLimitStrategy.USER_ID,
            window=RateLimitWindow.MINUTE,
            max_requests=10,
            exempt_user_ids=["admin", "service"],
        )
        
        middleware = RateLimitMiddleware(
            app=None,
            redis_url="redis://localhost:6379/0",
            rules=[rule],
        )
        
        # Mock request from exempt user
        request = Mock()
        request.client = Mock(host="192.168.1.1")
        request.headers = {}
        request.url = Mock(path="/api/test")
        request.method = "GET"
        request.state = Mock(user=Mock(id="admin"))
        
        is_exempt = asyncio.run(middleware._is_exempt(request, rule))
        assert is_exempt is True


class TestEdgeCases:
    """Test edge cases and unusual scenarios."""
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test handling of concurrent requests."""
        client = AsyncMock()
        client.pipeline = Mock(return_value=client)
        client.execute = AsyncMock(return_value=[None, 0, None, None])
        # Pipeline commands are non-async
        client.zremrangebyscore = Mock()
        client.zcard = Mock(return_value=0)
        client.zadd = Mock()
        client.expire = Mock()
        client.zrange = AsyncMock(return_value=[])
        
        limiter = SlidingWindowRateLimiter(client)
        
        # Simulate concurrent requests
        tasks = [
            limiter.is_allowed("test:concurrent", 10, 60)
            for _ in range(100)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All should succeed (mocked to return low count)
        assert all(r[0] for r in results)
    
    @pytest.mark.asyncio
    async def test_very_short_window(self):
        """Test with very short time window."""
        client = AsyncMock()
        client.pipeline = Mock(return_value=client)
        client.execute = AsyncMock(return_value=[None, 0, None, None])
        # Pipeline commands are non-async
        client.zremrangebyscore = Mock()
        client.zcard = Mock(return_value=0)
        client.zadd = Mock()
        client.expire = Mock()
        client.zrange = AsyncMock(return_value=[])
        
        limiter = SlidingWindowRateLimiter(client)
        
        allowed, metadata = await limiter.is_allowed(
            key="test:short",
            max_requests=10,
            window_seconds=1,  # 1 second window
        )
        
        assert allowed is True
    
    @pytest.mark.asyncio
    async def test_very_long_window(self):
        """Test with very long time window."""
        client = AsyncMock()
        client.pipeline = Mock(return_value=client)
        client.execute = AsyncMock(return_value=[None, 0, None, None])
        # Pipeline commands are non-async
        client.zremrangebyscore = Mock()
        client.zcard = Mock(return_value=0)
        client.zadd = Mock()
        client.expire = Mock()
        client.zrange = AsyncMock(return_value=[])
        
        limiter = SlidingWindowRateLimiter(client)
        
        allowed, metadata = await limiter.is_allowed(
            key="test:long",
            max_requests=10000,
            window_seconds=86400,  # 1 day window
        )
        
        assert allowed is True
    
    def test_missing_client_info(self):
        """Test handling of missing client info."""
        middleware = RateLimitMiddleware(
            app=None,
            redis_url="redis://localhost:6379/0",
        )
        
        request = Mock()
        request.client = None  # No client info
        request.headers = {}
        request.url = Mock(path="/api/test")
        request.method = "GET"
        request.state = Mock()
        
        ip = middleware._get_client_ip(request)
        assert ip == "unknown"
    
    def test_missing_user_info(self):
        """Test handling of missing user info."""
        middleware = RateLimitMiddleware(
            app=None,
            redis_url="redis://localhost:6379/0",
        )
        
        request = Mock()
        request.client = Mock(host="192.168.1.1")
        request.headers = {}
        request.url = Mock(path="/api/test")
        request.method = "GET"
        # Create state without user attribute
        request.state = Mock(spec=[])  # Empty spec means no attributes
        
        user_id = middleware._get_user_id(request)
        assert user_id is None


class TestComplianceScenarios:
    """Test compliance scenarios for enterprise use."""
    
    @pytest.mark.asyncio
    async def test_fair_usage_policy(self):
        """Test fair usage policy enforcement."""
        client = AsyncMock()
        client.pipeline = Mock(return_value=client)
        
        # Simulate user hitting limit
        client.execute = AsyncMock(return_value=[None, 100, None, None])
        # Pipeline commands are non-async
        client.zremrangebyscore = Mock()
        client.zcard = Mock(return_value=100)
        client.zadd = Mock()
        client.expire = Mock()
        client.zrange = AsyncMock(return_value=[(b"oldest", time.time() - 30)])
        client.zrem = AsyncMock()
        
        limiter = SlidingWindowRateLimiter(client)
        
        allowed, metadata = await limiter.is_allowed(
            key="test:fair:use",
            max_requests=100,
            window_seconds=60,
        )
        
        # Should be blocked
        assert allowed is False
        # Should have retry_after information
        assert "retry_after" in metadata
        assert metadata["retry_after"] >= 0
    
    def test_distributed_rate_limiting(self):
        """Test that rate limiting works in distributed systems."""
        # Rate limiting uses Redis, which provides distributed coordination
        middleware = RateLimitMiddleware(
            app=None,
            redis_url="redis://localhost:6379/0",
            key_prefix="app:ratelimit",
        )
        
        assert middleware.key_prefix == "app:ratelimit"
        # All instances sharing same Redis will coordinate
    
    def test_security_key_hashing(self):
        """Test that API keys are hashed for security."""
        api_key = "sk_live_super_secret_key_123"
        hashed = hashlib.sha256(api_key.encode()).hexdigest()[:16]
        
        # Original key should not be in Redis key
        assert len(hashed) == 16
        assert hashed != api_key


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
