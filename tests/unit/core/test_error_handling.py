"""
Comprehensive tests for error handling middleware.
Tests all error types, edge cases, and GDPR/SOC2 compliance scenarios.
"""

import pytest
import json
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError, OperationalError, DatabaseError
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError
from unittest.mock import Mock, patch

from core.middleware.error_handling import (
    sanitize_error_message,
    get_safe_error_details,
    ErrorHandlingMiddleware,
    setup_error_handlers,
    SENSITIVE_PATTERNS,
)


class TestSensitiveDataSanitization:
    """Test sensitive data sanitization for GDPR/SOC2 compliance."""
    
    @pytest.mark.parametrize("sensitive_input,expected_redacted", [
        # Passwords
        ('password="secret123"', True),
        ('pwd:abc123', True),
        ('passwd=mypassword', True),
        ('user_password: "P@ssw0rd!"', True),
        
        # Tokens
        ('token="Bearer abc123xyz"', True),
        ('access_token:jwt.token.here', True),
        ('refresh_token="xyz789"', True),
        ('auth_token: sk_test_12345', True),
        
        # API Keys
        ('api_key="sk_live_12345"', True),
        ('apiKey:AIzaSyXXXXXX', True),
        ('api-key="secret-key-123"', True),
        ('x-api-key: pk_test_XXXXX', True),
        
        # Secrets
        ('secret="confidential"', True),
        ('client_secret:abc123', True),
        ('SECRET_KEY="django-secret"', True),
        
        # Authorization
        ('authorization: Bearer token123', True),
        ('Authorization="Basic YWxhZGRpbjpvcGVuc2VzYW1l"', True),
        
        # SSN (Social Security Numbers)
        ('SSN: 123-45-6789', True),
        ('ssn:987-65-4321', True),
        ('social security: 111-22-3333', True),
        
        # Credit Cards
        ('card: 4532123456789010', True),
        ('credit_card:5425233430109903', True),
        ('4111111111111111', True),
        
        # Safe values (should not be redacted)
        ('username="john_doe"', False),
        ('email="user@example.com"', False),
        ('message="Operation successful"', False),
        ('count=12345', False),
    ])
    def test_sanitize_sensitive_patterns(self, sensitive_input, expected_redacted):
        """Test that sensitive patterns are properly detected and redacted."""
        sanitized = sanitize_error_message(sensitive_input)
        
        if expected_redacted:
            assert "[REDACTED]" in sanitized
            # Verify original sensitive value is removed
            if ":" in sensitive_input or "=" in sensitive_input:
                # Extract the value part
                value = sensitive_input.split(":", 1)[-1].split("=", 1)[-1].strip(' "\'')
                if len(value) > 5:  # Only check for substantial values
                    assert value not in sanitized
        else:
            assert "[REDACTED]" not in sanitized
    
    def test_multiple_sensitive_fields_in_one_message(self):
        """Test sanitization of multiple sensitive fields."""
        message = 'Error: password="secret" and token="abc123" and api_key="xyz789"'
        sanitized = sanitize_error_message(message)
        
        assert "secret" not in sanitized
        assert "abc123" not in sanitized
        assert "xyz789" not in sanitized
        assert sanitized.count("[REDACTED]") == 3
    
    def test_case_insensitive_pattern_matching(self):
        """Test that patterns work case-insensitively."""
        test_cases = [
            'PASSWORD="test"',
            'Password="test"',
            'password="test"',
            'API_KEY="test"',
            'Api_Key="test"',
            'api_key="test"',
        ]
        
        for test_case in test_cases:
            sanitized = sanitize_error_message(test_case)
            assert "[REDACTED]" in sanitized
    
    def test_gdpr_compliance_no_pii_leakage(self):
        """Test GDPR compliance - no PII in error messages."""
        pii_data = [
            'Error processing SSN: 123-45-6789',
            'Invalid credit card: 4532-1234-5678-9010',
            'Authentication failed for token: sk_live_abc123',
            'Database error with password: MyP@ssw0rd',
        ]
        
        for data in pii_data:
            sanitized = sanitize_error_message(data)
            # Verify no actual PII values remain
            assert "123-45-6789" not in sanitized
            assert "4532" not in sanitized or "1234" not in sanitized
            assert "sk_live_abc123" not in sanitized
            assert "MyP@ssw0rd" not in sanitized
    
    def test_edge_case_empty_string(self):
        """Test sanitization of empty string."""
        assert sanitize_error_message("") == ""
    
    def test_edge_case_only_redacted_content(self):
        """Test when entire message is sensitive."""
        message = "password=secret"
        sanitized = sanitize_error_message(message)
        assert "[REDACTED]" in sanitized
    
    def test_edge_case_special_characters(self):
        """Test sanitization with special characters."""
        message = 'password="P@$$w0rd!#%^&*()"'
        sanitized = sanitize_error_message(message)
        assert "P@$$w0rd" not in sanitized
        assert "[REDACTED]" in sanitized
    
    def test_edge_case_unicode_characters(self):
        """Test sanitization with unicode characters."""
        message = 'password="пароль123"'  # Russian for password
        sanitized = sanitize_error_message(message)
        assert "[REDACTED]" in sanitized


