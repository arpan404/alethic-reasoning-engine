"""
Error handling middleware with security-compliant error sanitization.
Prevents sensitive data leakage while providing useful error information.
"""

import logging
import traceback
from typing import Any, Callable
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError
import re

logger = logging.getLogger(__name__)

# Patterns for sensitive data that should never be logged
SENSITIVE_PATTERNS = [
    re.compile(r'password["\s:=]+[^"\s,}]+', re.IGNORECASE),
    re.compile(r'token["\s:=]+[^"\s,}]+', re.IGNORECASE),
    re.compile(r'api[_-]?key["\s:=]+[^"\s,}]+', re.IGNORECASE),
    re.compile(r'secret["\s:=]+[^"\s,}]+', re.IGNORECASE),
    re.compile(r'authorization["\s:]+[^"\s,}]+', re.IGNORECASE),
    re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),  # SSN
    re.compile(r'\b\d{16}\b'),  # Credit card
]


def sanitize_error_message(message: str) -> str:
    """
    Remove sensitive information from error messages.
    
    Args:
        message: Original error message
        
    Returns:
        Sanitized error message
    """
    sanitized = message
    for pattern in SENSITIVE_PATTERNS:
        sanitized = pattern.sub('[REDACTED]', sanitized)
    return sanitized


def get_safe_error_details(exc: Exception, include_details: bool = False) -> dict[str, Any]:
    """
    Extract safe error details without exposing sensitive information.
    
    Args:
        exc: The exception to extract details from
        include_details: Whether to include detailed error information (only in dev)
        
    Returns:
        Dictionary with safe error details
    """
    error_type = type(exc).__name__
    error_message = sanitize_error_message(str(exc))
    
    details = {
        "type": error_type,
        "message": error_message,
    }
    
    if include_details:
        # Only include stack trace in development
        details["traceback"] = traceback.format_exc()
    
    return details


