"""Security hardening for Open-LLM-VTuber."""

import re
import time
import hashlib
import secrets
from typing import Dict, Optional, Tuple
from collections import defaultdict
from dataclasses import dataclass, field
from functools import wraps

from loguru import logger


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    requests_per_window: int = 100
    window_seconds: int = 60
    burst_allowance: int = 10


@dataclass
class ClientRateLimit:
    """Per-client rate limit state."""
    requests: int = 0
    window_start: float = field(default_factory=time.time)
    burst_used: int = 0
    last_request: float = field(default_factory=time.time)


class RateLimiter:
    """Token bucket rate limiter with per-client tracking."""
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self.clients: Dict[str, ClientRateLimit] = defaultdict(ClientRateLimit)
        self._cleanup_interval = 300  # 5 minutes
        self._last_cleanup = time.time()
    
    def _cleanup_expired(self) -> None:
        """Remove expired client entries."""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return
        
        expired = [
            client_id for client_id, state in self.clients.items()
            if now - state.window_start > self.config.window_seconds * 2
        ]
        for client_id in expired:
            del self.clients[client_id]
        self._last_cleanup = now
    
    def check_rate_limit(self, client_id: str) -> Tuple[bool, Dict[str, any]]:
        """
        Check if client is within rate limits.
        Returns (allowed, info_dict).
        """
        self._cleanup_expired()
        now = time.time()
        state = self.clients[client_id]
        
        # Reset window if expired
        if now - state.window_start >= self.config.window_seconds:
            state.requests = 0
            state.window_start = now
            state.burst_used = 0
        
        # Check burst allowance
        if state.requests < self.config.burst_allowance:
            state.requests += 1
            state.burst_used += 1
            state.last_request = now
            return True, {
                "allowed": True,
                "remaining": self.config.requests_per_window - state.requests,
                "reset_in": int(self.config.window_seconds - (now - state.window_start)),
                "burst_remaining": self.config.burst_allowance - state.burst_used,
            }
        
        # Check regular limit
        if state.requests >= self.config.requests_per_window:
            return False, {
                "allowed": False,
                "remaining": 0,
                "reset_in": int(self.config.window_seconds - (now - state.window_start)),
                "retry_after": int(self.config.window_seconds - (now - state.window_start)) + 1,
            }
        
        # Within limits
        state.requests += 1
        state.last_request = now
        return True, {
            "allowed": True,
            "remaining": self.config.requests_per_window - state.requests,
            "reset_in": int(self.config.window_seconds - (now - state.window_start)),
            "burst_remaining": max(0, self.config.burst_allowance - state.burst_used),
        }
    
    def get_client_info(self, client_id: str) -> Dict[str, any]:
        """Get current rate limit info for client."""
        state = self.clients.get(client_id)
        if not state:
            return {
                "requests": 0,
                "remaining": self.config.requests_per_window,
                "reset_in": self.config.window_seconds,
            }
        now = time.time()
        return {
            "requests": state.requests,
            "remaining": max(0, self.config.requests_per_window - state.requests),
            "reset_in": max(0, int(self.config.window_seconds - (now - state.window_start))),
            "burst_remaining": max(0, self.config.burst_allowance - state.burst_used),
        }


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter(config: Optional[RateLimitConfig] = None) -> RateLimiter:
    """Get global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter(config)
    return _rate_limiter


def rate_limit(endpoint: str = "default", config: Optional[RateLimitConfig] = None):
    """Decorator for rate limiting async functions."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract client_id from args/kwargs
            client_id = kwargs.get("client_id") or (args[0] if args else "anonymous")
            limiter = get_rate_limiter(config)
            allowed, info = limiter.check_rate_limit(f"{endpoint}:{client_id}")
            
            if not allowed:
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "Rate limit exceeded",
                        "retry_after": info.get("retry_after", 60),
                    },
                    headers={"Retry-After": str(info.get("retry_after", 60))},
                )
            
            # Add rate limit info to response headers if possible
            result = await func(*args, **kwargs)
            return result
        return wrapper
    return decorator


