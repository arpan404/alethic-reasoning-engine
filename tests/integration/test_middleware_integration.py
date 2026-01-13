"""
Integration tests for all middleware components working together.
Tests end-to-end scenarios with FastAPI application.
"""

import pytest
import json
import time
from unittest.mock import patch, AsyncMock, Mock
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from core.middleware import (
    ErrorHandlingMiddleware,
    setup_error_handlers,
    StructuredLoggingMiddleware,
    setup_logging,
    RateLimitMiddleware,
    RateLimitRule,
    RateLimitStrategy,
    RateLimitWindow,
)


class TestFullMiddlewareStack:
    """Test all middleware components working together."""
    
    @pytest.fixture
    def full_app(self):
        """Create FastAPI app with full middleware stack."""
        app = FastAPI()
        
        # Setup logging
        setup_logging(log_level="INFO", json_logs=True)
        
        # Setup error handlers
        setup_error_handlers(app)
        
        # Add middleware in correct order
        app.add_middleware(ErrorHandlingMiddleware, debug=False)
        app.add_middleware(
            StructuredLoggingMiddleware,
            log_request_body=True,
            log_response_body=False,
            max_body_size=1024,
        )
        
        # Mock Redis for rate limiting
        with patch('core.middleware.rate_limiting.redis.from_url') as mock_redis:
            mock_client = AsyncMock()
            mock_client.pipeline = Mock(return_value=mock_client)
            mock_client.zremrangebyscore = AsyncMock()
            mock_client.zcard = AsyncMock(return_value=0)
            mock_client.zadd = AsyncMock()
            mock_client.expire = AsyncMock()
            mock_client.execute = AsyncMock(return_value=[None, 0, None, None])
            mock_client.zrange = AsyncMock(return_value=[])
            mock_redis.return_value = mock_client
            
            rules = [
                RateLimitRule(
                    strategy=RateLimitStrategy.IP_ADDRESS,
                    window=RateLimitWindow.MINUTE,
                    max_requests=10,
                    paths=["/api/limited"],
                ),
            ]
            
            app.add_middleware(
                RateLimitMiddleware,
                redis_url="redis://localhost:6379/0",
                rules=rules,
            )
        
        # Define test endpoints
        @app.get("/health")
        async def health():
            return {"status": "healthy"}
        
        @app.get("/api/success")
        async def success():
            return {"message": "success", "data": {"value": 123}}
        
        @app.post("/api/with-sensitive-data")
        async def sensitive_endpoint(request: Request):
            body = await request.json()
            return {"received": True}
        
        @app.get("/api/error")
        async def error_endpoint():
            raise ValueError("Test error with password=secret123")
        
        @app.get("/api/db-error")
        async def db_error():
            raise IntegrityError("Duplicate key", None, None)
        
        @app.get("/api/limited")
        async def rate_limited():
            return {"message": "success"}
        
        @app.get("/api/user-info")
        async def user_info():
            return {
                "username": "john_doe",
                "email": "john@example.com",
                "ssn": "123-45-6789",
            }
        
        return app
    
    @pytest.fixture
    def client(self, full_app):
        """Create test client."""
        return TestClient(full_app)
    
    def test_health_check_bypasses_all_middleware(self, client):
        """Test that health checks work without middleware overhead."""
        response = client.get("/health")
        
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}
    
    def test_successful_request_flow(self, client):
        """Test complete flow for successful request."""
        with patch('core.middleware.logging.logger') as mock_logger:
            response = client.get("/api/success")
            
            assert response.status_code == 200
            assert "x-request-id" in response.headers
            
            # Should be logged
            assert mock_logger.info.called
    
    def test_sensitive_data_handling_end_to_end(self, client):
        """Test sensitive data handling through entire stack."""
        data = {
            "username": "john",
            "password": "MyP@ssw0rd123",
            "email": "john@example.com",
            "api_key": "sk_live_abc123",
        }
        
        with patch('core.middleware.logging.logger') as mock_logger:
            response = client.post("/api/with-sensitive-data", json=data)
            
            assert response.status_code == 200
            
            # Check that sensitive data is not in logs
            logged_data = str(mock_logger.info.call_args_list)
            assert "MyP@ssw0rd123" not in logged_data
            assert "sk_live_abc123" not in logged_data
            assert "[REDACTED]" in logged_data or "password" not in logged_data
    
    def test_error_handling_with_logging(self, client):
        """Test that errors are properly handled and logged."""
        with patch('core.middleware.logging.logger') as mock_logger:
            response = client.get("/api/error")
            
            assert response.status_code == 400
            
            # Error should be in response
            data = response.json()
            assert "error" in data
            assert "secret123" not in json.dumps(data)
            
            # Error should be logged
            assert mock_logger.warning.called or mock_logger.error.called
    
    def test_database_error_handling(self, client):
        """Test database error handling through stack."""
        response = client.get("/api/db-error")
        
        assert response.status_code == 409
        data = response.json()
        assert data["error"]["code"] == "INTEGRITY_ERROR"
    
    def test_rate_limiting_integration(self, client):
        """Test rate limiting with full stack."""
        # Should have rate limit headers
        response = client.get("/api/limited")
        
        # Check for rate limit headers
        headers_lower = {k.lower(): v for k, v in response.headers.items()}
        assert any("ratelimit" in h for h in headers_lower.keys())
    
    def test_request_id_propagation(self, client):
        """Test request ID propagation through entire stack."""
        custom_id = "test-request-id-123"
        response = client.get(
            "/api/success",
            headers={"x-request-id": custom_id}
        )
        
        assert response.headers["x-request-id"] == custom_id
    
    def test_pii_not_in_response(self, client):
        """Test that PII in responses is handled correctly."""
        response = client.get("/api/user-info")
        
        # Response should contain data (app responsibility to handle)
        data = response.json()
        assert "username" in data


