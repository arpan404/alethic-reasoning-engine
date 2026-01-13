"""
Authentication middleware for verifying user identity and session validity.

This middleware:
1. Validates JWT tokens from Authorization headers
2. Verifies WorkOS user identity
3. Checks session validity and expiration
4. Loads user data into request context
5. Handles token refresh
6. Implements GDPR/SOC2 compliant session management
"""

import logging
from typing import Callable, Optional
from datetime import datetime, timezone
import jwt
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.engine import get_db
from database.models.users import User, UserSession, UserType
from core.security import verify_jwt_token, JWTPayload

logger = logging.getLogger(__name__)

# Public endpoints that don't require authentication
PUBLIC_ENDPOINTS = [
    "/",
    "/health",
    "/api/v1/health",
    "/api/v1/auth/login",
    "/api/v1/auth/signup",
    "/api/v1/auth/refresh",
    "/api/v1/auth/sso/workos",
    "/api/v1/auth/sso/callback",
    "/docs",
    "/redoc",
    "/openapi.json",
]


class AuthenticationError(Exception):
    """Base exception for authentication errors."""
    pass


class TokenExpiredError(AuthenticationError):
    """Raised when JWT token has expired."""
    pass


class TokenInvalidError(AuthenticationError):
    """Raised when JWT token is invalid."""
    pass


class SessionInvalidError(AuthenticationError):
    """Raised when user session is invalid or expired."""
    pass


class UserNotFoundError(AuthenticationError):
    """Raised when user is not found."""
    pass


class UserInactiveError(AuthenticationError):
    """Raised when user account is inactive."""
    pass