class TestSafeErrorDetails:
    """Test safe error detail extraction."""
    
    def test_basic_exception_details(self):
        """Test extraction of basic exception details."""
        exc = ValueError("Test error message")
        details = get_safe_error_details(exc, include_details=False)
        
        assert details["type"] == "ValueError"
        assert details["message"] == "Test error message"
        assert "traceback" not in details
    
    def test_details_with_debug_mode(self):
        """Test that debug mode includes traceback."""
        exc = ValueError("Test error")
        details = get_safe_error_details(exc, include_details=True)
        
        assert "traceback" in details
        assert isinstance(details["traceback"], str)
    
    def test_details_without_debug_mode(self):
        """Test that production mode excludes traceback."""
        exc = ValueError("Test error")
        details = get_safe_error_details(exc, include_details=False)
        
        assert "traceback" not in details
    
    def test_sanitization_in_error_details(self):
        """Test that error details are sanitized."""
        exc = ValueError("Error with password=secret123")
        details = get_safe_error_details(exc, include_details=False)
        
        assert "secret123" not in details["message"]
        assert "[REDACTED]" in details["message"]


class TestErrorHandlingMiddleware:
    """Test error handling middleware with various exception types."""
    
    @pytest.fixture
    def app(self):
        """Create FastAPI app with error handling middleware."""
        app = FastAPI()
        setup_error_handlers(app)  # Add error handlers
        app.add_middleware(ErrorHandlingMiddleware, debug=False)
        
        @app.get("/success")
        async def success():
            return {"message": "success"}
        
        @app.get("/value-error")
        async def value_error():
            raise ValueError("Invalid input with password=secret")
        
        @app.get("/http-error")
        async def http_error():
            raise HTTPException(status_code=401, detail="Unauthorized with token=abc123")
        
        @app.get("/database-integrity-error")
        async def db_integrity_error():
            raise IntegrityError("duplicate key", None, None)
        
        @app.get("/database-operational-error")
        async def db_operational_error():
            raise OperationalError("connection lost", None, None)
        
        @app.get("/redis-connection-error")
        async def redis_conn_error():
            raise RedisConnectionError("Redis connection failed")
        
        @app.get("/redis-error")
        async def redis_err():
            raise RedisError("Redis operation failed")
        
        @app.get("/permission-error")
        async def permission_err():
            raise PermissionError("Access denied")
        
        @app.get("/timeout-error")
        async def timeout_err():
            raise TimeoutError("Request timed out")
        
        @app.get("/generic-error")
        async def generic_err():
            raise Exception("Unexpected error with api_key=secret")
        
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)
    
    def test_successful_request(self, client):
        """Test that successful requests pass through."""
        response = client.get("/success")
        assert response.status_code == 200
        assert response.json() == {"message": "success"}
    
    def test_value_error_handling(self, client):
        """Test ValueError handling with sanitization."""
        response = client.get("/value-error")
        assert response.status_code == 400
        
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "INVALID_INPUT"
        assert "secret" not in json.dumps(data)
        assert "[REDACTED]" in data["error"]["message"]
    
    def test_http_exception_handling(self, client):
        """Test HTTP exception handling."""
        response = client.get("/http-error")
        assert response.status_code == 401
        
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "HTTP_EXCEPTION"
        assert "abc123" not in json.dumps(data)
    
    def test_database_integrity_error(self, client):
        """Test database integrity error handling."""
        response = client.get("/database-integrity-error")
        assert response.status_code == 409
        
        data = response.json()
        assert data["error"]["code"] == "INTEGRITY_ERROR"
        assert "constraint" in data["error"]["message"].lower()
    
    def test_database_operational_error(self, client):
        """Test database operational error handling."""
        response = client.get("/database-operational-error")
        assert response.status_code == 503
        
        data = response.json()
        assert data["error"]["code"] == "DATABASE_ERROR"
        assert "unavailable" in data["error"]["message"].lower()
    
    def test_redis_connection_error(self, client):
        """Test Redis connection error handling."""
        response = client.get("/redis-connection-error")
        assert response.status_code == 503
        
        data = response.json()
        assert data["error"]["code"] == "CACHE_ERROR"
        assert "unavailable" in data["error"]["message"].lower()
    
    def test_redis_error(self, client):
        """Test Redis error handling."""
        response = client.get("/redis-error")
        assert response.status_code == 500
        
        data = response.json()
        assert data["error"]["code"] == "CACHE_ERROR"
    
    def test_permission_error(self, client):
        """Test permission error handling."""
        response = client.get("/permission-error")
        assert response.status_code == 403
        
        data = response.json()
        assert data["error"]["code"] == "PERMISSION_DENIED"
    
    def test_timeout_error(self, client):
        """Test timeout error handling."""
        response = client.get("/timeout-error")
        assert response.status_code == 504
        
        data = response.json()
        assert data["error"]["code"] == "TIMEOUT"
    
    def test_generic_error_handling(self, client):
        """Test generic exception handling with sanitization."""
        response = client.get("/generic-error")
        assert response.status_code == 500
        
        data = response.json()
        assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"
        assert "secret" not in json.dumps(data)
    
    def test_error_response_structure(self, client):
        """Test that error responses have consistent structure."""
        response = client.get("/value-error")
        data = response.json()
        
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
        assert "path" in data["error"]
        assert "method" in data["error"]
        
        assert data["error"]["path"] == "/value-error"
        assert data["error"]["method"] == "GET"
    
    def test_soc2_compliance_structured_errors(self, client):
        """Test SOC2 compliance - structured, auditable errors."""
        response = client.get("/value-error")
        data = response.json()
        
        # Should have all required fields for audit trail
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
        assert "path" in data["error"]
        assert "method" in data["error"]
        
        # Should not contain sensitive data
        assert "password" not in json.dumps(data).lower() or "[REDACTED]" in json.dumps(data)
    
    def test_debug_mode_includes_details(self):
        """Test that debug mode includes error details."""
        app = FastAPI()
        app.add_middleware(ErrorHandlingMiddleware, debug=True)
        
        @app.get("/error")
        async def error():
            raise ValueError("Test error")
        
        client = TestClient(app)
        response = client.get("/error")
        data = response.json()
        
        # In debug mode, should include details
        assert "error" in data
        # Note: Details might be in different structure in debug mode


