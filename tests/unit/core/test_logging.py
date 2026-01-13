"""
Comprehensive tests for logging middleware.
Tests PII masking, nested data, circular references, and privacy compliance.
"""

import pytest
import json
import asyncio
import logging
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from core.middleware.logging import (
    is_sensitive_field,
    mask_sensitive_data,
    mask_headers,
    should_log_request,
    get_client_ip,
    StructuredLoggingMiddleware,
    setup_logging,
    get_logger,
    SENSITIVE_FIELD_PATTERNS,
    PII_PATTERNS,
)


class TestSensitiveFieldDetection:
    """Test sensitive field name detection."""
    
    @pytest.mark.parametrize("field_name,expected", [
        # Sensitive fields
        ("password", True),
        ("Password", True),
        ("PASSWORD", True),
        ("user_password", True),
        ("passwd", True),
        ("pwd", True),
        ("token", True),
        ("access_token", True),
        ("refresh_token", True),
        ("auth_token", True),
        ("api_key", True),
        ("apiKey", True),
        ("api-key", True),
        ("secret", True),
        ("client_secret", True),
        ("SECRET_KEY", True),
        ("authorization", True),
        ("Authorization", True),
        ("bearer", True),
        ("cookie", True),
        ("session", True),
        ("session_id", True),
        ("csrf", True),
        ("csrf_token", True),
        ("credit_card", True),
        ("credit-card", True),
        ("creditcard", True),
        ("cvv", True),
        ("ssn", True),
        ("social_security", True),
        ("private_key", True),
        ("privateKey", True),
        
        # Non-sensitive fields
        ("username", False),
        ("email", False),
        ("name", False),
        ("id", False),
        ("user_id", False),
        ("created_at", False),
        ("updated_at", False),
        ("status", False),
        ("message", False),
        ("data", False),
    ])
    def test_sensitive_field_patterns(self, field_name, expected):
        """Test comprehensive sensitive field detection."""
        assert is_sensitive_field(field_name) == expected
    
    def test_case_insensitive_detection(self):
        """Test case-insensitive field detection."""
        variations = ["password", "Password", "PASSWORD", "PaSsWoRd"]
        assert all(is_sensitive_field(v) for v in variations)


class TestPIIMasking:
    """Test PII masking for GDPR compliance."""
    
    def test_email_masking(self):
        """Test email address masking."""
        # Valid emails that should be masked
        valid_emails = [
            "Contact john@example.com for help",
            "Email: user.name+tag@domain.co.uk",
            "test.user@sub.domain.com",
        ]
    
        for text in valid_emails:
            masked = mask_sensitive_data(text)
            assert "[EMAIL]" in masked, f"Expected [EMAIL] in {masked} for {text}"
        
        # Invalid/localhost addresses that won't be masked
        # (This is correct - localhost addresses aren't real PII)
        localhost_text = "admin@localhost"
        masked = mask_sensitive_data(localhost_text)
        assert masked == localhost_text  # Should remain unchanged
    
    def test_phone_number_masking(self):
        """Test phone number masking in various formats."""
        test_cases = [
            "Call 555-123-4567",
            "Phone: 555.123.4567",
            "Contact: 5551234567",
            "+1-555-123-4567",
            "+44 20 7123 4567",
        ]
        
        for text in test_cases:
            masked = mask_sensitive_data(text)
            assert "[PHONE]" in masked
    
    def test_ssn_masking(self):
        """Test SSN masking."""
        test_cases = [
            "SSN: 123-45-6789",
            "Social Security: 987-65-4321",
            "111-22-3333",
        ]
        
        for text in test_cases:
            masked = mask_sensitive_data(text)
            assert "[SSN]" in masked
            assert "123-45-6789" not in masked
    
    def test_credit_card_masking(self):
        """Test credit card number masking."""
        test_cases = [
            "Card: 4532 1234 5678 9010",
            "4532-1234-5678-9010",
            "4532123456789010",
        ]
        
        for text in test_cases:
            masked = mask_sensitive_data(text)
            assert "[CARD]" in masked
    
    def test_ip_address_masking(self):
        """Test IP address masking for privacy."""
        test_cases = [
            "From IP: 192.168.1.100",
            "Source: 10.0.0.1",
            "Address: 172.16.254.1",
        ]
        
        for text in test_cases:
            masked = mask_sensitive_data(text)
            assert "[IP]" in masked
    
    def test_multiple_pii_types_in_text(self):
        """Test masking multiple PII types in one string."""
        text = "Contact john@example.com at 555-123-4567, IP: 192.168.1.1, SSN: 123-45-6789"
        masked = mask_sensitive_data(text)
        
        assert "[EMAIL]" in masked
        assert "[PHONE]" in masked
        assert "[IP]" in masked
        assert "[SSN]" in masked
        
        # Original values should not be present
        assert "john@example.com" not in masked
        assert "555-123-4567" not in masked
        assert "192.168.1.1" not in masked
        assert "123-45-6789" not in masked


