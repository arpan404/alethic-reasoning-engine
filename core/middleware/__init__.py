"""
Core middleware package.

This package provides production-ready middleware components:
- Error handling with sensitive data sanitization
- Structured logging with PII masking
- Redis-based rate limiting with multiple strategies
- Authentication with JWT/WorkOS SSO
- Authorization with role-based and contextual permissions
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

from core.middleware.authentication import (
    AuthenticationMiddleware,
    get_current_user,
    get_current_session,
    require_user_types,
    AuthenticationError,
)

from core.middleware.authorization import (
    AuthorizationMiddleware,
    Permission,
    check_organization_access,
    check_permission,
    get_user_permissions,
    require_permission,
    require_organization_role,
    AuthorizationError,
    OrganizationAccessDenied,
    InsufficientPermissions,
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
    # Authentication
    "AuthenticationMiddleware",
    "get_current_user",
    "get_current_session",
    "require_user_types",
    "AuthenticationError",
    # Authorization
    "AuthorizationMiddleware",
    "Permission",
    "check_organization_access",
    "check_permission",
    "get_user_permissions",
    "require_permission",
    "require_organization_role",
    "AuthorizationError",
    "OrganizationAccessDenied",
    "InsufficientPermissions",
]