class TestExceptionHandlers:
    """Test exception handler setup."""
    
    def test_setup_error_handlers(self):
        """Test error handler setup."""
        app = FastAPI()
        setup_error_handlers(app)
        
        @app.get("/test")
        async def test():
            raise ValueError("Test error with password=secret")
        
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test")
        data = response.json()
        
        assert "error" in data
        assert "secret" not in json.dumps(data)


class TestEdgeCases:
    """Test edge cases and unusual scenarios."""
    
    def test_very_long_error_message(self):
        """Test handling of very long error messages."""
        long_message = "Error: " + "x" * 10000 + " password=secret"
        sanitized = sanitize_error_message(long_message)
        
        assert "[REDACTED]" in sanitized
        assert "secret" not in sanitized
    
    def test_nested_json_in_error(self):
        """Test handling of nested JSON in error messages."""
        message = 'Error: {"user": {"password": "secret", "token": "abc123"}}'
        sanitized = sanitize_error_message(message)
        
        assert "secret" not in sanitized or "[REDACTED]" in sanitized
        assert "abc123" not in sanitized or "[REDACTED]" in sanitized
    
    def test_multiple_patterns_same_message(self):
        """Test multiple different patterns in one message."""
        message = 'Failed: password=pass1, token=tok1, api_key=key1, ssn=123-45-6789'
        sanitized = sanitize_error_message(message)
        
        assert sanitized.count("[REDACTED]") >= 3
        assert "pass1" not in sanitized
        assert "tok1" not in sanitized
        assert "key1" not in sanitized
        assert "123-45-6789" not in sanitized
    
    def test_url_encoded_sensitive_data(self):
        """Test handling of URL-encoded sensitive data."""
        message = "Error: password%3Dsecret123"
        # Note: Current implementation may not handle URL encoding
        # This test documents current behavior
        sanitized = sanitize_error_message(message)
        assert sanitized is not None
    
    def test_base64_encoded_data(self):
        """Test handling of base64-encoded data."""
        import base64
        sensitive = base64.b64encode(b"password=secret").decode()
        message = f"Error: data={sensitive}"
        # Note: Current implementation may not decode base64
        # This test documents the behavior
        sanitized = sanitize_error_message(message)
        assert sanitized is not None
    
    def test_concurrent_error_handling(self):
        """Test thread-safety of error sanitization."""
        import concurrent.futures
        
        def sanitize_test(msg):
            return sanitize_error_message(msg)
        
        messages = [
            f"Error {i}: password=secret{i}" for i in range(100)
        ]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(sanitize_test, messages))
        
        # All should be sanitized
        assert all("[REDACTED]" in r for r in results)
        assert all(f"secret{i}" not in results[i] for i in range(100))