class InputValidator:
    """Input validation and sanitization."""
    
    # Maximum lengths for various inputs
    MAX_TEXT_LENGTH = 10000
    MAX_USERNAME_LENGTH = 100
    MAX_MESSAGE_LENGTH = 5000
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    
    # Allowed characters for usernames
    USERNAME_PATTERN = r"^[a-zA-Z0-9_\-\.]{1,100}$"
    
    # Dangerous patterns to detect
    DANGEROUS_PATTERNS = [
        r"<script",
        r"javascript:",
        r"on\w+\s*=",
        r"eval\s*\(",
        r"exec\s*\(",
        r"__import__",
        r"subprocess",
        r"os\.system",
    ]
    
    @classmethod
    def validate_text(cls, text: str, max_length: Optional[int] = None) -> str:
        """Validate and sanitize text input."""
        if not isinstance(text, str):
            raise ValueError("Input must be a string")
        
        max_len = max_length or cls.MAX_TEXT_LENGTH
        if len(text) > max_len:
            raise ValueError(f"Text exceeds maximum length of {max_len}")
        
        # Check for dangerous patterns
        text_lower = text.lower()
        for pattern in cls.DANGEROUS_PATTERNS:
            # Use regex search for patterns with special chars, otherwise simple substring
            if any(c in pattern for c in r'\.*+?^${}[]|()'):
                if re.search(pattern, text_lower):
                    logger.warning(f"Dangerous pattern detected: {pattern}")
                    raise ValueError("Input contains potentially dangerous content")
            elif pattern in text_lower:
                logger.warning(f"Dangerous pattern detected: {pattern}")
                raise ValueError("Input contains potentially dangerous content")
        
        return text
    
    @classmethod
    def validate_username(cls, username: str) -> str:
        """Validate username."""
        if not isinstance(username, str):
            raise ValueError("Username must be a string")
        
        if len(username) > cls.MAX_USERNAME_LENGTH:
            raise ValueError(f"Username exceeds maximum length of {cls.MAX_USERNAME_LENGTH}")
        
        import re
        if not re.match(cls.USERNAME_PATTERN, username):
            raise ValueError("Username contains invalid characters")
        
        return username.lower().strip()
    
    @classmethod
    def validate_audio_data(cls, audio_data: bytes) -> bytes:
        """Validate audio data."""
        if not isinstance(audio_data, bytes):
            raise ValueError("Audio data must be bytes")
        
        if len(audio_data) > cls.MAX_FILE_SIZE:
            raise ValueError(f"Audio file exceeds maximum size of {cls.MAX_FILE_SIZE} bytes")
        
        if len(audio_data) < 44:  # Minimum WAV header
            raise ValueError("Audio data too small to be valid")
        
        return audio_data
    
    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """Sanitize filename for safe storage."""
        import re
        # Remove path traversal attempts
        filename = filename.replace("..", "").replace("/", "").replace("\\", "")
        # Remove non-printable characters
        filename = re.sub(r"[^\w\-\.\s]", "", filename)
        # Limit length
        return filename[:255]


class APIKeyManager:
    """API key management for external services."""
    
    def __init__(self):
        self.keys: Dict[str, Dict[str, any]] = {}
    
    def generate_key(self, name: str, permissions: Optional[list] = None) -> str:
        """Generate a new API key."""
        key = f"vtuber_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        self.keys[key_hash] = {
            "name": name,
            "permissions": permissions or ["read"],
            "created_at": time.time(),
            "last_used": None,
            "usage_count": 0,
        }
        return key
    
    def validate_key(self, key: str, required_permission: Optional[str] = None) -> bool:
        """Validate an API key."""
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        key_info = self.keys.get(key_hash)
        
        if not key_info:
            return False
        
        if required_permission and required_permission not in key_info["permissions"]:
            return False
        
        key_info["last_used"] = time.time()
        key_info["usage_count"] += 1
        return True
    
    def revoke_key(self, key: str) -> bool:
        """Revoke an API key."""
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        if key_hash in self.keys:
            del self.keys[key_hash]
            return True
        return False
    
    def list_keys(self) -> list:
        """List all API keys (without the actual keys)."""
        return [
            {
                "name": info["name"],
                "permissions": info["permissions"],
                "created_at": info["created_at"],
                "last_used": info["last_used"],
                "usage_count": info["usage_count"],
            }
            for info in self.keys.values()
        ]


# Global instances
_api_key_manager: Optional[APIKeyManager] = None


def get_api_key_manager() -> APIKeyManager:
    """Get global API key manager."""
    global _api_key_manager
    if _api_key_manager is None:
        _api_key_manager = APIKeyManager()
    return _api_key_manager


class SecurityHeaders:
    """Security headers for HTTP responses."""
    
    @staticmethod
    def get_headers() -> Dict[str, str]:
        """Get recommended security headers."""
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' wss: https:;",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        }
    
    @staticmethod
    def apply_to_response(response) -> None:
        """Apply security headers to FastAPI response."""
        for header, value in SecurityHeaders.get_headers().items():
            response.headers[header] = value