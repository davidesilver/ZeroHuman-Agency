"""Internal API routes — brand secrets management.

These routes are Next.js-internal only (proxied from /api/internal/*).
They expose CRUD for encrypted brand secrets without ever returning plaintext.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..db import get_db
from ..services.brand_secrets import (
    delete_brand_secret,
    set_brand_secret,
)

_logger = logging.getLogger("content_engine.internal")

router = APIRouter(prefix="/internal", tags=["internal"])


def _brand_id(request: Request) -> str:
    brand_id = getattr(request.state, "brand_id", None)
    if not brand_id:
        raise HTTPException(401, "Not authenticated")
    return brand_id


class SecretUpsert(BaseModel):
    provider: str
    key_name: str
    value: str


@router.post("/brand-secrets", status_code=204)
async def upsert_brand_secret(body: SecretUpsert, request: Request):
    """Encrypt and store a brand secret. Returns 204 No Content."""
    brand_id = _brand_id(request)
    if not body.provider.strip() or not body.key_name.strip():
        raise HTTPException(400, "provider and key_name must be non-empty")
    if not body.value.strip():
        raise HTTPException(400, "value must be non-empty")
    set_brand_secret(brand_id, body.provider, body.key_name, body.value)


@router.get("/brand-secrets")
async def check_brand_secret(provider: str, key_name: str, request: Request):
    """Check whether a secret exists without returning its value."""
    brand_id = _brand_id(request)
    result = (
        get_db()
        .from_("brand_integrations")
        .select("updated_at")
        .eq("brand_id", brand_id)
        .eq("provider", provider)
        .eq("key_name", key_name)
        .maybe_single()
        .execute()
    )
    if result.data:
        return {"exists": True, "updated_at": result.data.get("updated_at")}
    return {"exists": False, "updated_at": None}


@router.delete("/brand-secrets", status_code=204)
async def remove_brand_secret(provider: str, key_name: str, request: Request):
    """Delete a brand secret."""
    brand_id = _brand_id(request)
    delete_brand_secret(brand_id, provider, key_name)
