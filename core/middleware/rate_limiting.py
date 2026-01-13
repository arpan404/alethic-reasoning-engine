"""
Redis-based rate limiting middleware with multiple strategies.
Implements distributed rate limiting with sliding window algorithm.
"""

import logging
import time
import hashlib
from typing import Callable, Optional, List, Dict, Any
from enum import Enum
from dataclasses import dataclass
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import redis.asyncio as redis
from redis.asyncio import Redis
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError

logger = logging.getLogger(__name__)


class RateLimitStrategy(str, Enum):
    """Rate limiting strategy types."""
    IP_ADDRESS = "ip"
    USER_ID = "user"
    API_KEY = "api_key"
    ENDPOINT = "endpoint"
    GLOBAL = "global"
    COMBINED = "combined"  # Combination of multiple strategies


class RateLimitWindow(str, Enum):
    """Time window types for rate limiting."""
    SECOND = "second"
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"


@dataclass
class RateLimitRule:
    """Rate limit rule configuration."""
    strategy: RateLimitStrategy
    window: RateLimitWindow
    max_requests: int
    paths: Optional[List[str]] = None  # Specific paths to apply rule
    methods: Optional[List[str]] = None  # Specific HTTP methods
    exempt_ips: Optional[List[str]] = None  # IPs exempt from this rule
    exempt_user_ids: Optional[List[str]] = None  # User IDs exempt from this rule


