"""Postiz bridge routes — proxy to Postiz Public API with brand scoping."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..services.postiz_client import PostizClient
from ..services.postiz_publisher import _is_postiz_enabled
from ..db import get_db
from .routes import _get_brand_id

_logger = logging.getLogger("content_engine.api.postiz")
router = APIRouter(prefix="/social", tags=["social"])


# ── Health ───────────────────────────────────────────────────────────────────

@router.get("/health")
async def postiz_health():
    """Check Postiz connectivity. Works for both self-hosted and cloud."""
    if not _is_postiz_enabled():
        return {"success": True, "data": {"status": "disabled", "mode": "disabled"}}
    try:
        client = PostizClient()
        await client.health()
        return {"success": True, "data": {"status": "ok", "mode": "connected"}}
    except Exception as e:
        return {"success": True, "data": {"status": "error", "error": str(e)}}


# ── Integrations ─────────────────────────────────────────────────────────────

@router.get("/integrations")
async def list_integrations(request: Request):
    """Proxy to Postiz integrations list. Useful for discovering available channels."""
    _get_brand_id(request)  # auth guard
    try:
        client = PostizClient()
        data = await client.list_integrations()
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(502, f"Postiz error: {e}")


# ── Analytics ────────────────────────────────────────────────────────────────

@router.get("/analytics")
async def get_analytics(
    request: Request,
    integration_id: str,
    days: int = 7,
):
    brand_id = _get_brand_id(request)
    try:
        client = PostizClient()
        data = await client.get_platform_analytics(integration_id, days=days)
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(502, f"Postiz analytics error: {e}")


# ── Brand-scoped integrations CRUD ───────────────────────────────────────────

@router.get("/integrations/mine")
async def list_my_integrations(request: Request):
    """List integrations stored for the current brand (our DB, not Postiz)."""
    brand_id = _get_brand_id(request)
    db = get_db()
    rows = (
        db.table("brand_social_integrations")
        .select("*")
        .eq("brand_id", brand_id)
        .order("platform")
        .execute()
        .data
        or []
    )
    return {"success": True, "data": rows}


class IntegrationUpsertBody(BaseModel):
    platform: str
    postiz_integration_id: str
    postiz_channel_name: str | None = None
    is_active: bool = True


@router.post("/integrations/mine")
async def upsert_integration(body: IntegrationUpsertBody, request: Request):
    brand_id = _get_brand_id(request)
    db = get_db()

    # Check if exists
    existing = (
        db.table("brand_social_integrations")
        .select("id")
        .eq("brand_id", brand_id)
        .eq("platform", body.platform)
        .execute()
        .data
    )

    payload = {
        "brand_id": brand_id,
        "platform": body.platform,
        "postiz_integration_id": body.postiz_integration_id,
        "postiz_channel_name": body.postiz_channel_name,
        "is_active": body.is_active,
    }

    if existing:
        updated = (
            db.table("brand_social_integrations")
            .update(payload)
            .eq("id", existing[0]["id"])
            .execute()
            .data[0]
        )
        return {"success": True, "data": updated, "message": "Updated"}
    else:
        created = (
            db.table("brand_social_integrations")
            .insert(payload)
            .execute()
            .data[0]
        )
        return {"success": True, "data": created, "message": "Created"}


@router.delete("/integrations/mine/{platform}")
async def delete_integration(platform: str, request: Request):
    brand_id = _get_brand_id(request)
    db = get_db()
    db.table("brand_social_integrations").delete().eq("brand_id", brand_id).eq(
        "platform", platform
    ).execute()
    return {"success": True, "data": {"deleted": platform}}
