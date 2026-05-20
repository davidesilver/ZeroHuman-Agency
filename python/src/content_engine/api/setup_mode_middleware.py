"""Setup Mode Middleware.

When NEXT_PUBLIC_SUPABASE_URL is not configured, the backend runs in degraded
mode: only /health responds normally. Every other route returns 503 with a
clear message directing the user to run 'zh init' or visit /bootstrap.
"""

from __future__ import annotations

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..config import settings

_SETUP_REQUIRED_PATHS_EXEMPT = {"/health", "/docs", "/openapi.json", "/redoc"}


class SetupModeMiddleware(BaseHTTPMiddleware):
    """Return 503 on all non-health routes when Supabase is not configured."""

    async def dispatch(self, request: Request, call_next) -> Response:
        if settings.next_public_supabase_url:
            return await call_next(request)

        path = request.url.path
        if path in _SETUP_REQUIRED_PATHS_EXEMPT or path.startswith("/redoc"):
            return await call_next(request)

        return JSONResponse(
            status_code=503,
            content={
                "detail": "Setup required — run `zh init` or visit /bootstrap to configure the application.",
                "setup_required": True,
            },
        )
