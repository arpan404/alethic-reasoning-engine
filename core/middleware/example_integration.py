"""
Example integration of all middleware components.
Shows how to properly configure and use the middleware in a FastAPI application.
"""

from fastapi import FastAPI
from core.config import settings
from core.middleware.error_handling import (
    ErrorHandlingMiddleware,
    setup_error_handlers,
)
from core.middleware.logging import (
    StructuredLoggingMiddleware,
    setup_logging,
)
from core.middleware.rate_limiting import (
    RateLimitMiddleware,
    RateLimitRule,
    RateLimitStrategy,
    RateLimitWindow,
)


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application with all middleware.
    
    Returns:
        Configured FastAPI application
    """
    # Initialize FastAPI app
    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        docs_url="/api/docs" if settings.debug else None,
        redoc_url="/api/redoc" if settings.debug else None,
    )
    
    # Setup structured logging (do this first)
    setup_logging(
        log_level=settings.log_level,
        json_logs=settings.json_logs,
    )
    
    # Setup error handlers
    setup_error_handlers(app)
    
    # Add middleware (order matters - they execute in reverse order)
    # 1. Error handling (outermost - catches all errors)
    app.add_middleware(
        ErrorHandlingMiddleware,
        debug=settings.debug,
    )
    
    # 2. Logging middleware (logs all requests/responses)
    app.add_middleware(
        StructuredLoggingMiddleware,
        log_request_body=settings.log_request_body,
        log_response_body=settings.log_response_body,
        max_body_size=settings.log_max_body_size,
    )
    
    # 3. Rate limiting (innermost - only applied to valid requests)
    if settings.rate_limit_enabled:
        # Define custom rate limit rules
        rate_limit_rules = [
            # Strict limits for authentication endpoints
            RateLimitRule(
                strategy=RateLimitStrategy.IP_ADDRESS,
                window=RateLimitWindow.MINUTE,
                max_requests=5,
                paths=['/api/v1/auth/login', '/api/v1/auth/register', '/api/v1/auth/forgot-password'],
                methods=['POST'],
            ),
            # Strict limits for password reset
            RateLimitRule(
                strategy=RateLimitStrategy.IP_ADDRESS,
                window=RateLimitWindow.HOUR,
                max_requests=3,
                paths=['/api/v1/auth/reset-password'],
                methods=['POST'],
            ),
            # User-specific rate limits
            RateLimitRule(
                strategy=RateLimitStrategy.USER_ID,
                window=RateLimitWindow.SECOND,
                max_requests=settings.rate_limit_per_second,
            ),
            RateLimitRule(
                strategy=RateLimitStrategy.USER_ID,
                window=RateLimitWindow.MINUTE,
                max_requests=settings.rate_limit_per_minute,
            ),
            RateLimitRule(
                strategy=RateLimitStrategy.USER_ID,
                window=RateLimitWindow.HOUR,
                max_requests=settings.rate_limit_per_hour,
            ),
            # Global IP-based rate limits (backup for unauthenticated requests)
            RateLimitRule(
                strategy=RateLimitStrategy.IP_ADDRESS,
                window=RateLimitWindow.MINUTE,
                max_requests=100,
            ),
            RateLimitRule(
                strategy=RateLimitStrategy.IP_ADDRESS,
                window=RateLimitWindow.HOUR,
                max_requests=1000,
            ),
            # API endpoint specific limits (for expensive operations)
            RateLimitRule(
                strategy=RateLimitStrategy.COMBINED,
                window=RateLimitWindow.MINUTE,
                max_requests=10,
                paths=['/api/v1/resume/parse', '/api/v1/evaluation/analyze'],
                methods=['POST'],
            ),
        ]
        
        app.add_middleware(
            RateLimitMiddleware,
            redis_url=str(settings.redis_url),
            rules=rate_limit_rules,
            default_limits={
                RateLimitWindow.SECOND: settings.rate_limit_per_second,
                RateLimitWindow.MINUTE: settings.rate_limit_per_minute,
                RateLimitWindow.HOUR: settings.rate_limit_per_hour,
            },
            key_prefix="are:ratelimit",
            enable_headers=True,
        )
    
    # Add CORS middleware if needed
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    return app


# Create the application instance
app = create_app()


@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(
        f"Starting {settings.app_name} in {settings.app_env} environment"
    )


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on shutdown."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Shutting down {settings.app_name}")
    
    # Close rate limiter Redis connection if it exists
    for middleware in app.user_middleware:
        if hasattr(middleware, 'cls') and middleware.cls.__name__ == 'RateLimitMiddleware':
            if hasattr(middleware, 'kwargs'):
                # Access the middleware instance to close it
                # Note: This is a simplified example
                pass


# Example health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint (not rate limited)."""
    return {
        "status": "healthy",
        "environment": settings.app_env,
    }


# Example protected endpoint
@app.get("/api/v1/protected")
async def protected_endpoint():
    """Example endpoint that is rate limited."""
    return {"message": "This endpoint is protected by rate limiting"}


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "middleware_example:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
