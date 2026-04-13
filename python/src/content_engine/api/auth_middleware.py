"""FastAPI JWT Authentication Middleware.

C-01/C-02: Every request to the Python backend must carry a valid Supabase JWT.
The middleware verifies the token, attaches user + brand_id to request.state,
and rejects unauthenticated callers with 401 before they reach any route handler.

Public paths (health, docs) are exempted automatically.
Scheduler endpoints are exempt from JWT but require their own secret (C-06).
"""

from __future__ import annotations

import logging
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..config import settings
from ..db import get_user_db

_logger = logging.getLogger("content_engine.auth")

# Paths that do NOT require a JWT token
_PUBLIC_PATHS = {
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
}

# Scheduler endpoints use a separate secret (C-06) — exempt from JWT
_SCHEDULER_PREFIX = "/api/scheduler/"


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """C-01/C-02: Verify Supabase JWT on every non-public request.

    On success, attaches to request.state:
        - user_id   (str) — Supabase auth.users.id
        - brand_id  (str) — brand associated with the user
        - jwt       (str) — raw token (available for user-scoped DB client)
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        # Skip public & scheduler paths
        if path in _PUBLIC_PATHS or path.startswith(_SCHEDULER_PREFIX):
            return await call_next(request)

        # Extract Bearer token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"success": False, "error": {"message": "Missing authentication token"}},
            )

        jwt = auth_header.split(" ", 1)[1]

        try:
            # Verify JWT against Supabase auth — uses anon key intentionally
            # (service role is not needed to verify a JWT)
            from supabase import create_client
            client = create_client(settings.supabase_url, settings.supabase_anon_key)
            user_resp = client.auth.get_user(jwt)
            user = user_resp.user

            if not user:
                raise ValueError("Null user from JWT")

            # Resolve brand_id from users table
            brand_resp = (
                get_user_db(jwt)
                .table("users")
                .select("brand_id")
                .eq("id", user.id)
                .single()
                .execute()
            )
            brand_id = brand_resp.data.get("brand_id") if brand_resp.data else None
            if not brand_id:
                return JSONResponse(
                    status_code=403,
                    content={"success": False, "error": {"message": "User has no associated brand"}},
                )

            # Attach to request state — available in every route handler
            request.state.user_id = user.id
            request.state.brand_id = brand_id
            request.state.jwt = jwt

        except ValueError as e:
            _logger.warning("JWT validation failed: %s", e)
            return JSONResponse(
                status_code=401,
                content={"success": False, "error": {"message": "Invalid or expired token"}},
            )
        except Exception as e:
            _logger.error("Auth middleware error: %s", e, exc_info=True)
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": {"message": "Authentication service unavailable"}},
            )

        return await call_next(request)