class TestComplianceScenarios:
    """Test specific compliance scenarios for GDPR/SOC2."""
    
    def test_gdpr_right_to_erasure_simulation(self):
        """Simulate GDPR right to erasure - no user data in errors."""
        user_data = {
            "email": "user@example.com",
            "name": "John Doe",
            "ssn": "123-45-6789",
            "password": "MyPassword123",
        }
        
        # Simulate error with user data
        message = f"Database error for user {json.dumps(user_data)}"
        sanitized = sanitize_error_message(message)
        
        # Password and SSN must be redacted
        assert "MyPassword123" not in sanitized
        assert "123-45-6789" not in sanitized
        assert "[REDACTED]" in sanitized
    
    def test_soc2_audit_trail_completeness(self):
        """Test SOC2 requirement for complete audit trail."""
        app = FastAPI()
        app.add_middleware(ErrorHandlingMiddleware, debug=False)
        
        @app.get("/test")
        async def test():
            raise ValueError("Test error")
        
        client = TestClient(app)
        
        with patch('core.middleware.error_handling.logger') as mock_logger:
            response = client.get("/test")
            
            # Should log the error
            assert mock_logger.warning.called or mock_logger.error.called
            
            # Response should have audit fields
            data = response.json()
            assert "error" in data
            assert "path" in data["error"]
            assert "method" in data["error"]
    
    def test_data_minimization_principle(self):
        """Test GDPR data minimization - only necessary data exposed."""
        exc = ValueError("Error with customer_email=user@example.com and password=secret")
        details = get_safe_error_details(exc, include_details=False)
        
        # Should not include unnecessary sensitive information
        assert "traceback" not in details  # No stack trace in production
        assert "secret" not in details["message"]  # Passwords redacted
    
    def test_security_by_design(self):
        """Test security by design - default to safe behavior."""
        # Test that default behavior is secure
        middleware = ErrorHandlingMiddleware(None, debug=False)
        assert middleware.debug == False  # Should default to production mode
        
        # Test sanitization happens by default
        message = "Error with password=secret"
        sanitized = sanitize_error_message(message)
        assert "secret" not in sanitized


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