class ErrorHandlingMiddleware:
    """
    Comprehensive error handling middleware with security compliance.
    
    Features:
    - Sanitizes error messages to prevent sensitive data leakage
    - Provides structured error responses
    - Handles all exception types gracefully
    - Logs errors with appropriate severity
    - Returns user-friendly error messages
    """
    
    def __init__(self, app: Callable, debug: bool = False):
        """
        Initialize error handling middleware.
        
        Args:
            app: The ASGI application
            debug: Whether to include detailed error information
        """
        self.app = app
        self.debug = debug
    
    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        """
        Process requests with comprehensive error handling.
        
        Args:
            scope: ASGI scope
            receive: ASGI receive channel
            send: ASGI send channel
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        try:
            await self.app(scope, receive, send)
        except Exception as exc:
            # Handle the exception and send error response
            response = await self._handle_exception(exc, scope)
            await response(scope, receive, send)
    
    async def _handle_exception(self, exc: Exception, scope: dict) -> Response:
        """
        Handle different types of exceptions and return appropriate responses.
        
        Args:
            exc: The exception to handle
            scope: ASGI scope for context
            
        Returns:
            JSONResponse with error details
        """
        request_path = scope.get("path", "unknown")
        request_method = scope.get("method", "unknown")
        
        # Initialize response variables
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        error_code = "INTERNAL_SERVER_ERROR"
        message = "An unexpected error occurred"
        details = None
        
        # Handle specific exception types
        if isinstance(exc, StarletteHTTPException):
            status_code = exc.status_code
            error_code = "HTTP_EXCEPTION"
            message = sanitize_error_message(exc.detail)
            logger.warning(
                f"HTTP exception: {request_method} {request_path} - "
                f"Status: {status_code}, Message: {message}"
            )
        
        elif isinstance(exc, RequestValidationError):
            status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
            error_code = "VALIDATION_ERROR"
            message = "Request validation failed"
            details = self._format_validation_errors(exc)
            logger.warning(
                f"Validation error: {request_method} {request_path} - "
                f"Errors: {details}"
            )
        
        elif isinstance(exc, IntegrityError):
            status_code = status.HTTP_409_CONFLICT
            error_code = "INTEGRITY_ERROR"
            message = "Database integrity constraint violated"
            if self.debug:
                details = get_safe_error_details(exc, include_details=True)
            logger.error(
                f"Database integrity error: {request_method} {request_path}",
                exc_info=not self.debug
            )
        
        elif isinstance(exc, OperationalError):
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            error_code = "DATABASE_ERROR"
            message = "Database service temporarily unavailable"
            logger.error(
                f"Database operational error: {request_method} {request_path}",
                exc_info=True
            )
        
        elif isinstance(exc, SQLAlchemyError):
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            error_code = "DATABASE_ERROR"
            message = "A database error occurred"
            if self.debug:
                details = get_safe_error_details(exc, include_details=True)
            logger.error(
                f"SQLAlchemy error: {request_method} {request_path}",
                exc_info=not self.debug
            )
        
        elif isinstance(exc, RedisConnectionError):
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            error_code = "CACHE_ERROR"
            message = "Cache service temporarily unavailable"
            logger.error(
                f"Redis connection error: {request_method} {request_path}",
                exc_info=True
            )
        
        elif isinstance(exc, RedisError):
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            error_code = "CACHE_ERROR"
            message = "A cache error occurred"
            if self.debug:
                details = get_safe_error_details(exc, include_details=True)
            logger.error(
                f"Redis error: {request_method} {request_path}",
                exc_info=not self.debug
            )
        
        elif isinstance(exc, ValueError):
            status_code = status.HTTP_400_BAD_REQUEST
            error_code = "INVALID_INPUT"
            message = sanitize_error_message(str(exc)) or "Invalid input provided"
            logger.warning(
                f"Value error: {request_method} {request_path} - {message}"
            )
        
        elif isinstance(exc, PermissionError):
            status_code = status.HTTP_403_FORBIDDEN
            error_code = "PERMISSION_DENIED"
            message = "You don't have permission to perform this action"
            logger.warning(
                f"Permission error: {request_method} {request_path}"
            )
        
        elif isinstance(exc, TimeoutError):
            status_code = status.HTTP_504_GATEWAY_TIMEOUT
            error_code = "TIMEOUT"
            message = "The request timed out"
            logger.error(
                f"Timeout error: {request_method} {request_path}"
            )
        
        else:
            # Generic exception handler
            error_code = "INTERNAL_SERVER_ERROR"
            message = "An unexpected error occurred"
            if self.debug:
                details = get_safe_error_details(exc, include_details=True)
            logger.error(
                f"Unhandled exception: {request_method} {request_path} - "
                f"{type(exc).__name__}: {sanitize_error_message(str(exc))}",
                exc_info=True
            )
        
        # Build error response
        error_response = {
            "error": {
                "code": error_code,
                "message": message,
                "path": request_path,
                "method": request_method,
            }
        }
        
        if details is not None:
            error_response["error"]["details"] = details
        
        # Add request ID if available
        if "headers" in scope:
            headers = dict(scope["headers"])
            request_id = headers.get(b"x-request-id")
            if request_id:
                error_response["error"]["request_id"] = request_id.decode()
        
        return JSONResponse(
            status_code=status_code,
            content=error_response,
        )
    
    def _format_validation_errors(self, exc: RequestValidationError) -> list[dict[str, Any]]:
        """
        Format validation errors into a user-friendly structure.
        
        Args:
            exc: The validation exception
            
        Returns:
            List of formatted validation errors
        """
        errors = []
        for error in exc.errors():
            error_dict = {
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": sanitize_error_message(error["msg"]),
                "type": error["type"],
            }
            
            # Include input value only if it's safe (not sensitive)
            if "input" in error:
                input_value = error["input"]
                # Only include input if it's a simple type and not sensitive
                if isinstance(input_value, (str, int, float, bool)):
                    input_str = str(input_value)
                    if not any(pattern.search(input_str) for pattern in SENSITIVE_PATTERNS):
                        error_dict["input"] = input_value
            
            errors.append(error_dict)
        
        return errors


def setup_error_handlers(app):
    """
    Set up exception handlers for FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle HTTP exceptions."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": "HTTP_EXCEPTION",
                    "message": sanitize_error_message(exc.detail),
                    "path": str(request.url.path),
                    "method": request.method,
                }
            },
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle validation errors."""
        errors = []
        for error in exc.errors():
            error_dict = {
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": sanitize_error_message(error["msg"]),
                "type": error["type"],
            }
            errors.append(error_dict)
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "path": str(request.url.path),
                    "method": request.method,
                    "details": errors,
                }
            },
        )
    
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        """Handle all other exceptions."""
        logger.error(
            f"Unhandled exception: {request.method} {request.url.path} - "
            f"{type(exc).__name__}: {sanitize_error_message(str(exc))}",
            exc_info=True
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred",
                    "path": str(request.url.path),
                    "method": request.method,
                }
            },
        )