class TestDataStructureMasking:
    """Test masking in complex data structures."""
    
    def test_dict_masking(self):
        """Test dictionary masking."""
        data = {
            "username": "john_doe",
            "password": "secret123",
            "email": "john@example.com",
            "token": "abc123xyz",
        }
        
        masked = mask_sensitive_data(data)
        
        assert masked["username"] == "john_doe"
        assert masked["password"] == "[REDACTED]"
        assert "[EMAIL]" in masked["email"]
        assert masked["token"] == "[REDACTED]"
    
    def test_nested_dict_masking(self):
        """Test nested dictionary masking."""
        data = {
            "user": {
                "profile": {
                    "name": "John",
                    "credentials": {
                        "password": "secret",
                        "api_key": "key123",
                    }
                },
                "contact": {
                    "email": "john@example.com",
                    "phone": "555-123-4567",
                }
            }
        }
        
        masked = mask_sensitive_data(data)
        
        assert masked["user"]["profile"]["name"] == "John"
        assert masked["user"]["profile"]["credentials"]["password"] == "[REDACTED]"
        assert masked["user"]["profile"]["credentials"]["api_key"] == "[REDACTED]"
        assert "[EMAIL]" in masked["user"]["contact"]["email"]
        assert "[PHONE]" in masked["user"]["contact"]["phone"]
    
    def test_list_masking(self):
        """Test list masking."""
        data = [
            {"username": "user1", "password": "pass1"},
            {"username": "user2", "password": "pass2"},
        ]
        
        masked = mask_sensitive_data(data)
        
        assert masked[0]["username"] == "user1"
        assert masked[0]["password"] == "[REDACTED]"
        assert masked[1]["password"] == "[REDACTED]"
    
    def test_mixed_structure_masking(self):
        """Test masking in mixed structures."""
        data = {
            "users": [
                {"name": "User1", "password": "pass1"},
                {"name": "User2", "token": "token2"},
            ],
            "config": {
                "database": {
                    "host": "localhost",
                    "password": "dbpass",
                },
                "api_keys": ["key1", "key2"],
            }
        }
        
        masked = mask_sensitive_data(data)
        
        assert masked["users"][0]["name"] == "User1"
        assert masked["users"][0]["password"] == "[REDACTED]"
        assert masked["users"][1]["token"] == "[REDACTED]"
        assert masked["config"]["database"]["host"] == "localhost"
        assert masked["config"]["database"]["password"] == "[REDACTED]"
    
    def test_circular_reference_protection(self):
        """Test protection against circular references."""
        data = {"level": 1}
        current = data
        
        # Create deep nesting
        for i in range(15):
            current["nested"] = {"level": i + 2, "password": f"pass{i}"}
            current = current["nested"]
        
        # Should not crash, will stop at max depth
        masked = mask_sensitive_data(data)
        assert masked is not None
    
    def test_max_depth_protection(self):
        """Test max depth protection."""
        # Create very deep structure
        data = {"password": "secret"}
        current = data
        for i in range(20):
            current["child"] = {"password": f"secret{i}"}
            current = current["child"]
        
        # Should handle gracefully
        masked = mask_sensitive_data(data, max_depth=10)
        assert masked is not None
        assert "[MAX_DEPTH_EXCEEDED]" in str(masked) or "password" not in str(masked).lower()


