"""Transport hardening for the HTTP/WebSocket surface (audit A22).

Two independent pieces live here:

* **CORS** -- the previous setup combined ``allow_origins=["*"]`` with
  ``allow_credentials=True``, a combination the CORS spec forbids: browsers
  silently reject the wildcard when credentials are allowed. The wildcard is
  replaced by an explicit allow-list (loopback plus the configured host) and a
  regex that only covers loopback and the RFC 1918 ranges, so OBS on the same
  machine and the debug UI on a phone keep working while an arbitrary website
  no longer gets a CORS pass.
* **Shared token** -- when ``VTUBER_WS_TOKEN`` is set, every WebSocket
  handshake must present it (``?token=...`` or ``Authorization: Bearer ...``).
  An empty value means "local show", i.e. the pre-A22 behaviour, which is why
  the feature is opt-in and cannot break an existing deployment.

The module is stdlib-only on purpose (plus ``loguru``): it must be unit
testable without importing the heavy service context.
"""

import hmac
import os
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

from loguru import logger

WS_TOKEN_ENV = "VTUBER_WS_TOKEN"
CORS_ORIGINS_ENV = "VTUBER_CORS_ORIGINS"
TOKEN_QUERY_PARAM = "token"

#: RFC 6455 "policy violation"; FastAPI turns a pre-accept close into HTTP 403
WS_CLOSE_POLICY_VIOLATION = 1008

_PRIVATE_HOST = (
    r"localhost"
    r"|127(?:\.\d{1,3}){3}"
    r"|0\.0\.0\.0"
    r"|\[::1\]"
    r"|10(?:\.\d{1,3}){3}"
    r"|192\.168(?:\.\d{1,3}){2}"
    r"|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2}"
)

#: Loopback + private LAN, any port. Public origins must be listed explicitly.
LOCAL_ORIGIN_REGEX = r"^https?://(?:" + _PRIVATE_HOST + r")(?::\d{1,5})?$"

_WILDCARD = "*"


# --------------------------------------------------------------------------- #
# Shared token
# --------------------------------------------------------------------------- #
def get_ws_token(token: Optional[str] = None) -> str:
    """Return the active token; an explicit value wins over the environment."""
    if token is not None:
        return token.strip()
    return os.environ.get(WS_TOKEN_ENV, "").strip()


def token_matches(presented: str, token: str) -> bool:
    """Constant-time comparison; always False when either side is empty."""
    if not token or not presented:
        return False
    return hmac.compare_digest(presented.encode("utf-8"), token.encode("utf-8"))


def _as_text(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("latin-1", errors="replace")
    return str(value or "")


def _bearer(header_value: str) -> str:
    scheme, _, credentials = header_value.strip().partition(" ")
    if scheme.lower() == "bearer":
        return credentials.strip()
    return ""


def header_value(websocket: Any, name: str) -> str:
    """Case-insensitive handshake header lookup (works on ASGI fakes too)."""
    headers = getattr(websocket, "headers", None)
    if headers is not None:
        try:
            value = headers.get(name)
        except Exception:  # pragma: no cover - defensive, Headers never fails
            value = None
        if value:
            return _as_text(value)

    scope = getattr(websocket, "scope", None) or {}
    wanted = name.lower()
    for key, value in scope.get("headers", []):
        if _as_text(key).lower() == wanted:
            return _as_text(value)
    return ""


def extract_ws_token(websocket: Any) -> str:
    """Token presented on a WebSocket handshake: query param, then header."""
    query = getattr(websocket, "query_params", None)
    if query is not None:
        try:
            value = query.get(TOKEN_QUERY_PARAM)
        except Exception:  # pragma: no cover - defensive
            value = None
        if value:
            return _as_text(value).strip()
    return _bearer(header_value(websocket, "authorization"))


async def enforce_ws_token(websocket: Any, token: Optional[str] = None) -> bool:
    """Validate the handshake token, closing the socket when it is wrong.

    Returns ``True`` when the connection may proceed. With no token configured
    (the default for a local show) it never rejects nor logs.
    """
    expected = get_ws_token(token)
    if not expected:
        return True

    if token_matches(extract_ws_token(websocket), expected):
        return True

    path = getattr(getattr(websocket, "url", None), "path", "?")
    logger.warning(
        f"Rejected WebSocket handshake on {path}: missing or invalid token. "
        f"Set {WS_TOKEN_ENV} and append ?{TOKEN_QUERY_PARAM}=... to the URL."
    )
    await websocket.close(code=WS_CLOSE_POLICY_VIOLATION)
    return False


def http_token_allowed(request: Any, token: Optional[str] = None) -> bool:
    """Same rule as :func:`enforce_ws_token`, for plain HTTP endpoints."""
    expected = get_ws_token(token)
    if not expected:
        return True

    presented = ""
    query = getattr(request, "query_params", None)
    if query is not None:
        try:
            presented = (query.get(TOKEN_QUERY_PARAM) or "").strip()
        except Exception:  # pragma: no cover - defensive
            presented = ""
    if not presented:
        presented = _bearer(header_value(request, "authorization"))
    return token_matches(presented, expected)


def with_token(url: str, token: Optional[str] = None) -> str:
    """Append the shared token to a WebSocket URL (no-op when unset)."""
    expected = get_ws_token(token)
    if not expected or f"{TOKEN_QUERY_PARAM}=" in url:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}{TOKEN_QUERY_PARAM}={quote(expected, safe='')}"


