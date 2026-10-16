"""Tests for PWA module."""

from unittest.mock import patch

from src.open_llm_vtuber.pwa import create_pwa_router


class TestPWARouter:
    """Tests for PWA router."""

    def test_create_pwa_router(self):
        """Test router creation."""
        router = create_pwa_router(www_dir="www")
        assert router is not None
        assert len(router.routes) > 0

    @patch("os.path.exists", return_value=True)
    def test_pwa_index(self, mock_exists):
        """Test PWA index route."""
        router = create_pwa_router(www_dir="test_www")
        # Verify the route exists
        routes = [r.path for r in router.routes]
        assert "/" in routes or "" in routes

    @patch("os.path.exists", return_value=True)
    def test_pwa_manifest(self, mock_exists):
        """Test PWA manifest route."""
        router = create_pwa_router(www_dir="test_www")
        routes = [r.path for r in router.routes]
        assert "/manifest.json" in routes or "manifest" in str(routes)

    @patch("os.path.exists", return_value=True)
    def test_pwa_sw(self, mock_exists):
        """Test PWA service worker route."""
        router = create_pwa_router(www_dir="test_www")
        routes = [r.path for r in router.routes]
        assert "/sw.js" in routes

    @patch("os.path.exists", return_value=False)
    def test_pwa_fallback(self, mock_exists):
        """Test PWA fallback when files don't exist."""
        router = create_pwa_router(www_dir="nonexistent")
        # Should still create router without errors
        assert router is not None