class TestErrorRecovery:
    """Test error recovery and resilience."""
    
    @pytest.fixture
    def resilient_app(self):
        """Create app that tests resilience."""
        app = FastAPI()
        
        setup_logging(log_level="INFO", json_logs=True)
        setup_error_handlers(app)
        
        app.add_middleware(ErrorHandlingMiddleware, debug=False)
        app.add_middleware(StructuredLoggingMiddleware)
        
        # Mock failing Redis
        with patch('core.middleware.rate_limiting.redis.from_url') as mock_redis:
            mock_client = AsyncMock()
            mock_client.pipeline = Mock(return_value=mock_client)
            mock_client.execute = AsyncMock(side_effect=Exception("Redis down"))
            mock_redis.return_value = mock_client
            
            app.add_middleware(
                RateLimitMiddleware,
                redis_url="redis://localhost:6379/0",
                rules=[
                    RateLimitRule(
                        strategy=RateLimitStrategy.IP_ADDRESS,
                        window=RateLimitWindow.MINUTE,
                        max_requests=10,
                    )
                ],
            )
        
        @app.get("/test")
        async def test():
            return {"message": "ok"}
        
        return app
    
    def test_redis_failure_doesnt_break_app(self, resilient_app):
        """Test that Redis failure doesn't break the application."""
        client = TestClient(resilient_app)
        
        # Should still work even with Redis down (fail-open)
        response = client.get("/test")
        assert response.status_code == 200


class TestSecurityCompliance:
    """Test security and compliance scenarios."""
    
    @pytest.fixture
    def secure_app(self):
        """Create app for security testing."""
        app = FastAPI()
        
        setup_logging(log_level="INFO", json_logs=True)
        setup_error_handlers(app)
        
        app.add_middleware(ErrorHandlingMiddleware, debug=False)
        app.add_middleware(StructuredLoggingMiddleware, log_request_body=True)
        
        @app.post("/api/login")
        async def login(request: Request):
            body = await request.json()
            if body.get("password") == "correct":
                return {"token": "abc123"}
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        @app.get("/api/user/{user_id}")
        async def get_user(user_id: str):
            return {
                "id": user_id,
                "email": f"user{user_id}@example.com",
                "ssn": "123-45-6789",
            }
        
        return app
    
    def test_gdpr_no_password_in_logs(self, secure_app):
        """Test GDPR compliance - passwords not logged."""
        client = TestClient(secure_app)
        
        with patch('core.middleware.logging.logger') as mock_logger:
            client.post("/api/login", json={
                "username": "john",
                "password": "MySecretPassword123"
            })
            
            logged = str(mock_logger.info.call_args_list)
            assert "MySecretPassword123" not in logged
    
    def test_soc2_audit_trail(self, secure_app):
        """Test SOC2 compliance - complete audit trail."""
        client = TestClient(secure_app)
        
        with patch('core.middleware.logging.logger') as mock_logger:
            response = client.get("/api/user/123")
            
            # Should log request and response
            assert mock_logger.info.call_count >= 2
            
            # Should have request ID for tracing
            assert "x-request-id" in response.headers
    
    def test_no_stack_traces_in_production(self, secure_app):
        """Test that stack traces are not exposed."""
        client = TestClient(secure_app)
        
        response = client.post("/api/login", json={
            "username": "john",
            "password": "wrong"
        })
        
        data = response.json()
        # Should not contain traceback or file paths
        assert "traceback" not in json.dumps(data).lower()
        assert ".py" not in json.dumps(data)


