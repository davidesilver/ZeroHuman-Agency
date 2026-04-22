"""FastAPI JWT Authentication Middleware.

C-01/C-02: Every request to the Python backend must carry a valid Supabase JWT.
The middleware verifies the token, attaches user + brand_id to request.state,
and rejects unauthenticated callers with 401 before they reach any route handler.

Public paths (health, docs) are exempted automatically.
Scheduler endpoints are exempt from JWT but require their own secret (C-06).
"""

from __future__ import annotations

import logging
import uuid
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

        # L-07: Assign X-Request-ID for distributed tracing
        # Use client-provided ID if present (allows end-to-end correlation),
        # otherwise generate a new one.
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        # Skip public & scheduler paths
        if path in _PUBLIC_PATHS or path.startswith(_SCHEDULER_PREFIX):
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response

        # Extract Bearer token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"success": False, "error": {"message": "Missing authentication token"}},
            )

        jwt = auth_header.split(" ", 1)[1]

        import time
        now = time.time()

        # Simple global TTL Cache to avoid hitting Supabase HTTP API on every single request
        global _AUTH_CACHE
        if "_AUTH_CACHE" not in globals():
            _AUTH_CACHE = {}

        # Cleanup old entries occasionally
        if len(_AUTH_CACHE) > 1000:
            _AUTH_CACHE = {k: v for k, v in _AUTH_CACHE.items() if now - v["ts"] < 300}

        try:
            if jwt in _AUTH_CACHE and now - _AUTH_CACHE[jwt]["ts"] < 300:
                user_id = _AUTH_CACHE[jwt]["user_id"]
                brand_id = _AUTH_CACHE[jwt]["brand_id"]
            else:
                # Verify JWT against Supabase auth — uses anon key intentionally
                from supabase import create_client
                client = create_client(settings.supabase_url, settings.supabase_anon_key)
                user_resp = client.auth.get_user(jwt)
                user = user_resp.user

                if not user:
                    raise ValueError("Null user from JWT")

                # P1/P2: Resolve brand memberships from brand_members (N:M).
                # This is the only runtime source of truth for tenant membership.
                db = get_user_db(jwt)
                member_resp = (
                    db.table("brand_members")
                    .select("brand_id")
                    .eq("user_id", user.id)
                    .order("created_at")
                    .execute()
                )
                member_brand_ids: list[str] = [
                    row["brand_id"] for row in (member_resp.data or [])
                ]

                if not member_brand_ids:
                    return JSONResponse(
                        status_code=403,
                        content={"success": False, "error": {"message": "User has no associated brand"}},
                    )

                # Default brand = oldest membership (same as requireAuth() server-side)
                brand_id = member_brand_ids[0]
                user_id = user.id
                _AUTH_CACHE[jwt] = {
                    "user_id": user_id,
                    "brand_id": brand_id,
                    "member_brand_ids": member_brand_ids,
                    "ts": now,
                }

            # P1: X-Brand-ID membership check (replaces strict equality guard).
            # Callers may pass any brand they are a member of; the active brand
            # for this request is the header value if membership is confirmed.
            req_brand_id = request.headers.get("X-Brand-ID")
            member_brand_ids_cached = _AUTH_CACHE[jwt].get("member_brand_ids", [brand_id])
            if req_brand_id:
                if req_brand_id not in member_brand_ids_cached:
                    return JSONResponse(
                        status_code=403,
                        content={
                            "success": False,
                            "error": {"message": "X-Brand-ID is not in user brand membership"},
                        },
                    )
                # Override the default brand with the explicitly requested one
                brand_id = req_brand_id

            # Attach to request state — available in every route handler
            request.state.user_id = user_id
            request.state.brand_id = brand_id
            request.state.member_brand_ids = _AUTH_CACHE[jwt].get("member_brand_ids", [brand_id])
            request.state.jwt = jwt

        except ValueError as e:
            _logger.warning("JWT validation failed [%s]: %s", request_id, e)
            return JSONResponse(
                status_code=401,
                content={"success": False, "error": {"message": "Invalid or expired token"}},
            )
        except Exception as e:
            _logger.error("Auth middleware error [%s]: %s", request_id, e, exc_info=True)
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": {"message": "Authentication service unavailable"}},
            )

        response = await call_next(request)
        # L-07: propagate request_id in response so frontend can correlate logs
        response.headers["X-Request-ID"] = request_id
        return response