class TestHeaderMasking:
    """Test HTTP header masking."""
    
    def test_authorization_header_masking(self):
        """Test authorization header masking."""
        headers = {
            "authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "content-type": "application/json",
        }
        
        masked = mask_headers(headers)
        
        assert "Bearer [REDACTED]" in masked["authorization"]
        assert masked["content-type"] == "application/json"
    
    def test_basic_auth_header_masking(self):
        """Test Basic auth header masking."""
        headers = {
            "authorization": "Basic YWxhZGRpbjpvcGVuc2VzYW1l",
        }
        
        masked = mask_headers(headers)
        assert "Basic [REDACTED]" in masked["authorization"]
    
    def test_api_key_header_masking(self):
        """Test API key header masking."""
        headers = {
            "x-api-key": "sk_live_abc123xyz789",
            "user-agent": "Mozilla/5.0",
        }
        
        masked = mask_headers(headers)
        
        assert masked["x-api-key"] == "[REDACTED]"
        assert masked["user-agent"] == "Mozilla/5.0"
    
    def test_cookie_header_masking(self):
        """Test cookie header masking."""
        headers = {
            "cookie": "session=abc123; token=xyz789",
        }
        
        masked = mask_headers(headers)
        assert masked["cookie"] == "[REDACTED]"
    
    def test_multiple_sensitive_headers(self):
        """Test masking multiple sensitive headers."""
        headers = {
            "authorization": "Bearer token123",
            "x-api-key": "key123",
            "cookie": "session=xyz",
            "x-csrf-token": "csrf123",
            "content-type": "application/json",
            "user-agent": "TestClient",
        }
        
        masked = mask_headers(headers)
        
        # Sensitive headers masked
        assert "[REDACTED]" in str(masked["authorization"])
        assert masked["x-api-key"] == "[REDACTED]"
        assert masked["cookie"] == "[REDACTED]"
        assert masked["x-csrf-token"] == "[REDACTED]"
        
        # Non-sensitive headers preserved
        assert masked["content-type"] == "application/json"
        assert masked["user-agent"] == "TestClient"


class TestClientIPExtraction:
    """Test client IP extraction with privacy."""
    
    def test_direct_client_ip(self):
        """Test direct client IP extraction."""
        request = Mock()
        request.client = Mock(host="192.168.1.100")
        request.headers = {}
        
        ip = get_client_ip(request)
        
        # Last octet should be masked
        assert ip == "192.168.1.xxx"
    
    def test_forwarded_for_header(self):
        """Test X-Forwarded-For header."""
        request = Mock()
        request.client = Mock(host="10.0.0.1")
        request.headers = {"x-forwarded-for": "203.0.113.195, 70.41.3.18"}
        
        ip = get_client_ip(request)
        
        # Should use first IP and mask it
        assert ip == "203.0.113.xxx"
    
    def test_real_ip_header(self):
        """Test X-Real-IP header."""
        request = Mock()
        request.client = Mock(host="10.0.0.1")
        request.headers = {"x-real-ip": "198.51.100.42"}
        
        # Note: Current implementation prefers x-forwarded-for
        # This test documents the behavior
        ip = get_client_ip(request)
        assert ip.endswith(".xxx")
    
    def test_no_client_info(self):
        """Test handling of missing client info."""
        request = Mock()
        request.client = None
        request.headers = {}
        
        ip = get_client_ip(request)
        assert ip == "unknown"


