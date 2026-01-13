"""
Tests for middleware components.
Run with: pytest tests/unit/core/test_middleware.py -v
"""

import pytest
import asyncio
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
import json

from core.middleware.error_handling import (
    sanitize_error_message,
    get_safe_error_details,
    ErrorHandlingMiddleware,
)
from core.middleware.logging import (
    is_sensitive_field,
    mask_sensitive_data,
    mask_headers,
    StructuredLoggingMiddleware,
)
from core.middleware.rate_limiting import (
    RateLimitMiddleware,
    RateLimitRule,
    RateLimitStrategy,
    RateLimitWindow,
    SlidingWindowRateLimiter,
)


class TestErrorHandling:
    """Tests for error handling middleware."""
    
    def test_sanitize_password(self):
        """Test password sanitization."""
        message = 'Error: password="secret123"'
        sanitized = sanitize_error_message(message)
        assert "secret123" not in sanitized
        assert "[REDACTED]" in sanitized
    
    def test_sanitize_token(self):
        """Test token sanitization."""
        message = "Invalid token: Bearer abc123xyz"
        sanitized = sanitize_error_message(message)
        assert "abc123xyz" not in sanitized
        assert "[REDACTED]" in sanitized
    
    def test_sanitize_api_key(self):
        """Test API key sanitization."""
        message = 'api_key="sk_test_12345"'
        sanitized = sanitize_error_message(message)
        assert "sk_test_12345" not in sanitized
        assert "[REDACTED]" in sanitized
    
    def test_sanitize_ssn(self):
        """Test SSN sanitization."""
        message = "SSN: 123-45-6789 is invalid"
        sanitized = sanitize_error_message(message)
        assert "123-45-6789" not in sanitized
        assert "[REDACTED]" in sanitized
    
    def test_get_safe_error_details(self):
        """Test safe error detail extraction."""
        exc = ValueError("Invalid input: password=secret")
        details = get_safe_error_details(exc, include_details=False)
        
        assert details["type"] == "ValueError"
        assert "password" in details["message"]
        assert "secret" not in details["message"]
        assert "traceback" not in details
    
    def test_get_safe_error_details_with_debug(self):
        """Test error details in debug mode."""
        exc = ValueError("Test error")
        details = get_safe_error_details(exc, include_details=True)
        
        assert "traceback" in details


class TestLogging:
    """Tests for logging middleware."""
    
    def test_is_sensitive_field(self):
        """Test sensitive field detection."""
        assert is_sensitive_field("password")
        assert is_sensitive_field("api_key")
        assert is_sensitive_field("secret_token")
        assert is_sensitive_field("bearer_token")
        assert is_sensitive_field("credit_card_number")
        assert not is_sensitive_field("username")
        assert not is_sensitive_field("email")
    
    def test_mask_sensitive_data_dict(self):
        """Test masking sensitive data in dictionary."""
        data = {
            "username": "john",
            "password": "secret123",
            "email": "john@example.com",
            "api_key": "sk_test_12345",
        }
        
        masked = mask_sensitive_data(data)
        
        assert masked["username"] == "john"
        assert masked["password"] == "[REDACTED]"
        assert "[EMAIL]" in masked["email"]
        assert masked["api_key"] == "[REDACTED]"
    
    def test_mask_sensitive_data_nested(self):
        """Test masking nested sensitive data."""
        data = {
            "user": {
                "name": "John",
                "credentials": {
                    "password": "secret",
                    "token": "abc123",
                }
            }
        }
        
        masked = mask_sensitive_data(data)
        
        assert masked["user"]["name"] == "John"
        assert masked["user"]["credentials"]["password"] == "[REDACTED]"
        assert masked["user"]["credentials"]["token"] == "[REDACTED]"
    
    def test_mask_sensitive_data_list(self):
        """Test masking sensitive data in lists."""
        data = [
            {"username": "user1", "password": "pass1"},
            {"username": "user2", "password": "pass2"},
        ]
        
        masked = mask_sensitive_data(data)
        
        assert masked[0]["username"] == "user1"
        assert masked[0]["password"] == "[REDACTED]"
        assert masked[1]["password"] == "[REDACTED]"
    
    def test_mask_pii_in_strings(self):
        """Test PII masking in strings."""
        data = "Contact john@example.com or call 555-123-4567"
        masked = mask_sensitive_data(data)
        
        assert "john@example.com" not in masked
        assert "[EMAIL]" in masked
        assert "555-123-4567" not in masked
        assert "[PHONE]" in masked
    
    def test_mask_headers(self):
        """Test header masking."""
        headers = {
            "authorization": "Bearer token123",
            "content-type": "application/json",
            "x-api-key": "secret_key",
            "user-agent": "Mozilla/5.0",
        }
        
        masked = mask_headers(headers)
        
        assert "Bearer [REDACTED]" in masked["authorization"]
        assert masked["content-type"] == "application/json"
        assert masked["x-api-key"] == "[REDACTED]"
        assert masked["user-agent"] == "Mozilla/5.0"
    
    def test_max_depth_protection(self):
        """Test protection against infinite recursion."""
        # Create circular reference
        data = {"level": 1}
        current = data
        for i in range(15):
            current["nested"] = {"level": i + 2}
            current = current["nested"]
        
        # Should not crash, will stop at max depth
        masked = mask_sensitive_data(data)
        assert masked is not None