# --------------------------------------------------------------------------- #
# CORS
# --------------------------------------------------------------------------- #
def build_allowed_origins(host: Optional[str], port: int) -> List[str]:
    """Explicit origins for loopback plus the configured bind address."""
    hosts = ["localhost", "127.0.0.1", "[::1]"]
    configured = (host or "").strip()
    if configured in {"::1", "[::1]"}:
        configured = "[::1]"
    if configured and configured not in {"0.0.0.0", "::", _WILDCARD}:
        if configured not in hosts:
            hosts.append(configured)

    origins: List[str] = []
    for name in hosts:
        for scheme in ("http", "https"):
            origins.append(f"{scheme}://{name}:{port}")
    return origins


def _split_origins(value: Optional[str]) -> List[str]:
    items = (value or "").split(",")
    return [item.strip().rstrip("/") for item in items if item.strip()]


def resolve_cors_policy(
    host: Optional[str],
    port: int,
    extra_origins: Optional[str] = None,
) -> Tuple[List[str], Optional[str]]:
    """Return ``(allow_origins, allow_origin_regex)`` for CORSMiddleware.

    ``extra_origins`` defaults to ``VTUBER_CORS_ORIGINS`` (comma separated).
    Setting it to ``*`` re-enables the old behaviour, deliberately and loudly.
    """
    origins = build_allowed_origins(host, port)
    if extra_origins is None:
        extra_origins = os.environ.get(CORS_ORIGINS_ENV, "")
    for origin in _split_origins(extra_origins):
        if origin not in origins:
            origins.append(origin)

    if _WILDCARD in origins:
        return origins, None
    return origins, LOCAL_ORIGIN_REGEX


def build_cors_settings(
    host: Optional[str],
    port: int,
    extra_origins: Optional[str] = None,
) -> Dict[str, Any]:
    """Keyword arguments for ``app.add_middleware(CORSMiddleware, ...)``."""
    origins, origin_regex = resolve_cors_policy(host, port, extra_origins)
    return {
        "allow_origins": origins,
        "allow_origin_regex": origin_regex,
        # The app has no cookie/session auth, so credentials stay off: that is
        # what makes the wildcard invalid in the first place (audit A22).
        "allow_credentials": False,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
        "max_age": 600,
    }


def origin_allowed(
    origin: Optional[str],
    origins: List[str],
    origin_regex: Optional[str] = None,
) -> bool:
    """Whether a request ``Origin`` may read cross-origin responses."""
    if not origin:
        # Same-origin navigations, curl and the live connectors send no Origin.
        return True
    origin = origin.strip().rstrip("/")
    if _WILDCARD in origins or origin in origins:
        return True
    return bool(origin_regex and re.match(origin_regex, origin))


def scope_origin(scope: Dict[str, Any]) -> str:
    """Extract the ``Origin`` header from an ASGI scope."""
    for key, value in scope.get("headers", []):
        if _as_text(key).lower() == "origin":
            return _as_text(value).strip()
    return ""


def static_cors_headers(
    scope: Dict[str, Any],
    origins: List[str],
    origin_regex: Optional[str] = None,
) -> Dict[str, str]:
    """CORS headers for ``StaticFiles`` responses (never a blind ``*``)."""
    origin = scope_origin(scope)
    if not origin or not origin_allowed(origin, origins, origin_regex):
        return {}

    allow_origin = _WILDCARD if _WILDCARD in origins else origin
    headers = {
        "Access-Control-Allow-Origin": allow_origin,
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "*",
    }
    if allow_origin != _WILDCARD:
        # The answer depends on the request, so caches must key on Origin.
        headers["Vary"] = "Origin"
    return headers