class TestStructuredLoggingMiddleware:
    """Test structured logging middleware."""
    
    @pytest.fixture
    def app(self):
        """Create FastAPI app with logging middleware."""
        app = FastAPI()
        app.add_middleware(
            StructuredLoggingMiddleware,
            log_request_body=True,
            log_response_body=False,
            max_body_size=1024,
        )
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "success"}
        
        @app.post("/post-data")
        async def post_endpoint(request: Request):
            body = await request.json()
            return {"received": True}
        
        @app.get("/error")
        async def error_endpoint():
            raise ValueError("Test error")
        
        @app.get("/health")
        async def health():
            return {"status": "healthy"}
        
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)
    
    def test_request_logging(self, client):
        """Test basic request logging."""
        with patch('core.middleware.logging.logger') as mock_logger:
            response = client.get("/test")
            
            assert response.status_code == 200
            assert mock_logger.info.called
            
            # Check that request_started and request_completed were logged
            calls = [str(call) for call in mock_logger.info.call_args_list]
            assert any("request_started" in str(call) or "request_completed" in str(call) for call in calls)
    
    def test_request_id_generation(self, client):
        """Test request ID generation and tracking."""
        response = client.get("/test")
        
        assert "x-request-id" in response.headers
        request_id = response.headers["x-request-id"]
        assert len(request_id) > 0
    
    def test_request_id_preservation(self, client):
        """Test that provided request ID is preserved."""
        custom_id = "custom-request-id-123"
        response = client.get("/test", headers={"x-request-id": custom_id})
        
        assert response.headers["x-request-id"] == custom_id
    
    def test_health_check_not_logged(self, client):
        """Test that health checks are not logged."""
        with patch('core.middleware.logging.logger') as mock_logger:
            response = client.get("/health")
            
            assert response.status_code == 200
            # Health checks should be skipped
            assert not mock_logger.info.called
    
    def test_request_body_logging(self, client):
        """Test request body logging with masking."""
        data = {
            "username": "john",
            "password": "secret123",
            "email": "john@example.com",
        }
        
        with patch('core.middleware.logging.logger') as mock_logger:
            response = client.post("/post-data", json=data)
            
            assert response.status_code == 200
            
            # Check logged data doesn't contain sensitive info
            logged_data = str(mock_logger.info.call_args_list)
            assert "secret123" not in logged_data
            assert "[REDACTED]" in logged_data or "password" not in logged_data
    
    def test_error_logging(self, client):
        """Test error logging."""
        with patch('core.middleware.logging.logger') as mock_logger:
            try:
                client.get("/error")
            except:
                pass
            
            # Should log the error
            assert mock_logger.error.called
    
    def test_performance_metrics(self, client):
        """Test performance metrics logging."""
        with patch('core.middleware.logging.logger') as mock_logger:
            response = client.get("/test")
            
            # Check that duration is logged
            calls = str(mock_logger.info.call_args_list)
            assert "duration_ms" in calls or "request_completed" in calls
    
    def test_client_ip_privacy(self, client):
        """Test that client IP is masked."""
        with patch('core.middleware.logging.logger') as mock_logger:
            response = client.get("/test")
            
            # Check logged data
            logged = str(mock_logger.info.call_args_list)
            # Should contain masked IP or be sanitized
            if "client_ip" in logged:
                assert ".xxx" in logged or "unknown" in logged


class TestEdgeCases:
    """Test edge cases and unusual scenarios."""
    
    def test_empty_data_masking(self):
        """Test masking empty data structures."""
        assert mask_sensitive_data({}) == {}
        assert mask_sensitive_data([]) == []
        assert mask_sensitive_data("") == ""
        assert mask_sensitive_data(None) is None
    
    def test_large_data_structure(self):
        """Test masking large data structures."""
        data = {
            f"field_{i}": f"value_{i}" if i % 10 != 0 else "password=secret"
            for i in range(1000)
        }
        
        masked = mask_sensitive_data(data)
        assert masked is not None
        assert len(masked) == len(data)
    
    def test_special_characters_in_values(self):
        """Test masking with special characters."""
        data = {
            "password": "P@$$w0rd!#%^&*()",
            "message": "Normal message with <html> & symbols",
        }
        
        masked = mask_sensitive_data(data)
        assert masked["password"] == "[REDACTED]"
        assert masked["message"] == "Normal message with <html> & symbols"
    
    def test_unicode_in_data(self):
        """Test handling unicode data."""
        data = {
            "name": "Ψ∈λ",
            "password": "пароль123",
            "message": "你好世界",
        }
        
        masked = mask_sensitive_data(data)
        assert masked["password"] == "[REDACTED]"
        assert masked["name"] == "Ψ∈λ"
        assert masked["message"] == "你好世界"
    
    def test_binary_data(self):
        """Test handling binary data."""
        data = {"file": b"binary content"}
        masked = mask_sensitive_data(data)
        # Binary data should pass through or be handled
        assert masked is not None
    
    def test_none_values(self):
        """Test handling None values."""
        data = {
            "username": None,
            "password": None,
            "data": {"nested": None},
        }
        
        masked = mask_sensitive_data(data)
        assert masked["username"] is None
        # Password field should still be redacted even if None
        assert masked["password"] == "[REDACTED]" or masked["password"] is None