class TestRateLimiting:
    """Tests for rate limiting middleware."""
    
    @pytest.fixture
    async def redis_mock(self):
        """Mock Redis client."""
        redis = AsyncMock()
        # pipeline() returns self (non-async call)
        redis.pipeline = Mock(return_value=redis)
        # Pipeline commands are non-async
        redis.zremrangebyscore = Mock(return_value=None)
        redis.zcard = Mock(return_value=5)
        redis.zadd = Mock(return_value=None)
        redis.expire = Mock(return_value=None)
        # execute() is async
        redis.execute = AsyncMock(return_value=[None, 5, None, None])
        redis.zrange = AsyncMock(return_value=[])
        redis.zrem = AsyncMock(return_value=None)
        return redis
    
    @pytest.mark.asyncio
    async def test_sliding_window_allows_request(self, redis_mock):
        """Test that requests within limit are allowed."""
        limiter = SlidingWindowRateLimiter(redis_mock)
        
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
    async def test_sliding_window_blocks_exceeded(self, redis_mock):
        """Test that requests exceeding limit are blocked."""
        redis_mock.execute = AsyncMock(return_value=[None, 15, None, None])
        limiter = SlidingWindowRateLimiter(redis_mock)
        
        allowed, metadata = await limiter.is_allowed(
            key="test:user:123",
            max_requests=10,
            window_seconds=60,
        )
        
        assert allowed is False
        assert metadata["limit"] == 10
        assert "retry_after" in metadata
    
    @pytest.mark.asyncio
    async def test_rate_limit_fail_open_on_redis_error(self, redis_mock):
        """Test that rate limiter fails open when Redis is unavailable."""
        redis_mock.execute = AsyncMock(side_effect=Exception("Redis error"))
        limiter = SlidingWindowRateLimiter(redis_mock)
        
        allowed, metadata = await limiter.is_allowed(
            key="test:user:123",
            max_requests=10,
            window_seconds=60,
        )
        
        # Should allow request even with Redis error
        assert allowed is True
        assert "error" in metadata
    
    def test_rate_limit_rule_creation(self):
        """Test rate limit rule creation."""
        rule = RateLimitRule(
            strategy=RateLimitStrategy.IP_ADDRESS,
            window=RateLimitWindow.MINUTE,
            max_requests=100,
            paths=["/api/v1/users"],
            methods=["POST", "PUT"],
        )
        
        assert rule.strategy == RateLimitStrategy.IP_ADDRESS
        assert rule.window == RateLimitWindow.MINUTE
        assert rule.max_requests == 100
        assert "/api/v1/users" in rule.paths
        assert "POST" in rule.methods


class TestIntegration:
    """Integration tests for middleware."""
    
    def test_error_handling_integration(self):
        """Test error handling in a FastAPI app."""
        app = FastAPI()
        app.add_middleware(ErrorHandlingMiddleware, debug=False)
        
        @app.get("/error")
        async def error_endpoint():
            raise ValueError("Test error with password=secret")
        
        client = TestClient(app)
        response = client.get("/error")
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "secret" not in json.dumps(data)
        assert "[REDACTED]" in data["error"]["message"]
    
    def test_logging_skip_health_check(self):
        """Test that health checks are not logged."""
        app = FastAPI()
        app.add_middleware(StructuredLoggingMiddleware)
        
        @app.get("/health")
        async def health():
            return {"status": "healthy"}
        
        client = TestClient(app)
        with patch("core.middleware.logging.logger") as mock_logger:
            response = client.get("/health")
            assert response.status_code == 200
            # Should not log health check requests
            assert not mock_logger.info.called


class TestSecurityCompliance:
    """Tests for security compliance."""
    
    def test_no_sensitive_data_in_errors(self):
        """Verify no sensitive data leaks in error messages."""
        sensitive_strings = [
            "password=secret123",
            "token=abc123xyz",
            "api_key=sk_test_12345",
            "secret=confidential",
            "123-45-6789",  # SSN
            "4532-1234-5678-9010",  # Credit card
        ]
        
        for sensitive in sensitive_strings:
            message = f"Error occurred: {sensitive}"
            sanitized = sanitize_error_message(message)
            
            # For field=value patterns, check that values are redacted
            if "=" in sensitive:
                field, value = sensitive.split("=", 1)
                # Field name can remain for debugging, but value must be redacted
                assert value not in sanitized, f"Sensitive value '{value}' leaked"
            else:
                # For standalone PII (SSN, credit cards), entire value should be redacted
                assert sensitive not in sanitized, f"Sensitive data '{sensitive}' leaked"
            
            # Should contain redaction marker
            assert "[REDACTED]" in sanitized
    
    def test_no_pii_in_logs(self):
        """Verify PII is masked in log data."""
        data = {
            "username": "john_doe",
            "email": "john@example.com",
            "phone": "555-123-4567",
            "ssn": "123-45-6789",
            "message": "User created successfully",
        }
        
        masked = mask_sensitive_data(data)
        
        # Check that PII is masked
        assert "john@example.com" not in json.dumps(masked)
        assert "555-123-4567" not in json.dumps(masked)
        assert "123-45-6789" not in json.dumps(masked)
        
        # Check that non-sensitive data is preserved
        assert masked["username"] == "john_doe"
        assert masked["message"] == "User created successfully"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
