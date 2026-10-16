"""Tests for security hardening module."""

import pytest
from unittest.mock import MagicMock, patch

from src.open_llm_vtuber.security.hardening import (
    RateLimiter,
    RateLimitConfig,
    get_rate_limiter,
    InputValidator,
    APIKeyManager,
    get_api_key_manager,
    SecurityHeaders,
)


class TestRateLimitConfig:
    """Tests for RateLimitConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = RateLimitConfig()
        assert config.requests_per_window == 100
        assert config.window_seconds == 60
        assert config.burst_allowance == 10

    def test_custom_config(self):
        """Test custom configuration."""
        config = RateLimitConfig(
            requests_per_window=50,
            window_seconds=30,
            burst_allowance=5,
        )
        assert config.requests_per_window == 50
        assert config.window_seconds == 30
        assert config.burst_allowance == 5


class TestRateLimiter:
    """Tests for RateLimiter class."""

    @pytest.fixture
    def limiter(self):
        """Create a rate limiter for testing."""
        return RateLimiter(RateLimitConfig(
            requests_per_window=5,
            window_seconds=60,
            burst_allowance=2,
        ))

    @pytest.mark.asyncio
    async def test_check_rate_limit_allows_first_requests(self, limiter):
        """Test rate limiter allows requests within limit."""
        for i in range(5):
            allowed, info = limiter.check_rate_limit("test_client")
            assert allowed is True
            assert info["remaining"] == 4 - i

    @pytest.mark.asyncio
    async def test_check_rate_limit_blocks_excess(self, limiter):
        """Test rate limiter blocks excess requests."""
        # Use all 5 requests
        for _ in range(5):
            limiter.check_rate_limit("test_client")
        
        # Next request should be blocked
        allowed, info = limiter.check_rate_limit("test_client")
        assert allowed is False
        assert info["allowed"] is False
        assert "retry_after" in info

    @pytest.mark.asyncio
    async def test_check_rate_limit_burst_allowance(self, limiter):
        """Test burst allowance."""
        # First 2 requests use burst
        for _ in range(2):
            allowed, info = limiter.check_rate_limit("burst_client")
            assert allowed is True
            assert info["burst_remaining"] >= 0
        
        # Regular requests after burst
        for i in range(3):
            allowed, info = limiter.check_rate_limit("burst_client")
            assert allowed is True

    @pytest.mark.asyncio
    async def test_different_clients_independent(self, limiter):
        """Test different clients have independent limits."""
        for _ in range(5):
            limiter.check_rate_limit("client_a")
        
        # client_b should still have full allowance
        allowed, info = limiter.check_rate_limit("client_b")
        assert allowed is True
        assert info["remaining"] == 4

    @pytest.mark.asyncio
    async def test_get_client_info(self, limiter):
        """Test get_client_info."""
        limiter.check_rate_limit("info_client")
        limiter.check_rate_limit("info_client")
        
        info = limiter.get_client_info("info_client")
        assert info["requests"] == 2
        assert info["remaining"] == 3


class TestInputValidator:
    """Tests for InputValidator class."""

    def test_validate_text_valid(self):
        """Test valid text passes validation."""
        text = "Hello, world! This is a normal message."
        result = InputValidator.validate_text(text)
        assert result == text

    def test_validate_text_too_long(self):
        """Test text exceeding max length raises error."""
        text = "x" * 10001
        with pytest.raises(ValueError, match="exceeds maximum length"):
            InputValidator.validate_text(text)

    def test_validate_text_dangerous_pattern(self):
        """Test dangerous patterns are rejected."""
        dangerous_inputs = [
            "<script>alert('xss')</script>",
            "javascript:alert(1)",
            "onclick=alert(1)",
            "eval(code)",
            "exec(code)",
            "__import__('os')",
            "subprocess.run",
            "os.system('ls')",
        ]
        
        for dangerous in dangerous_inputs:
            with pytest.raises(ValueError, match="dangerous content"):
                InputValidator.validate_text(dangerous)

    def test_validate_username_valid(self):
        """Test valid username passes validation."""
        usernames = ["user123", "test_user", "user-name", "user.name", "User123"]
        for username in usernames:
            result = InputValidator.validate_username(username)
            assert result == username.lower()

    def test_validate_username_invalid(self):
        """Test invalid usernames are rejected."""
        invalid_usernames = [
            "",  # Empty
            "a" * 101,  # Too long
            "user@name",  # Invalid char
            "user name",  # Space
            "user#name",  # Invalid char
        ]
        
        for username in invalid_usernames:
            with pytest.raises(ValueError):
                InputValidator.validate_username(username)

    def test_validate_audio_data_valid(self):
        """Test valid audio data passes."""
        audio = b"x" * 1000
        result = InputValidator.validate_audio_data(audio)
        assert result == audio

    def test_validate_audio_data_too_large(self):
        """Test oversized audio data is rejected."""
        audio = b"x" * (51 * 1024 * 1024)  # 51MB
        with pytest.raises(ValueError, match="exceeds maximum size"):
            InputValidator.validate_audio_data(audio)

    def test_validate_audio_data_too_small(self):
        """Test undersized audio data is rejected."""
        audio = b"x" * 10
        with pytest.raises(ValueError, match="too small"):
            InputValidator.validate_audio_data(audio)

    def test_sanitize_filename(self):
        """Test filename sanitization."""
        assert InputValidator.sanitize_filename("normal_file.txt") == "normal_file.txt"
        assert InputValidator.sanitize_filename("../etc/passwd") == "etcpasswd"
        assert InputValidator.sanitize_filename("file<script>.txt") == "filescript.txt"
        assert InputValidator.sanitize_filename("a" * 300) == "a" * 255


class TestAPIKeyManager:
    """Tests for APIKeyManager class."""

    @pytest.fixture
    def manager(self):
        """Create API key manager for testing."""
        return APIKeyManager()

    def test_generate_key(self, manager):
        """Test key generation."""
        key = manager.generate_key("test-key", ["read", "write"])
        assert key.startswith("vtuber_")
        assert len(key) > 40

    def test_validate_key_valid(self, manager):
        """Test valid key validation."""
        key = manager.generate_key("test", ["read"])
        assert manager.validate_key(key) is True
        assert manager.validate_key(key, "read") is True

    def test_validate_key_invalid(self, manager):
        """Test invalid key validation."""
        assert manager.validate_key("invalid_key") is False

    def test_validate_key_wrong_permission(self, manager):
        """Test key with insufficient permissions."""
        key = manager.generate_key("test", ["read"])
        assert manager.validate_key(key, "write") is False

    def test_revoke_key(self, manager):
        """Test key revocation."""
        key = manager.generate_key("test")
        assert manager.validate_key(key) is True
        assert manager.revoke_key(key) is True
        assert manager.validate_key(key) is False

    def test_list_keys(self, manager):
        """Test listing keys."""
        manager.generate_key("key1", ["read"])
        manager.generate_key("key2", ["write"])
        
        keys = manager.list_keys()
        assert len(keys) == 2
        assert all("name" in k for k in keys)
        assert all("permissions" in k for k in keys)
        assert all("created_at" in k for k in keys)
        assert all("usage_count" in k for k in keys)


class TestSecurityHeaders:
    """Tests for SecurityHeaders class."""

    def test_get_headers(self):
        """Test security headers."""
        headers = SecurityHeaders.get_headers()
        
        assert "X-Content-Type-Options" in headers
        assert headers["X-Content-Type-Options"] == "nosniff"
        
        assert "X-Frame-Options" in headers
        assert headers["X-Frame-Options"] == "DENY"
        
        assert "Content-Security-Policy" in headers
        assert "default-src 'self'" in headers["Content-Security-Policy"]

    def test_apply_to_response(self):
        """Test applying headers to response."""
        mock_response = MagicMock()
        mock_response.headers = {}
        
        SecurityHeaders.apply_to_response(mock_response)
        
        assert "X-Content-Type-Options" in mock_response.headers
        assert "X-Frame-Options" in mock_response.headers
        assert "Content-Security-Policy" in mock_response.headers


class TestGlobalInstances:
    """Tests for global instances."""

    @patch("src.open_llm_vtuber.security.hardening._rate_limiter", None)
    def test_get_rate_limiter_creates_instance(self):
        """Test get_rate_limiter creates global instance."""
        limiter = get_rate_limiter()
        assert limiter is not None
        assert isinstance(limiter, RateLimiter)

    @patch("src.open_llm_vtuber.security.hardening._api_key_manager", None)
    def test_get_api_key_manager_creates_instance(self):
        """Test get_api_key_manager creates global instance."""
        manager = get_api_key_manager()
        assert manager is not None
        assert isinstance(manager, APIKeyManager)