"""
FastAPI application initialization and configuration.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import settings
from database.engine import init_db, close_db
from api.routes import health
from api.routes.v1 import (
    agents as agents_routes,
    actions,
    compliance,
    auth,
    beta,
    candidates,
    applications,
    jobs,
    interviews,
    evaluations,
    documents,
    search,
    comparison,
    calendar,
    bulk,
    background_checks,
    offers,
    users,
    webhooks,
)

# Import middleware components
from core.middleware import (
    ErrorHandlingMiddleware,
    setup_error_handlers,
    StructuredLoggingMiddleware,
    setup_logging,
    RateLimitMiddleware,
    RateLimitRule,
    RateLimitStrategy,
    RateLimitWindow,
    AuthenticationMiddleware,
    AuthorizationMiddleware,
)

# Setup structured logging (do this first, before anything else)
setup_logging(
    log_level=settings.log_level,
    json_logs=settings.json_logs,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    import logging
    from core.cache import redis_cache
    
    logger = logging.getLogger(__name__)
    
    # Startup
    logger.info(f"Starting {settings.app_name} in {settings.app_env} environment")
    await init_db()
    await redis_cache.init()
    
    yield
    
    # Shutdown
    logger.info(f"Shutting down {settings.app_name}")
    
    await redis_cache.close()
    
    # Close rate limiter Redis connection if enabled
    if settings.rate_limit_enabled:
        for middleware in app.user_middleware:
            if hasattr(middleware, 'cls'):
                if middleware.cls.__name__ == 'RateLimitMiddleware':
                    if hasattr(middleware, 'options') and 'kwargs' in middleware.options:
                        limiter = middleware.options.get('kwargs', {}).get('limiter')
                        if limiter and hasattr(limiter, 'close'):
                            await limiter.close()
    
    await close_db()


# Create FastAPI app with comprehensive API documentation
API_DESCRIPTION = """
# Alethic API

The **AI Hiring Copilot** API for intelligent recruitment automation.

## Features

- 🤖 **AI Chat Copilot** - Natural language interface for hiring tasks
- 📄 **Resume Parsing** - Automatic extraction and analysis
- 🎯 **Smart Matching** - AI-powered candidate ranking
- 📊 **Evaluations** - Pre and full candidate evaluations
- 🔒 **GDPR Compliant** - Built-in privacy controls

## Documentation

- [API Overview](/docs/api/overview.md)
- [Authentication Guide](/docs/api/authentication.md)
- [Endpoint Reference](/api-reference)

## Security

