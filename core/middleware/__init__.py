"""
Core middleware package.

This package provides production-ready middleware components:
- Error handling with sensitive data sanitization
- Structured logging with PII masking
- Redis-based rate limiting with multiple strategies
"""

from core.middleware.error_handling import (
    ErrorHandlingMiddleware,
    setup_error_handlers,
    sanitize_error_message,
)

from core.middleware.logging import (
    StructuredLoggingMiddleware,
    setup_logging,
    get_logger,
)

from core.middleware.rate_limiting import (
    RateLimitMiddleware,
    RateLimitRule,
    RateLimitStrategy,
    RateLimitWindow,
    SlidingWindowRateLimiter,
)

__all__ = [
    # Error handling
    "ErrorHandlingMiddleware",
    "setup_error_handlers",
    "sanitize_error_message",
    # Logging
    "StructuredLoggingMiddleware",
    "setup_logging",
    "get_logger",
    # Rate limiting
    "RateLimitMiddleware",
    "RateLimitRule",
    "RateLimitStrategy",
    "RateLimitWindow",
    "SlidingWindowRateLimiter",
]