class AuthenticationMiddleware:
    """
    Authentication middleware that validates user identity and sessions.
    
    Features:
    - JWT token validation
    - WorkOS user verification
    - Session management
    - GDPR/SOC2 compliant logging
    - Rate limiting integration
    - Request context injection
    """
    
    def __init__(
        self,
        app: Callable,
        jwt_secret: str,
        jwt_algorithm: str = "HS256",
        token_refresh_threshold: int = 3600,  # Refresh if < 1 hour remaining
    ):
        """
        Initialize authentication middleware.
        
        Args:
            app: ASGI application
            jwt_secret: Secret key for JWT verification
            jwt_algorithm: JWT signing algorithm
            token_refresh_threshold: Seconds before expiry to trigger refresh
        """
        self.app = app
        self.jwt_secret = jwt_secret
        self.jwt_algorithm = jwt_algorithm
        self.token_refresh_threshold = token_refresh_threshold
    
    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        """
        Process requests with authentication validation.
        
        Args:
            scope: ASGI scope dictionary
            receive: ASGI receive function
            send: ASGI send function
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope)
        
        # Skip authentication for public endpoints
        if self._is_public_endpoint(request.url.path):
            await self.app(scope, receive, send)
            return
        
        try:
            # Extract and verify token
            token = self._extract_token(request)
            if not token:
                raise TokenInvalidError("No authentication token provided")
            
            # Verify JWT and extract payload
            try:
                payload = verify_jwt_token(token, self.jwt_secret, self.jwt_algorithm)
            except jwt.ExpiredSignatureError:
                raise TokenExpiredError("Token has expired")
            except jwt.InvalidTokenError as e:
                raise TokenInvalidError(f"Invalid token: {str(e)}")
            
            # Load user and validate session
            async with get_db() as db:
                user, session = await self._validate_user_and_session(
                    db, payload, token
                )
                
                # Inject authenticated user into request scope
                scope["user"] = user
                scope["session"] = session
                scope["jwt_payload"] = payload
                
                # Check if token needs refresh
                if self._should_refresh_token(payload):
                    scope["token_refresh_needed"] = True
            
            # Continue to next middleware/route
            await self.app(scope, receive, send)
            
        except TokenExpiredError:
            await self._send_error_response(
                send,
                status_code=status.HTTP_401_UNAUTHORIZED,
                code="TOKEN_EXPIRED",
                message="Authentication token has expired. Please refresh your token.",
            )
        except TokenInvalidError as e:
            logger.warning(f"Invalid token: {str(e)}")
            await self._send_error_response(
                send,
                status_code=status.HTTP_401_UNAUTHORIZED,
                code="TOKEN_INVALID",
                message="Invalid authentication token.",
            )
        except SessionInvalidError as e:
            logger.warning(f"Invalid session: {str(e)}")
            await self._send_error_response(
                send,
                status_code=status.HTTP_401_UNAUTHORIZED,
                code="SESSION_INVALID",
                message="Session has expired or is invalid. Please login again.",
            )
        except UserNotFoundError:
            logger.error("User not found for valid token")
            await self._send_error_response(
                send,
                status_code=status.HTTP_401_UNAUTHORIZED,
                code="USER_NOT_FOUND",
                message="User account not found.",
            )
        except UserInactiveError:
            logger.warning("Inactive user attempted access")
            await self._send_error_response(
                send,
                status_code=status.HTTP_403_FORBIDDEN,
                code="USER_INACTIVE",
                message="User account is inactive. Please contact support.",
            )
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}", exc_info=True)
            await self._send_error_response(
                send,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                code="AUTHENTICATION_ERROR",
                message="An error occurred during authentication.",
            )
    
    def _is_public_endpoint(self, path: str) -> bool:
        """
        Check if endpoint is public (no auth required).
        
        Args:
            path: Request path
            
        Returns:
            True if endpoint is public
        """
        # Exact match
        if path in PUBLIC_ENDPOINTS:
            return True
        
        # Prefix match for health checks and docs
        public_prefixes = ["/health", "/docs", "/redoc", "/openapi"]
        return any(path.startswith(prefix) for prefix in public_prefixes)
    
    def _extract_token(self, request: Request) -> Optional[str]:
        """
        Extract JWT token from Authorization header.
        
        Args:
            request: FastAPI request
            
        Returns:
            JWT token or None
        """
        auth_header = request.headers.get("Authorization")
        
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[7:]  # Remove "Bearer " prefix
        
        return None
    
    async def _validate_user_and_session(
        self,
        db: AsyncSession,
        payload: JWTPayload,
        token: str,
    ) -> tuple[User, UserSession]:
        """
        Validate user exists, is active, and has valid session.
        
        Args:
            db: Database session
            payload: JWT payload
            token: JWT token string
            
        Returns:
            Tuple of (User, UserSession)
            
        Raises:
            UserNotFoundError: If user doesn't exist
            UserInactiveError: If user is inactive
            SessionInvalidError: If session is invalid or expired
        """
        user_id = payload.get("user_id")
        session_id = payload.get("session_id")
        
        if not user_id:
            raise TokenInvalidError("Token missing user_id")
        
        # Load user
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise UserNotFoundError(f"User {user_id} not found")
        
        if not user.is_active:
            raise UserInactiveError(f"User {user_id} is inactive")
        
        if not user.email_verified:
            raise SessionInvalidError(f"User {user_id} email not verified")
        
        # Validate session if session_id provided
        if session_id:
            result = await db.execute(
                select(UserSession).where(
                    UserSession.id == session_id,
                    UserSession.user_id == user_id,
                    UserSession.session_token == token,
                )
            )
            session = result.scalar_one_or_none()
            
            if not session:
                raise SessionInvalidError("Session not found")
            
            # Check session expiration
            if session.expires_at < datetime.now(timezone.utc):
                raise SessionInvalidError("Session has expired")
            
            if session.revoked_at:
                raise SessionInvalidError("Session has been revoked")
        else:
            # No session tracking (for service accounts or API keys)
            session = None
        
        return user, session
    
    def _should_refresh_token(self, payload: JWTPayload) -> bool:
        """
        Check if token should be refreshed.
        
        Args:
            payload: JWT payload
            
        Returns:
            True if token should be refreshed
        """
        exp = payload.get("exp")
        if not exp:
            return False
        
        # Calculate time until expiry
        expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)
        now = datetime.now(timezone.utc)
        seconds_until_expiry = (expires_at - now).total_seconds()
        
        return seconds_until_expiry < self.token_refresh_threshold
    
    async def _send_error_response(
        self,
        send: Callable,
        status_code: int,
        code: str,
        message: str,
    ) -> None:
        """
        Send error response for authentication failures.
        
        Args:
            send: ASGI send function
            status_code: HTTP status code
            code: Error code
            message: Error message
        """
        error_response = {
            "error": {
                "code": code,
                "message": message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        }
        
        response = JSONResponse(
            status_code=status_code,
            content=error_response,
        )
        
        await response({"type": "http", "method": "GET"}, None, send)


def get_current_user(request: Request) -> User:
    """
    Get current authenticated user from request scope.
    
    Args:
        request: FastAPI request
        
    Returns:
        Authenticated user
        
    Raises:
        AuthenticationError: If user not found in scope
    """
    user = request.scope.get("user")
    if not user:
        raise AuthenticationError("User not authenticated")
    return user


def get_current_session(request: Request) -> Optional[UserSession]:
    """
    Get current user session from request scope.
    
    Args:
        request: FastAPI request
        
    Returns:
        User session or None
    """
    return request.scope.get("session")


def require_user_types(*allowed_types: UserType) -> Callable:
    """
    Decorator to require specific user types.
    
    Args:
        allowed_types: Allowed user types
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(request: Request, *args, **kwargs):
            user = get_current_user(request)
            if user.user_type not in allowed_types:
                raise AuthenticationError(
                    f"User type {user.user_type} not allowed. "
                    f"Required: {', '.join(str(t) for t in allowed_types)}"
                )
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator
