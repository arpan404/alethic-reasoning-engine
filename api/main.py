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
    applications,
    candidates,
    jobs,
    offers,
    users,
    webhooks,
    agents as agents_routes,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="ATS with AI-powered agents using Google ADK",
    version="0.1.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check routes
app.include_router(health.router, tags=["Health"])

# API v1 routes
app.include_router(
    applications.router,
    prefix=f"{settings.api_v1_prefix}/applications",
    tags=["Applications"],
)
app.include_router(
    candidates.router,
    prefix=f"{settings.api_v1_prefix}/candidates",
    tags=["Candidates"],
)
app.include_router(
    jobs.router,
    prefix=f"{settings.api_v1_prefix}/jobs",
    tags=["Jobs"],
)
app.include_router(
    offers.router,
    prefix=f"{settings.api_v1_prefix}/offers",
    tags=["Offers"],
)
app.include_router(
    users.router,
    prefix=f"{settings.api_v1_prefix}/users",
    tags=["Users"],
)
app.include_router(
    webhooks.router,
    prefix=f"{settings.api_v1_prefix}/webhooks",
    tags=["Webhooks"],
)
app.include_router(
    agents_routes.router,
    prefix=f"{settings.api_v1_prefix}/agents",
    tags=["Agents"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle all unhandled exceptions."""
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