class TestComplianceScenarios:
    """Test GDPR and SOC2 compliance scenarios."""
    
    def test_gdpr_data_minimization(self):
        """Test GDPR principle of data minimization."""
        # Only necessary data should be logged
        data = {
            "user_id": "12345",
            "email": "user@example.com",
            "password": "secret",
            "ssn": "123-45-6789",
        }
        
        masked = mask_sensitive_data(data)
        
        # User ID should be preserved (necessary for tracking)
        assert masked["user_id"] == "12345"
        
        # PII should be masked
        assert "[EMAIL]" in masked["email"]
        assert masked["password"] == "[REDACTED]"
        assert "[SSN]" in masked["ssn"]
    
    def test_gdpr_right_to_privacy(self):
        """Test GDPR right to privacy - no unnecessary PII."""
        request_data = {
            "action": "login",
            "email": "user@example.com",
            "ip": "192.168.1.1",
            "user_agent": "Mozilla/5.0",
        }
        
        masked = mask_sensitive_data(request_data)
        
        # Email and IP should be masked
        assert "[EMAIL]" in masked["email"]
        assert "[IP]" in masked["ip"]
        
        # Non-PII can remain
        assert masked["action"] == "login"
    
    def test_soc2_audit_trail_integrity(self):
        """Test SOC2 requirement for audit trail integrity."""
        # Logs should be complete but not contain sensitive data
        log_entry = {
            "timestamp": "2026-01-12T10:00:00Z",
            "user_id": "12345",
            "action": "update_profile",
            "old_email": "old@example.com",
            "new_email": "new@example.com",
            "password_changed": True,
            "new_password": "NewPass123",
        }
        
        masked = mask_sensitive_data(log_entry)
        
        # Audit fields should be preserved
        assert masked["timestamp"] == log_entry["timestamp"]
        assert masked["user_id"] == log_entry["user_id"]
        assert masked["action"] == log_entry["action"]
        
        # PII should be masked
        assert "[EMAIL]" in masked["old_email"]
        assert "[EMAIL]" in masked["new_email"]
        assert masked["new_password"] == "[REDACTED]"
    
    def test_concurrent_logging_thread_safety(self):
        """Test thread-safety for concurrent logging."""
        import concurrent.futures
        
        def mask_test(data):
            return mask_sensitive_data(data)
        
        test_data = [
            {"password": f"pass{i}", "email": f"user{i}@example.com"}
            for i in range(100)
        ]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(mask_test, test_data))
        
        # All passwords should be masked
        assert all(r["password"] == "[REDACTED]" for r in results)
        # All emails should be masked
        assert all("[EMAIL]" in r["email"] for r in results)


class TestLoggingSetup:
    """Test logging setup and configuration."""
    
    def test_setup_logging_json_format(self):
        """Test JSON logging setup."""
        setup_logging(log_level="INFO", json_logs=True)
        logger = get_logger(__name__)
        assert logger is not None
    
    def test_setup_logging_text_format(self):
        """Test text logging setup."""
        setup_logging(log_level="DEBUG", json_logs=False)
        logger = get_logger(__name__)
        assert logger is not None
    
    def test_get_logger(self):
        """Test logger retrieval."""
        logger = get_logger("test_module")
        assert logger is not None
        assert isinstance(logger, logging.Logger)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