class SlidingWindowRateLimiter:
    """
    Redis-based sliding window rate limiter.
    
    Implements a precise sliding window algorithm using Redis sorted sets.
    More accurate than fixed window and more memory-efficient than full sliding log.
    """
    
    def __init__(self, redis_client: Redis):
        """
        Initialize rate limiter.
        
        Args:
            redis_client: Async Redis client instance
        """
        self.redis = redis_client
    
    async def is_allowed(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
        cost: int = 1,
    ) -> tuple[bool, Dict[str, Any]]:
        """
        Check if request is allowed under rate limit.
        
        Args:
            key: Unique identifier for the rate limit
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
            cost: Cost of this request (default 1, can be higher for expensive operations)
            
        Returns:
            Tuple of (is_allowed, metadata)
            metadata contains: remaining, reset_time, retry_after
        """
        now = time.time()
        window_start = now - window_seconds
        
        try:
            # Use Redis transaction for atomic operations
            pipe = self.redis.pipeline()
            
            # Remove old entries outside the window
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count requests in current window
            pipe.zcard(key)
            
            # Add current request with score = timestamp
            # Use microseconds to ensure uniqueness
            request_id = f"{now}:{hashlib.md5(str(now).encode()).hexdigest()[:8]}"
            pipe.zadd(key, {request_id: now})
            
            # Set expiry on the key (window + buffer)
            pipe.expire(key, window_seconds + 60)
            
            # Execute pipeline
            results = await pipe.execute()
            
            # Get current count (before adding new request)
            current_count = results[1]
            
            # Calculate remaining and metadata
            remaining = max(0, max_requests - current_count - cost)
            reset_time = int(now + window_seconds)
            
            # Check if allowed (account for cost of this request)
            is_allowed = (current_count + cost) <= max_requests
            
            if not is_allowed:
                # Calculate retry after (time until oldest request expires)
                oldest_scores = await self.redis.zrange(key, 0, 0, withscores=True)
                if oldest_scores:
                    oldest_timestamp = oldest_scores[0][1]
                    retry_after = int(oldest_timestamp + window_seconds - now)
                else:
                    retry_after = window_seconds
                
                # Remove the request we just added since it's not allowed
                await self.redis.zrem(key, request_id)
            else:
                retry_after = 0
            
            metadata = {
                'limit': max_requests,
                'remaining': remaining,
                'reset': reset_time,
                'retry_after': max(0, retry_after),
                'current': current_count,
            }
            
            return is_allowed, metadata
        
        except RedisConnectionError as e:
            logger.error(f"Redis connection error in rate limiter: {e}")
            # Fail open - allow request if Redis is unavailable
            return True, {
                'limit': max_requests,
                'remaining': max_requests,
                'reset': int(now + window_seconds),
                'retry_after': 0,
                'error': 'redis_unavailable',
            }
        
        except (RedisError, Exception) as e:
            logger.error(f"Redis error in rate limiter: {e}")
            # Fail open - allow request if Redis has errors
            return True, {
                'limit': max_requests,
                'remaining': max_requests,
                'reset': int(now + window_seconds),
                'retry_after': 0,
                'error': 'redis_error',
            }
    
    async def reset(self, key: str) -> bool:
        """
        Reset rate limit for a specific key.
        
        Args:
            key: Rate limit key to reset
            
        Returns:
            True if reset successful
        """
        try:
            await self.redis.delete(key)
            return True
        except RedisError as e:
            logger.error(f"Failed to reset rate limit for {key}: {e}")
            return False


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive rate limiting middleware with multiple strategies.
    
    Features:
    - Multiple rate limiting strategies (IP, user, API key, endpoint, global)
    - Sliding window algorithm for precise rate limiting
    - Redis-based distributed rate limiting
    - Configurable rules per endpoint
    - Graceful degradation (fail open) if Redis is unavailable
    - Detailed rate limit headers in responses
    - Support for rate limit costs (expensive operations)
    """
    
    WINDOW_SECONDS = {
        RateLimitWindow.SECOND: 1,
        RateLimitWindow.MINUTE: 60,
        RateLimitWindow.HOUR: 3600,
        RateLimitWindow.DAY: 86400,
    }
    
    def __init__(
        self,
        app: ASGIApp,
        redis_url: str,
        rules: Optional[List[RateLimitRule]] = None,
        default_limits: Optional[Dict[RateLimitWindow, int]] = None,
        key_prefix: str = "ratelimit",
        enable_headers: bool = True,
    ):
        """
        Initialize rate limiting middleware.
        
        Args:
            app: The ASGI application
            redis_url: Redis connection URL
            rules: List of rate limit rules to apply
            default_limits: Default limits per window if no rules match
            key_prefix: Prefix for Redis keys
            enable_headers: Whether to add rate limit headers to responses
        """
        super().__init__(app)
        self.redis_client: Optional[Redis] = None
        self.redis_url = redis_url
        self.limiter: Optional[SlidingWindowRateLimiter] = None
        self.rules = rules or self._default_rules()
        self.default_limits = default_limits or {
            RateLimitWindow.SECOND: 10,
            RateLimitWindow.MINUTE: 100,
            RateLimitWindow.HOUR: 1000,
        }
        self.key_prefix = key_prefix
        self.enable_headers = enable_headers
        self._initialized = False
    
    async def _initialize(self):
        """Initialize Redis connection lazily."""
        if not self._initialized:
            try:
                self.redis_client = await redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_keepalive=True,
                    health_check_interval=30,
                )
                self.limiter = SlidingWindowRateLimiter(self.redis_client)
                self._initialized = True
                logger.info("Rate limiter initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize rate limiter: {e}")
                # Continue without rate limiting (fail open)
                self._initialized = True
    
    def _default_rules(self) -> List[RateLimitRule]:
        """Get default rate limiting rules."""
        return [
            # Strict limits for authentication endpoints
            RateLimitRule(
                strategy=RateLimitStrategy.IP_ADDRESS,
                window=RateLimitWindow.MINUTE,
                max_requests=5,
                paths=['/api/v1/auth/login', '/api/v1/auth/register'],
            ),
            # Moderate limits for API endpoints
            RateLimitRule(
                strategy=RateLimitStrategy.USER_ID,
                window=RateLimitWindow.MINUTE,
                max_requests=60,
            ),
            # Generous limits per hour
            RateLimitRule(
                strategy=RateLimitStrategy.USER_ID,
                window=RateLimitWindow.HOUR,
                max_requests=1000,
            ),
            # Global rate limit per IP
            RateLimitRule(
                strategy=RateLimitStrategy.IP_ADDRESS,
                window=RateLimitWindow.MINUTE,
                max_requests=100,
            ),
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with rate limiting.
        
        Args:
            request: The incoming request
            call_next: The next middleware/handler
            
        Returns:
            Response from the application or rate limit error
        """
        # Initialize if needed
        if not self._initialized:
            await self._initialize()
        
        # Skip rate limiting if Redis is not available
        if not self.limiter:
            logger.warning("Rate limiter not available, allowing request")
            return await call_next(request)
        
        # Skip rate limiting for health checks
        if request.url.path in ['/health', '/healthz', '/metrics']:
            return await call_next(request)
        
        # Check rate limits
        rate_limit_result = await self._check_rate_limits(request)
        
        if not rate_limit_result['allowed']:
            # Rate limit exceeded
            response = JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    'error': {
                        'code': 'RATE_LIMIT_EXCEEDED',
                        'message': 'Too many requests. Please try again later.',
                        'retry_after': rate_limit_result['retry_after'],
                    }
                },
            )
            
            # Add rate limit headers
            if self.enable_headers:
                self._add_rate_limit_headers(response, rate_limit_result)
            
            return response
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to successful response
        if self.enable_headers:
            self._add_rate_limit_headers(response, rate_limit_result)
        
        return response
    
    async def _check_rate_limits(self, request: Request) -> Dict[str, Any]:
        """
        Check all applicable rate limits for a request.
        
        Args:
            request: The incoming request
            
        Returns:
            Dictionary with rate limit check results
        """
        results = {
            'allowed': True,
            'limit': 0,
            'remaining': 0,
            'reset': 0,
            'retry_after': 0,
        }
        
        # Find applicable rules
        applicable_rules = self._get_applicable_rules(request)
        
        if not applicable_rules:
            # No rules apply, use defaults
            applicable_rules = [
                RateLimitRule(
                    strategy=RateLimitStrategy.IP_ADDRESS,
                    window=RateLimitWindow.MINUTE,
                    max_requests=self.default_limits[RateLimitWindow.MINUTE],
                )
            ]
        
        # Check each rule
        for rule in applicable_rules:
            # Skip if user/IP is exempt
            if await self._is_exempt(request, rule):
                continue
            
            # Generate rate limit key
            key = await self._generate_key(request, rule)
            if not key:
                continue
            
            # Check rate limit
            window_seconds = self.WINDOW_SECONDS[rule.window]
            allowed, metadata = await self.limiter.is_allowed(
                key=key,
                max_requests=rule.max_requests,
                window_seconds=window_seconds,
            )
            
            # Update results with most restrictive limit
            if not allowed:
                results['allowed'] = False
                results['retry_after'] = max(results['retry_after'], metadata['retry_after'])
            
            # Always update to show the most restrictive limit that applies
            if metadata['remaining'] < results['remaining'] or results['limit'] == 0:
                results['limit'] = metadata['limit']
                results['remaining'] = metadata['remaining']
                results['reset'] = metadata['reset']
        
        return results
    
    def _get_applicable_rules(self, request: Request) -> List[RateLimitRule]:
        """
        Get rate limit rules applicable to the request.
        
        Args:
            request: The incoming request
            
        Returns:
            List of applicable rules
        """
        applicable = []
        
        for rule in self.rules:
            # Check if path matches
            if rule.paths:
                if not any(request.url.path.startswith(path) for path in rule.paths):
                    continue
            
            # Check if method matches
            if rule.methods:
                if request.method not in rule.methods:
                    continue
            
            applicable.append(rule)
        
        return applicable
    
    async def _is_exempt(self, request: Request, rule: RateLimitRule) -> bool:
        """
        Check if request is exempt from rate limiting.
        
        Args:
            request: The incoming request
            rule: The rate limit rule
            
        Returns:
            True if exempt, False otherwise
        """
        # Check IP exemption
        if rule.exempt_ips:
            client_ip = self._get_client_ip(request)
            if client_ip in rule.exempt_ips:
                return True
        
        # Check user ID exemption
        if rule.exempt_user_ids:
            user_id = self._get_user_id(request)
            if user_id and user_id in rule.exempt_user_ids:
                return True
        
        return False
    
    async def _generate_key(self, request: Request, rule: RateLimitRule) -> Optional[str]:
        """
        Generate rate limit key based on strategy.
        
        Args:
            request: The incoming request
            rule: The rate limit rule
            
        Returns:
            Rate limit key or None if key cannot be generated
        """
        parts = [self.key_prefix, rule.strategy.value, rule.window.value]
        
        if rule.strategy == RateLimitStrategy.IP_ADDRESS:
            client_ip = self._get_client_ip(request)
            parts.append(client_ip)
        
        elif rule.strategy == RateLimitStrategy.USER_ID:
            user_id = self._get_user_id(request)
            if not user_id:
                # Fall back to IP if user not authenticated
                client_ip = self._get_client_ip(request)
                parts.append(f"ip:{client_ip}")
            else:
                parts.append(user_id)
        
        elif rule.strategy == RateLimitStrategy.API_KEY:
            api_key = self._get_api_key(request)
            if not api_key:
                return None
            # Hash API key for privacy
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
            parts.append(key_hash)
        
        elif rule.strategy == RateLimitStrategy.ENDPOINT:
            parts.append(request.url.path)
        
        elif rule.strategy == RateLimitStrategy.GLOBAL:
            parts.append("global")
        
        elif rule.strategy == RateLimitStrategy.COMBINED:
            # Combine multiple factors
            client_ip = self._get_client_ip(request)
            user_id = self._get_user_id(request)
            endpoint = request.url.path
            combined = f"{client_ip}:{user_id or 'anon'}:{endpoint}"
            parts.append(hashlib.md5(combined.encode()).hexdigest())
        
        return ":".join(parts)
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Extract client IP address from request.
        
        Args:
            request: The incoming request
            
        Returns:
            Client IP address
        """
        # Check forwarded headers
        forwarded_for = request.headers.get('x-forwarded-for')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('x-real-ip')
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else 'unknown'
    
    def _get_user_id(self, request: Request) -> Optional[str]:
        """
        Extract user ID from request.
        
        Args:
            request: The incoming request
            
        Returns:
            User ID if authenticated, None otherwise
        """
        # Check if user is set in request state (by auth middleware)
        if hasattr(request.state, 'user') and request.state.user:
            user = request.state.user
            if hasattr(user, 'id'):
                return str(user.id)
            elif isinstance(user, dict) and 'id' in user:
                return str(user['id'])
        
        return None
    
    def _get_api_key(self, request: Request) -> Optional[str]:
        """
        Extract API key from request.
        
        Args:
            request: The incoming request
            
        Returns:
            API key if present, None otherwise
        """
        # Check header
        api_key = request.headers.get('x-api-key')
        if api_key:
            return api_key
        
        # Check query parameter
        api_key = request.query_params.get('api_key')
        if api_key:
            return api_key
        
        return None
    
    def _add_rate_limit_headers(self, response: Response, result: Dict[str, Any]):
        """
        Add rate limit headers to response.
        
        Args:
            response: The response object
            result: Rate limit check result
        """
        response.headers['X-RateLimit-Limit'] = str(result['limit'])
        response.headers['X-RateLimit-Remaining'] = str(result['remaining'])
        response.headers['X-RateLimit-Reset'] = str(result['reset'])
        
        if not result['allowed']:
            response.headers['Retry-After'] = str(result['retry_after'])
    
    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Rate limiter closed")
