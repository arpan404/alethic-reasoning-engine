"""
Structured logging middleware with PII masking and security compliance.
Provides comprehensive request/response logging without exposing sensitive data.
"""

import logging
import time
import json
import re
import uuid
from typing import Callable, Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import traceback

# Configure structured logging
logger = logging.getLogger(__name__)


# Sensitive field patterns to mask in logs
SENSITIVE_FIELD_PATTERNS = [
    re.compile(r'password', re.IGNORECASE),
    re.compile(r'passwd', re.IGNORECASE),
    re.compile(r'pwd', re.IGNORECASE),
    re.compile(r'token', re.IGNORECASE),
    re.compile(r'api[_-]?key', re.IGNORECASE),
    re.compile(r'secret', re.IGNORECASE),
    re.compile(r'authorization', re.IGNORECASE),
    re.compile(r'bearer', re.IGNORECASE),
    re.compile(r'cookie', re.IGNORECASE),
    re.compile(r'session', re.IGNORECASE),
    re.compile(r'csrf', re.IGNORECASE),
    re.compile(r'credit[_-]?card', re.IGNORECASE),
    re.compile(r'cvv', re.IGNORECASE),
    re.compile(r'ssn', re.IGNORECASE),
    re.compile(r'social[_-]?security', re.IGNORECASE),
    re.compile(r'private[_-]?key', re.IGNORECASE),
]

