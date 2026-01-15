"""
Redis caching layer for Alethic.

Usage:
    from core.cache import cache
    
    @cache(ttl=60, key_prefix="users")
    async def get_user(user_id: int):
        ...
"""

import json
import logging
import functools
import hashlib
from typing import Any, Callable, Optional, Union
from datetime import datetime, date

from redis.asyncio import Redis, from_url
from core.config import settings

logger = logging.getLogger(__name__)

class RedisCache:
    _instance = None
    _redis: Optional[Redis] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisCache, cls).__new__(cls)
        return cls._instance
    
    async def init(self):
        """Initialize Redis connection."""
        if not self._redis:
            self._redis = from_url(
                str(settings.redis_url),
                encoding="utf-8",
                decode_responses=True
            )
            logger.info("Redis cache initialized")
    
    async def close(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None
            logger.info("Redis cache closed")
            
    @property
    def redis(self) -> Redis:
        if not self._redis:
            raise RuntimeError("Redis cache not initialized. Call init() first.")
        return self._redis

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            val = await self.redis.get(key)
            if val:
                return json.loads(val)
        except Exception as e:
            logger.error(f"Cache get error for {key}: {e}")
        return None

    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in cache."""
        try:
            serialized = json.dumps(value, default=self._json_serializer)
            await self.redis.set(key, serialized, ex=ttl)
            return True
        except Exception as e:
            logger.error(f"Cache set error for {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error for {key}: {e}")
            return False
            
    async def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern."""
        try:
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)
            return len(keys)
        except Exception as e:
            logger.error(f"Cache delete pattern error for {pattern}: {e}")
            return 0

    @staticmethod
    def _json_serializer(obj):
        """JSON serializer for datetime objects."""
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")


# Global instance
redis_cache = RedisCache()


def cache(
    ttl: int = 60,
    key_prefix: str = None,
    key_builder: Callable = None,
):
    """
    Async decorator for caching function results in Redis.
    
    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache key
        key_builder: Optional custom function to build cache key.
                     Receives func, args, kwargs.
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 1. Build cache key
            if key_builder:
                key = key_builder(func, *args, **kwargs)
            else:
                # Default key builder: prefix:func_name:arg_hash
                prefix = key_prefix or func.__module__
                
                # Create a stable representation of args
                # Note: This simple hash might collide or be sensitive to order/types
                # For more robust hashing, inspect signature.
                arg_str = f"{args}-{kwargs}"
                arg_hash = hashlib.md5(arg_str.encode()).hexdigest()
                key = f"{prefix}:{func.__name__}:{arg_hash}"
            
            # 2. Try cache get
            try:
                cached_val = await redis_cache.get(key)
                if cached_val is not None:
                    # logger.debug(f"Cache HIT: {key}")
                    return cached_val
            except Exception:
                # Fail open if cache errors
                pass
            
            # 3. Call actual function
            result = await func(*args, **kwargs)
            
            # 4. Cache set (if result is valid)
            if result is not None:
                # Run in background? usually await is fine for set
                await redis_cache.set(key, result, ttl)
                
            return result
        return wrapper
    return decorator