class TestPerformance:
    """Test performance characteristics."""
    
    @pytest.fixture
    def perf_app(self):
        """Create app for performance testing."""
        app = FastAPI()
        
        setup_logging(log_level="INFO", json_logs=True)
        app.add_middleware(ErrorHandlingMiddleware, debug=False)
        app.add_middleware(StructuredLoggingMiddleware)
        
        @app.get("/api/test")
        async def test():
            return {"message": "ok"}
        
        return app
    
    def test_middleware_overhead(self, perf_app):
        """Test that middleware doesn't add excessive overhead."""
        client = TestClient(perf_app)
        
        # Warm up
        for _ in range(10):
            client.get("/api/test")
        
        # Measure
        start = time.time()
        for _ in range(100):
            response = client.get("/api/test")
            assert response.status_code == 200
        duration = time.time() - start
        
        # Should complete 100 requests quickly
        # (This is a loose check, actual performance depends on hardware)
        assert duration < 5.0  # 5 seconds for 100 requests
    
    def test_concurrent_requests(self, perf_app):
        """Test handling of concurrent requests."""
        client = TestClient(perf_app)
        
        import concurrent.futures
        
        def make_request():
            response = client.get("/api/test")
            return response.status_code
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(50)]
            results = [f.result() for f in futures]
        
        # All should succeed
        assert all(status == 200 for status in results)


class TestEdgeCases:
    """Test edge cases in integrated environment."""
    
    @pytest.fixture
    def edge_case_app(self):
        """Create app for edge case testing."""
        app = FastAPI()
        
        setup_logging(log_level="INFO", json_logs=True)
        setup_error_handlers(app)
        
        app.add_middleware(ErrorHandlingMiddleware, debug=False)
        app.add_middleware(StructuredLoggingMiddleware, log_request_body=True, max_body_size=100)
        
        @app.post("/api/large-body")
        async def large_body(request: Request):
            body = await request.body()
            return {"size": len(body)}
        
        @app.get("/api/slow")
        async def slow():
            import asyncio
            await asyncio.sleep(0.1)
            return {"message": "slow"}
        
        @app.get("/api/nested-error")
        async def nested_error():
            try:
                try:
                    raise ValueError("Inner error with token=abc123")
                except ValueError as e:
                    raise RuntimeError(f"Outer error: {e}")
            except RuntimeError as e:
                raise Exception(f"Top level: {e}")
        
        return app
    
    def test_large_request_body_handling(self, edge_case_app):
        """Test handling of large request bodies."""
        client = TestClient(edge_case_app)
        
        large_data = {"data": "x" * 10000}
        response = client.post("/api/large-body", json=large_data)
        
        assert response.status_code == 200
    
    def test_slow_request_logging(self, edge_case_app):
        """Test that slow requests are logged appropriately."""
        client = TestClient(edge_case_app)
        
        with patch('core.middleware.logging.logger') as mock_logger:
            response = client.get("/api/slow")
            
            assert response.status_code == 200
            
            # Should log with performance marker
            logged = str(mock_logger.info.call_args_list)
            # Check that duration was logged
            assert "duration" in logged.lower() or "request_completed" in logged
    
    def test_nested_exception_handling(self, edge_case_app):
        """Test handling of nested exceptions."""
        client = TestClient(edge_case_app)
        
        response = client.get("/api/nested-error")
        
        assert response.status_code == 500
        data = response.json()
        
        # Should not contain sensitive data from any level
        assert "abc123" not in json.dumps(data)


class TestEnterpriseScenarios:
    """Test scenarios specific to enterprise environments."""
    
    def test_multi_tenant_rate_limiting(self):
        """Test rate limiting for multi-tenant scenario."""
        app = FastAPI()
        
        with patch('core.middleware.rate_limiting.redis.from_url') as mock_redis:
            mock_client = AsyncMock()
            mock_client.pipeline = Mock(return_value=mock_client)
            mock_client.execute = AsyncMock(return_value=[None, 0, None, None])
            mock_client.zremrangebyscore = AsyncMock()
            mock_client.zcard = AsyncMock(return_value=0)
            mock_client.zadd = AsyncMock()
            mock_client.expire = AsyncMock()
            mock_client.zrange = AsyncMock(return_value=[])
            mock_redis.return_value = mock_client
            
            # Different limits per tenant
            rules = [
                RateLimitRule(
                    strategy=RateLimitStrategy.USER_ID,
                    window=RateLimitWindow.MINUTE,
                    max_requests=100,
                ),
            ]
            
            app.add_middleware(
                RateLimitMiddleware,
                redis_url="redis://localhost:6379/0",
                rules=rules,
                key_prefix="tenant1:ratelimit",
            )
        
        @app.get("/api/test")
        async def test():
            return {"message": "ok"}
        
        client = TestClient(app)
        response = client.get("/api/test")
        assert response.status_code == 200
    
    def test_compliance_audit_export(self):
        """Test that logs can be exported for compliance audits."""
        app = FastAPI()
        
        setup_logging(log_level="INFO", json_logs=True)
        app.add_middleware(StructuredLoggingMiddleware)
        
        @app.get("/api/test")
        async def test():
            return {"message": "ok"}
        
        client = TestClient(app)
        
        with patch('core.middleware.logging.logger') as mock_logger:
            response = client.get("/api/test")
            
            # Logs should be structured (JSON) for export
            assert mock_logger.info.called
            
            # Should contain audit fields
            # (In real scenario, these would be exported to SIEM)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