# PII patterns to detect and mask
PII_PATTERNS = [
    # Email addresses
    (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), '[EMAIL]'),
    # Phone numbers (various formats)
    (re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'), '[PHONE]'),
    (re.compile(r'\+\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}'), '[PHONE]'),
    # SSN
    (re.compile(r'\b\d{3}-\d{2}-\d{4}\b'), '[SSN]'),
    # Credit card numbers
    (re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'), '[CARD]'),
    # IP addresses (sometimes considered PII)
    (re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'), '[IP]'),
]


def is_sensitive_field(field_name: str) -> bool:
    """
    Check if a field name indicates sensitive data.
    
    Args:
        field_name: Name of the field to check
        
    Returns:
        True if field is sensitive, False otherwise
    """
    return any(pattern.search(field_name) for pattern in SENSITIVE_FIELD_PATTERNS)


def mask_sensitive_data(data: Any, depth: int = 0, max_depth: int = 10) -> Any:
    """
    Recursively mask sensitive data in dictionaries and lists.
    
    Args:
        data: Data structure to mask
        depth: Current recursion depth
        max_depth: Maximum recursion depth to prevent infinite loops
        
    Returns:
        Data structure with sensitive values masked
    """
    if depth > max_depth:
        return "[MAX_DEPTH_EXCEEDED]"
    
    if isinstance(data, dict):
        masked = {}
        for key, value in data.items():
            if is_sensitive_field(str(key)):
                # Apply PII patterns to the value if it's a string
                if isinstance(value, str):
                    masked_value = value
                    original_value = value
                    for pattern, replacement in PII_PATTERNS:
                        masked_value = pattern.sub(replacement, masked_value)
                    # If no pattern matched, use generic redaction
                    if masked_value == original_value:
                        masked[key] = "[REDACTED]"
                    else:
                        masked[key] = masked_value
                else:
                    masked[key] = "[REDACTED]"
            else:
                masked[key] = mask_sensitive_data(value, depth + 1, max_depth)
        return masked
    
    elif isinstance(data, list):
        return [mask_sensitive_data(item, depth + 1, max_depth) for item in data]
    
    elif isinstance(data, str):
        # Mask PII in string values
        masked_str = data
        for pattern, replacement in PII_PATTERNS:
            masked_str = pattern.sub(replacement, masked_str)
        return masked_str
    
    else:
        return data


def mask_headers(headers: dict) -> dict:
    """
    Mask sensitive headers while preserving useful debugging information.
    
    Args:
        headers: Dictionary of HTTP headers
        
    Returns:
        Headers with sensitive values masked
    """
    masked = {}
    for key, value in headers.items():
        key_lower = key.lower()
        if any(pattern.search(key_lower) for pattern in SENSITIVE_FIELD_PATTERNS):
            # For authorization headers, show the type but mask the token
            if key_lower == 'authorization' and isinstance(value, str):
                parts = value.split(' ', 1)
                if len(parts) == 2:
                    masked[key] = f"{parts[0]} [REDACTED]"
                else:
                    masked[key] = "[REDACTED]"
            else:
                masked[key] = "[REDACTED]"
        else:
            masked[key] = value
    
    return masked


def should_log_request(path: str) -> bool:
    """
    Determine if a request should be logged based on the path.
    
    Args:
        path: Request path
        
    Returns:
        True if request should be logged, False otherwise
    """
    # Don't log health checks and metrics to reduce noise
    skip_paths = ['/health', '/healthz', '/metrics', '/ready', '/alive']
    return not any(path.startswith(skip) for skip in skip_paths)


def get_client_ip(request: Request) -> str:
    """
    Extract client IP address from request, handling proxies.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Client IP address (masked for privacy)
    """
    # Check forwarded headers (common in proxy setups)
    forwarded_for = request.headers.get('x-forwarded-for')
    if forwarded_for:
        # Take the first IP in the chain
        ip = forwarded_for.split(',')[0].strip()
    else:
        ip = request.client.host if request.client else 'unknown'
    
    # Mask last octet for privacy compliance
    if ip and ip != 'unknown':
        parts = ip.split('.')
        if len(parts) == 4:
            # Valid IPv4 address
            return f"{parts[0]}.{parts[1]}.{parts[2]}.xxx"
        else:
            # Not a valid IPv4, return as unknown for privacy
            return 'unknown'
    
    return ip


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """
    Structured logging middleware with PII masking and security compliance.
    
    Features:
    - Structured JSON logging for easy parsing
    - Automatic PII/sensitive data masking
    - Request/response timing and metrics
    - Request ID tracking for distributed tracing
    - Configurable log levels per endpoint
    - Security-compliant logging (no credentials, tokens, etc.)
    """
    
    def __init__(
        self,
        app: ASGIApp,
        log_request_body: bool = False,
        log_response_body: bool = False,
        max_body_size: int = 1024,
    ):
        """
        Initialize logging middleware.
        
        Args:
            app: The ASGI application
            log_request_body: Whether to log request bodies (masked)
            log_response_body: Whether to log response bodies (masked)
            max_body_size: Maximum body size to log (bytes)
        """
        super().__init__(app)
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.max_body_size = max_body_size
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with structured logging.
        
        Args:
            request: The incoming request
            call_next: The next middleware/handler
            
        Returns:
            Response from the application
        """
        # Generate or extract request ID for tracing
        request_id = request.headers.get('x-request-id', str(uuid.uuid4()))
        request.state.request_id = request_id
        
        # Skip logging for certain paths
        if not should_log_request(request.url.path):
            response = await call_next(request)
            response.headers['x-request-id'] = request_id
            return response
        
        # Start timing
        start_time = time.time()
        
        # Prepare request log data
        request_log = {
            'event': 'request_started',
            'request_id': request_id,
            'method': request.method,
            'path': request.url.path,
            'query_params': mask_sensitive_data(dict(request.query_params)),
            'client_ip': get_client_ip(request),
            'user_agent': request.headers.get('user-agent', 'unknown'),
            'headers': mask_headers(dict(request.headers)),
        }
        
        # Log request body if enabled
        if self.log_request_body and request.method in ['POST', 'PUT', 'PATCH']:
            try:
                body = await self._get_request_body(request)
                if body:
                    request_log['body'] = mask_sensitive_data(body)
            except Exception as e:
                logger.warning(f"Failed to read request body: {e}")
                request_log['body_error'] = str(e)
        
        # Log the request
        logger.info(json.dumps(request_log))
        
        # Process request and handle errors
        response = None
        error_occurred = False
        error_details = None
        
        try:
            response = await call_next(request)
        except Exception as exc:
            error_occurred = True
            error_details = {
                'type': type(exc).__name__,
                'message': str(exc),
            }
            logger.error(
                f"Request processing error: {request.method} {request.url.path}",
                exc_info=True,
                extra={
                    'request_id': request_id,
                    'error': error_details,
                }
            )
            raise
        finally:
            # Calculate request duration
            duration = time.time() - start_time
            
            # Prepare response log data
            response_log = {
                'event': 'request_completed',
                'request_id': request_id,
                'method': request.method,
                'path': request.url.path,
                'duration_ms': round(duration * 1000, 2),
                'status_code': response.status_code if response else 500,
            }
            
            # Add error details if applicable
            if error_occurred:
                response_log['error'] = error_details
            
            # Add performance markers
            if duration > 5.0:
                response_log['performance'] = 'slow'
            elif duration > 1.0:
                response_log['performance'] = 'moderate'
            else:
                response_log['performance'] = 'fast'
            
            # Log appropriate level based on status code
            if response and response.status_code >= 500:
                logger.error(json.dumps(response_log))
            elif response and response.status_code >= 400:
                logger.warning(json.dumps(response_log))
            else:
                logger.info(json.dumps(response_log))
            
            # Add request ID to response headers
            if response:
                response.headers['x-request-id'] = request_id
        
        return response
    
    async def _get_request_body(self, request: Request) -> Any:
        """
        Safely extract request body for logging.
        
        Args:
            request: The incoming request
            
        Returns:
            Parsed request body or None
        """
        try:
            # Check content type
            content_type = request.headers.get('content-type', '')
            
            if 'application/json' in content_type:
                body_bytes = await request.body()
                if len(body_bytes) > self.max_body_size:
                    return {'_truncated': True, '_size': len(body_bytes)}
                
                body_str = body_bytes.decode('utf-8')
                return json.loads(body_str)
            
            elif 'application/x-www-form-urlencoded' in content_type:
                form = await request.form()
                return dict(form)
            
            else:
                # Don't log binary or other content types
                return {'_content_type': content_type}
        
        except Exception as e:
            logger.debug(f"Could not parse request body: {e}")
            return None


def setup_logging(log_level: str = "INFO", json_logs: bool = True):
    """
    Configure application-wide structured logging.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        json_logs: Whether to format logs as JSON
    """
    
    class StructuredFormatter(logging.Formatter):
        """Custom formatter for structured JSON logs."""
        
        def format(self, record: logging.LogRecord) -> str:
            """Format log record as JSON."""
            log_data = {
                'timestamp': self.formatTime(record, self.datefmt),
                'level': record.levelname,
                'logger': record.name,
                'message': record.getMessage(),
            }
            
            # Add extra fields if present
            if hasattr(record, 'request_id'):
                log_data['request_id'] = record.request_id
            
            if hasattr(record, 'user_id'):
                log_data['user_id'] = record.user_id
            
            # Add exception info if present
            if record.exc_info:
                log_data['exception'] = {
                    'type': record.exc_info[0].__name__,
                    'message': str(record.exc_info[1]),
                    'traceback': traceback.format_exception(*record.exc_info),
                }
            
            return json.dumps(log_data)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper()))
    
    if json_logs:
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Reduce noise from third-party libraries
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with proper configuration.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