All endpoints are protected by JWT authentication and rate limiting.
PII access is logged for GDPR/SOC2 compliance.
"""

app = FastAPI(
    title="Alethic API",
    description=API_DESCRIPTION,
    version="1.0.0",
    docs_url="/api-reference",
    redoc_url="/api-reference/redoc",
    openapi_url="/api-reference/openapi.json",
    openapi_tags=[
        {"name": "Agents", "description": "AI Copilot chat and actions"},
        {"name": "Candidates", "description": "Candidate management (PII)"},
        {"name": "Applications", "description": "Application workflow"},
        {"name": "Jobs", "description": "Job postings"},
        {"name": "Interviews", "description": "Interview scheduling"},
        {"name": "Evaluations", "description": "AI evaluations and rankings"},
        {"name": "Documents", "description": "Resume and document access (PII)"},
        {"name": "Search", "description": "Semantic candidate search"},
        {"name": "Bulk Operations", "description": "Bulk actions"},
        {"name": "Background Checks", "description": "Background verification"},
        {"name": "Compliance", "description": "GDPR and legal compliance"},
        {"name": "Calendar", "description": "Scheduling and availability"},
        {"name": "Comparison", "description": "Candidate comparison"},
    ],
    lifespan=lifespan,
)

# Setup error handlers (before middleware)
setup_error_handlers(app)

# Add middleware (order matters - they execute in reverse order)
# 1. Error handling middleware (outermost - catches all errors)
app.add_middleware(
    ErrorHandlingMiddleware,
    debug=settings.debug,
)

# 2. Structured logging middleware (logs all requests/responses)
app.add_middleware(
    StructuredLoggingMiddleware,
    log_request_body=settings.log_request_body,
    log_response_body=settings.log_response_body,
    max_body_size=settings.log_max_body_size,
)

# 3. Authentication middleware (validates JWT tokens and sessions)
app.add_middleware(
    AuthenticationMiddleware,
    jwt_secret=settings.JWT_SECRET,
    jwt_algorithm=settings.JWT_ALGORITHM,
    token_refresh_threshold=3600,  # Refresh if < 1 hour remaining
)

# 4. Authorization middleware (checks permissions - runs after auth)
app.add_middleware(AuthorizationMiddleware)

# 5. Rate limiting middleware (innermost - only applied to valid requests)
if settings.rate_limit_enabled:
    # Define rate limit rules
    rate_limit_rules = [
        # Strict limits for authentication endpoints
        RateLimitRule(
            strategy=RateLimitStrategy.IP_ADDRESS,
            window=RateLimitWindow.MINUTE,
            max_requests=5,
            paths=[
                f"{settings.api_v1_prefix}/auth/login",
                f"{settings.api_v1_prefix}/auth/register",
                f"{settings.api_v1_prefix}/auth/forgot-password",
            ],
            methods=['POST'],
        ),
        # Strict limits for password reset
        RateLimitRule(
            strategy=RateLimitStrategy.IP_ADDRESS,
            window=RateLimitWindow.HOUR,
            max_requests=3,
            paths=[f"{settings.api_v1_prefix}/auth/reset-password"],
            methods=['POST'],
        ),
        # User-specific rate limits (per second)
        RateLimitRule(
            strategy=RateLimitStrategy.USER_ID,
            window=RateLimitWindow.SECOND,
            max_requests=settings.rate_limit_per_second,
        ),
        # User-specific rate limits (per minute)
        RateLimitRule(
            strategy=RateLimitStrategy.USER_ID,
            window=RateLimitWindow.MINUTE,
            max_requests=settings.rate_limit_per_minute,
        ),
        # User-specific rate limits (per hour)
        RateLimitRule(
            strategy=RateLimitStrategy.USER_ID,
            window=RateLimitWindow.HOUR,
            max_requests=settings.rate_limit_per_hour,
        ),
        # IP-based rate limits (backup for unauthenticated)
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
        # Expensive AI operations - combined strategy
        RateLimitRule(
            strategy=RateLimitStrategy.COMBINED,
            window=RateLimitWindow.MINUTE,
            max_requests=10,
            paths=[
                f"{settings.api_v1_prefix}/agents/resume/parse",
                f"{settings.api_v1_prefix}/agents/evaluation/analyze",
                f"{settings.api_v1_prefix}/agents/screening/conduct",
            ],
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

# 6. CORS middleware (after rate limiting)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check routes
app.include_router(health.router, tags=["Health"])

# =============================================================================
# API v1 Routes - Chat-First Hybrid Model
# =============================================================================

# Authentication
app.include_router(
    auth.router,
    tags=["Authentication"],
)

# Primary Chat Interface (AI Copilot)
app.include_router(
    agents_routes.router,
    prefix=f"{settings.api_v1_prefix}",
    tags=["AI Copilot"],
)

# Action Endpoints (UI buttons/menus)
app.include_router(
    actions.router,
    prefix=f"{settings.api_v1_prefix}",
    tags=["Actions"],
)

# Compliance (GDPR, legal - always required)
app.include_router(
    compliance.router,
    prefix=f"{settings.api_v1_prefix}",
    tags=["Compliance"],
)

# Beta features
app.include_router(
    beta.router,
    tags=["Beta"],
)

# Candidates
app.include_router(
    candidates.router,
    prefix=f"{settings.api_v1_prefix}",
    tags=["Candidates"],
)

# Applications
app.include_router(
    applications.router,
    prefix=f"{settings.api_v1_prefix}",
    tags=["Applications"],
)

# Jobs
app.include_router(
    jobs.router,
    prefix=f"{settings.api_v1_prefix}",
    tags=["Jobs"],
)

# Interviews
app.include_router(
    interviews.router,
    prefix=f"{settings.api_v1_prefix}",
    tags=["Interviews"],
)

# Evaluations
app.include_router(
    evaluations.router,
    prefix=f"{settings.api_v1_prefix}",
    tags=["Evaluations"],
)

# Documents
app.include_router(
    documents.router,
    prefix=f"{settings.api_v1_prefix}",
    tags=["Documents"],
)

# Search
app.include_router(
    search.router,
    prefix=f"{settings.api_v1_prefix}",
    tags=["Search"],
)

# Comparison
app.include_router(
    comparison.router,
    prefix=f"{settings.api_v1_prefix}",
    tags=["Comparison"],
)

# Calendar
app.include_router(
    calendar.router,
    prefix=f"{settings.api_v1_prefix}",
    tags=["Calendar"],
)

# Bulk Operations
app.include_router(
    bulk.router,
    prefix=f"{settings.api_v1_prefix}",
    tags=["Bulk Operations"],
)

# Background Checks
app.include_router(
    background_checks.router,
    prefix=f"{settings.api_v1_prefix}",
    tags=["Background Checks"],
)

# Offers
app.include_router(
    offers.router,
    prefix=f"{settings.api_v1_prefix}",
    tags=["Offers"],
)

# Users
app.include_router(
    users.router,
    prefix=f"{settings.api_v1_prefix}",
    tags=["Users"],
)

# Webhooks
app.include_router(
    webhooks.router,
    prefix=f"{settings.api_v1_prefix}",
    tags=["Webhooks"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Handle all unhandled exceptions.
    Note: This is a fallback - ErrorHandlingMiddleware handles most cases.
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.error(
        f"Unhandled exception in global handler: {type(exc).__name__}",
        exc_info=True,
    )
    
    if settings.debug:
        return JSONResponse(
            status_code=500,
            content={
                "detail": str(exc),
                "type": type(exc).__name__,
            },
        )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Root redirect
@app.get("/", include_in_schema=False)
async def root():
    """Redirect root to API reference."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/api-reference")



if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )

