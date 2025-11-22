"""
Security Middleware for Open-LLM-VTuber
========================================
Optional authentication and security features for production deployments.
"""

import os
from typing import Optional
from fastapi import Request, WebSocket, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce API key authentication for all requests.

    Set the API_KEY environment variable to enable authentication.
    If API_KEY is not set, authentication is disabled.

    Usage:
        app.add_middleware(APIKeyMiddleware)

    Clients should include the API key in one of the following ways:
    1. Header: Authorization: Bearer YOUR_API_KEY
    2. Header: X-API-Key: YOUR_API_KEY
    3. Query parameter: ?api_key=YOUR_API_KEY
    """

    def __init__(self, app, api_key: Optional[str] = None):
        super().__init__(app)
        self.api_key = api_key or os.getenv("API_KEY")
        if self.api_key:
            logger.info("API key authentication ENABLED")
        else:
            logger.warning(
                "API key authentication DISABLED - set API_KEY environment variable to enable"
            )

    async def dispatch(self, request: Request, call_next):
        # Skip authentication if no API key is configured
        if not self.api_key:
            return await call_next(request)

        # Skip authentication for health check endpoints
        if request.url.path in ["/health", "/", "/favicon.ico"]:
            return await call_next(request)

        # Skip authentication for static files
        if request.url.path.startswith(
            ("/live2d-models", "/bg", "/avatars", "/cache", "/web-tool")
        ):
            return await call_next(request)

        # Extract API key from request
        provided_key = self._extract_api_key(request)

        # Validate API key
        if not provided_key or provided_key != self.api_key:
            logger.warning(
                f"Unauthorized access attempt from {request.client.host} to {request.url.path}"
            )
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "detail": "Invalid or missing API key",
                    "hint": "Include API key in Authorization header or X-API-Key header",
                },
            )

        # Authentication successful
        response = await call_next(request)
        return response

    def _extract_api_key(self, request: Request) -> Optional[str]:
        """Extract API key from request headers or query parameters."""

        # Check Authorization header (Bearer token)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header.replace("Bearer ", "").strip()

        # Check X-API-Key header
        api_key_header = request.headers.get("X-API-Key", "")
        if api_key_header:
            return api_key_header.strip()

        # Check query parameter
        api_key_param = request.query_params.get("api_key", "")
        if api_key_param:
            return api_key_param.strip()

        return None


async def verify_websocket_auth(websocket: WebSocket, required_api_key: Optional[str] = None) -> bool:
    """
    Verify WebSocket connection authentication.

    Args:
        websocket: The WebSocket connection
        required_api_key: The required API key (if None, uses API_KEY env var)

    Returns:
        True if authentication is successful or disabled, False otherwise

    Usage in WebSocket endpoint:
        if not await verify_websocket_auth(websocket):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    """
    api_key = required_api_key or os.getenv("API_KEY")

    # Skip authentication if no API key is configured
    if not api_key:
        return True

    # Extract API key from query parameters or headers
    provided_key = None

    # Check query parameters
    query_params = dict(websocket.query_params)
    if "api_key" in query_params:
        provided_key = query_params["api_key"]

    # Check headers
    if not provided_key:
        headers = dict(websocket.headers)
        if "authorization" in headers:
            auth = headers["authorization"]
            if auth.startswith("Bearer "):
                provided_key = auth.replace("Bearer ", "").strip()
        elif "x-api-key" in headers:
            provided_key = headers["x-api-key"]

    # Validate API key
    if not provided_key or provided_key != api_key:
        logger.warning(
            f"Unauthorized WebSocket connection attempt from {websocket.client.host}"
        )
        return False

    logger.info(f"WebSocket connection authenticated from {websocket.client.host}")
    return True


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.

    Adds headers like:
    - X-Content-Type-Options
    - X-Frame-Options
    - X-XSS-Protection
    - Strict-Transport-Security (HSTS)
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Add HSTS header for HTTPS connections
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple rate limiting middleware to prevent abuse.

    Limits requests per IP address.
    """

    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}  # {ip: [(timestamp, count)]}

    async def dispatch(self, request: Request, call_next):
        import time

        client_ip = request.client.host
        current_time = time.time()

        # Clean old entries
        if client_ip in self.requests:
            self.requests[client_ip] = [
                (ts, count)
                for ts, count in self.requests[client_ip]
                if current_time - ts < self.window_seconds
            ]

        # Count requests
        if client_ip not in self.requests:
            self.requests[client_ip] = []

        request_count = sum(count for _, count in self.requests[client_ip])

        if request_count >= self.max_requests:
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded. Please try again later."},
            )

        # Add this request
        self.requests[client_ip].append((current_time, 1))

        response = await call_next(request)
        return response
