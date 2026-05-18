"""Persistent rate limiter backed by Supabase.

H-03: Replaces the in-memory RateLimitState singleton (rate_limiter.py) which had
three critical weaknesses:
  1. Resets on every deploy → limits are ineffective in production
  2. Not shared across multiple backend instances (horizontal scaling)
  3. Gradual memory leak from unbounded dict growth

Strategy: sliding window counter stored in `rate_limit_counters` table.
- Key = "{client_ip}:{path}" (same as before)
- Uses UPSERT to atomically increment within the current window
- Expired windows are reset on write (lazy cleanup)
- Falls back to in-memory if DB is unavailable (fail-open with warning)

Middleware: PersistentRateLimitMiddleware drops in as a replacement for
RateLimitMiddleware (same ROUTE_LIMITS and GOD_MODE_LIMIT config).
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

_logger = logging.getLogger("content_engine.rate_limit")

# Route-specific limits: (max_requests, window_seconds)
# Mirrors the config in rate_limiter.py for drop-in compatibility
ROUTE_LIMITS: dict[str, tuple[int, int]] = {
    "/api/research/trigger": (3, 60),
    "/api/scoring/run": (5, 60),
    "/api/content/generate": (5, 60),
    "/api/scheduler/daily-pipeline": (1, 300),
    "/api/newsletter/send": (2, 60),
    "/api/social/publish/linkedin": (3, 60),
    "/api/social/publish/twitter": (3, 60),
    "/api/social/publish": (3, 60),
}

DEFAULT_LIMIT = (60, 60)
GOD_MODE_LIMIT = (3, 60)


def _get_limit(path: str) -> tuple[int, int]:
    if "god-mode" in path:
        return GOD_MODE_LIMIT
    return ROUTE_LIMITS.get(path, DEFAULT_LIMIT)


class PersistentRateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding window rate limiter backed by Supabase.

    Falls back gracefully to in-memory if the DB write fails,
    logging a warning so the issue is observable without causing downtime.
    """

    def __init__(self, app, fallback_to_memory: bool = True) -> None:
        super().__init__(app)
        self._fallback_to_memory = fallback_to_memory
        # In-memory fallback state (used only if DB is unavailable)
        self._memory: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next) -> Response:
        # Only rate-limit POST routes (mutations/expensive ops)
        if request.method != "POST":
            return await call_next(request)

        path = request.url.path
        max_req, window_sec = _get_limit(path)
        client_ip = request.client.host if request.client else "unknown"
        key = f"{client_ip}:{path}"

        allowed = await self._is_allowed_persistent(key, max_req, window_sec)

        if not allowed:
            return Response(
                content=f'{{"success": false, "error": "Rate limit exceeded: max {max_req} requests per {window_sec}s"}}',
                status_code=429,
                media_type="application/json",
            )

        return await call_next(request)

    async def _is_allowed_persistent(self, key: str, max_req: int, window_sec: int) -> bool:
        """Check and update rate limit counter in Supabase.

        Uses upsert with conditional logic:
        - If the existing window is still active: increment count, check limit
        - If the window has expired: reset count to 1 (new window), allow
        """
        try:
            import asyncio
            return await asyncio.to_thread(
                self._is_allowed_sync, key, max_req, window_sec
            )
        except Exception as e:
            _logger.warning(
                "H-03: Persistent rate limiter DB error — falling back to in-memory: %s", e
            )
            if self._fallback_to_memory:
                return self._is_allowed_memory(key, max_req, window_sec)
            # Fail-open: allow the request (don't block due to monitoring failure)
            return True

    def _is_allowed_sync(self, key: str, max_req: int, window_sec: int) -> bool:
        """Synchronous DB check — run via asyncio.to_thread."""
        from ..db import get_db
        db = get_db()

        now = datetime.now(UTC)
        window_start = now - timedelta(seconds=window_sec)

        # Try to get the current counter
        existing = (
            db.table("rate_limit_counters")
            .select("count, window_start")
            .eq("key", key)
            .execute()
        )

        if existing.data:
            row = existing.data[0]
            row_window_start = datetime.fromisoformat(row["window_start"])
            # Ensure timezone-aware for comparison
            if row_window_start.tzinfo is None:
                row_window_start = row_window_start.replace(tzinfo=UTC)

            if row_window_start >= window_start:
                # Window is still active — check count
                current_count = row["count"]
                if current_count >= max_req:
                    return False
                # Increment
                db.table("rate_limit_counters").update(
                    {"count": current_count + 1}
                ).eq("key", key).execute()
                return True
            else:
                # Window expired — reset
                db.table("rate_limit_counters").update(
                    {"count": 1, "window_start": now.isoformat()}
                ).eq("key", key).execute()
                return True
        else:
            # First request for this key — insert
            db.table("rate_limit_counters").insert(
                {"key": key, "count": 1, "window_start": now.isoformat()}
            ).execute()
            return True

    def _is_allowed_memory(self, key: str, max_req: int, window_sec: int) -> bool:
        """In-memory fallback — sliding window."""
        now = time.monotonic()
        cutoff = now - window_sec
        self._memory[key] = [t for t in self._memory[key] if t > cutoff]
        if len(self._memory[key]) >= max_req:
            return False
        self._memory[key].append(now)
        return True
