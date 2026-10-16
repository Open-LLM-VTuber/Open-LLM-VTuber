"""Tests for cache module."""

import pytest
from unittest.mock import AsyncMock, patch

from src.open_llm_vtuber.cache.redis_cache import RedisCache, get_cache, close_cache, cached


class TestRedisCache:
    """Tests for RedisCache class."""

    @pytest.fixture
    def cache(self):
        """Create a cache instance for testing."""
        return RedisCache(host="localhost", port=6379, default_ttl=60)

    @pytest.mark.asyncio
    async def test_make_key(self, cache):
        """Test key prefixing."""
        assert cache._make_key("test") == "vtuber:test"

    @pytest.mark.asyncio
    async def test_get_set_not_connected(self, cache):
        """Test get/set when not connected."""
        assert await cache.get("test") is None
        assert await cache.set("test", "value") is False
        assert await cache.delete("test") is False
        assert await cache.exists("test") is False

    @pytest.mark.asyncio
    async def test_get_many_empty(self, cache):
        """Test get_many with empty list."""
        assert await cache.get_many([]) == {}

    @pytest.mark.asyncio
    async def test_set_many_empty(self, cache):
        """Test set_many with empty dict."""
        assert await cache.set_many({}) is False

    @pytest.mark.asyncio
    async def test_invalidate_pattern_not_connected(self, cache):
        """Test invalidate_pattern when not connected."""
        assert await cache.invalidate_pattern("*") == 0

    @pytest.mark.asyncio
    async def test_health_check_not_connected(self, cache):
        """Test health_check when not connected."""
        assert await cache.health_check() is False


class TestCacheDecorator:
    """Tests for cached decorator."""

    @pytest.mark.asyncio
    async def test_cached_decorator_not_connected(self):
        """Test cached decorator when cache not connected."""
        call_count = 0
        
        @cached(ttl=60)
        async def test_func(x):
            nonlocal call_count
            call_count += 1
            return x * 2
        
        # First call
        result1 = await test_func(5)
        assert result1 == 10
        assert call_count == 1
        
        # Second call should also execute since cache not connected
        result2 = await test_func(5)
        assert result2 == 10
        assert call_count == 2


class TestGlobalCache:
    """Tests for global cache functions."""

    @pytest.mark.asyncio
    async def test_get_cache_creates_instance(self):
        """Test get_cache creates global instance."""
        # Reset global instance
        import src.open_llm_vtuber.cache.redis_cache as cache_module
        cache_module._cache_instance = None
        
        with patch.object(RedisCache, "connect", new_callable=AsyncMock) as mock_connect:
            cache = await get_cache()
            assert cache is not None
            mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_cache(self):
        """Test close_cache."""
        import src.open_llm_vtuber.cache.redis_cache as cache_module
        cache_module._cache_instance = RedisCache()
        
        with patch.object(RedisCache, "disconnect", new_callable=AsyncMock) as mock_disconnect:
            await close_cache()
            mock_disconnect.assert_called_once()