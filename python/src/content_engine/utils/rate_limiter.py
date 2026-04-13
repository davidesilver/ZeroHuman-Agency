"""In-memory rate limiter middleware for FastAPI.

Protects expensive LLM-calling routes from accidental loops or abuse.
Uses a sliding window counter per IP + path.
"""

from __future__ import annotations

import time
from collections import defaultdict

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitState:
    """Track request timestamps per key (ip:path)."""

    def __init__(self) -> None:
        self._requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> bool:
        now = time.monotonic()
        cutoff = now - window_seconds

        # Prune old entries
        self._requests[key] = [t for t in self._requests[key] if t > cutoff]

        if len(self._requests[key]) >= max_requests:
            return False

        self._requests[key].append(now)
        return True


# Route-specific limits: (max_requests, window_seconds)
# Expensive routes (LLM calls) get strict limits
ROUTE_LIMITS: dict[str, tuple[int, int]] = {
    "/api/research/trigger": (3, 60),          # 3 per minute
    "/api/scoring/run": (5, 60),               # 5 per minute
    "/api/content/generate": (5, 60),          # 5 per minute
    "/api/scheduler/daily-pipeline": (1, 300),  # 1 per 5 minutes
    "/api/newsletter/send": (2, 60),           # 2 per minute
    "/api/social/publish/linkedin": (3, 60),   # 3 per minute
}

# Default limit for non-LLM routes
DEFAULT_LIMIT = (60, 60)  # 60 per minute

# Routes with god-mode in path get special handling
GOD_MODE_LIMIT = (3, 60)  # 3 per minute


_state = RateLimitState()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware.

    Applies per-route limits to protect expensive operations,
    especially LLM-calling endpoints that can burn API credits.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # Only rate-limit POST routes (mutations/expensive ops)
        if request.method != "POST":
            return await call_next(request)

        # Determine limit
        if "god-mode" in path:
            max_req, window = GOD_MODE_LIMIT
        elif path in ROUTE_LIMITS:
            max_req, window = ROUTE_LIMITS[path]
        else:
            max_req, window = DEFAULT_LIMIT

        # Key = client IP + path
        client_ip = request.client.host if request.client else "unknown"
        key = f"{client_ip}:{path}"

        if not _state.is_allowed(key, max_req, window):
            return Response(
                content=f'{{"success": false, "error": "Rate limit exceeded: max {max_req} requests per {window}s"}}',
                status_code=429,
                media_type="application/json",
            )

        return await call_next(request)
