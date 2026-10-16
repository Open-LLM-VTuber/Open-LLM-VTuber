"""Redis Cache implementation for Open-LLM-VTuber."""

import json
from typing import Any, Optional, Dict, List
from functools import wraps

import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool

from loguru import logger


class RedisCache:
    """Async Redis cache with connection pooling and TTL support."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        max_connections: int = 50,
        default_ttl: int = 300,
        key_prefix: str = "vtuber:",
    ):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.max_connections = max_connections
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[redis.Redis] = None
        self._connected = False

    async def connect(self) -> None:
        """Initialize connection pool and client."""
        if self._connected:
            return

        try:
            self._pool = ConnectionPool.from_url(
                f"redis://{':' + self.password + '@' if self.password else ''}{self.host}:{self.port}/{self.db}",
                max_connections=self.max_connections,
                decode_responses=True,
            )
            self._client = redis.Redis(connection_pool=self._pool)
            await self._client.ping()
            self._connected = True
            logger.info(f"Redis cache connected to {self.host}:{self.port}/{self.db}")
        except Exception as e:
            logger.warning(f"Redis connection failed, caching disabled: {e}")
            self._connected = False
            self._client = None

    async def disconnect(self) -> None:
        """Close connections."""
        if self._client:
            await self._client.aclose()
        if self._pool:
            await self._pool.disconnect()
        self._connected = False
        logger.info("Redis cache disconnected")

    def _make_key(self, key: str) -> str:
        """Add prefix to key."""
        return f"{self.key_prefix}{key}"

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self._connected or not self._client:
            return None
        try:
            value = await self._client.get(self._make_key(key))
            if value is not None:
                return json.loads(value)
        except Exception as e:
            logger.debug(f"Cache get error for {key}: {e}")
        return None

    async def set(
        self, key: str, value: Any, ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache with TTL."""
        if not self._connected or not self._client:
            return False
        try:
            serialized = json.dumps(value, default=str)
            await self._client.setex(
                self._make_key(key), ttl or self.default_ttl, serialized
            )
            return True
        except Exception as e:
            logger.debug(f"Cache set error for {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self._connected or not self._client:
            return False
        try:
            result = await self._client.delete(self._make_key(key))
            return result > 0
        except Exception as e:
            logger.debug(f"Cache delete error for {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        if not self._connected or not self._client:
            return False
        try:
            return await self._client.exists(self._make_key(key)) > 0
        except Exception:
            return False

    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values."""
        if not self._connected or not self._client or not keys:
            return {}
        try:
            prefixed_keys = [self._make_key(k) for k in keys]
            values = await self._client.mget(prefixed_keys)
            result = {}
            for key, value in zip(keys, values):
                if value is not None:
                    result[key] = json.loads(value)
            return result
        except Exception as e:
            logger.debug(f"Cache get_many error: {e}")
            return {}

    async def set_many(
        self, mapping: Dict[str, Any], ttl: Optional[int] = None
    ) -> bool:
        """Set multiple values."""
        if not self._connected or not self._client or not mapping:
            return False
        try:
            prefixed_mapping = {
                self._make_key(k): json.dumps(v, default=str)
                for k, v in mapping.items()
            }
            pipe = self._client.pipeline()
            for key, value in prefixed_mapping.items():
                pipe.setex(key, ttl or self.default_ttl, value)
            await pipe.execute()
            return True
        except Exception as e:
            logger.debug(f"Cache set_many error: {e}")
            return False

    async def invalidate_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern."""
        if not self._connected or not self._client:
            return 0
        try:
            full_pattern = self._make_key(pattern)
            cursor = 0
            deleted = 0
            while True:
                cursor, keys = await self._client.scan(cursor, match=full_pattern, count=100)
                if keys:
                    deleted += await self._client.delete(*keys)
                if cursor == 0:
                    break
            return deleted
        except Exception as e:
            logger.debug(f"Cache invalidate_pattern error: {e}")
            return 0

    async def health_check(self) -> bool:
        """Check Redis connectivity."""
        if not self._connected or not self._client:
            return False
        try:
            await self._client.ping()
            return True
        except Exception:
            self._connected = False
            return False


_cache_instance: Optional[RedisCache] = None


async def get_cache(
    host: str = "localhost",
    port: int = 6379,
    db: int = 0,
    password: Optional[str] = None,
    max_connections: int = 50,
    default_ttl: int = 300,
    key_prefix: str = "vtuber:",
) -> RedisCache:
    """Get or create global cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = RedisCache(
            host=host,
            port=port,
            db=db,
            password=password,
            max_connections=max_connections,
            default_ttl=default_ttl,
            key_prefix=key_prefix,
        )
        await _cache_instance.connect()
    return _cache_instance


async def close_cache() -> None:
    """Close global cache instance."""
    global _cache_instance
    if _cache_instance:
        await _cache_instance.disconnect()
        _cache_instance = None


def cached(ttl: int = 300, key_prefix: str = ""):
    """Decorator for caching async function results."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = await get_cache()
            if not cache._connected:
                return await func(*args, **kwargs)

            cache_key = f"{key_prefix}{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl)
            return result
        return wrapper
    return decorator