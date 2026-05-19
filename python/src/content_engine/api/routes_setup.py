"""Setup wizard progress API.

GET  /setup/progress        — return current brand's setup_progress row
PATCH /setup/progress       — update completed steps or wizard_state
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..db import get_db

_logger = logging.getLogger("content_engine.setup")

router = APIRouter(prefix="/setup", tags=["setup"])


def _brand_id(request: Request) -> str:
    brand_id = getattr(request.state, "brand_id", None)
    if not brand_id:
        raise HTTPException(401, "Not authenticated")
    return brand_id


class ProgressPatch(BaseModel):
    completed: dict[str, bool] | None = None
    wizard_state: dict[str, Any] | None = None
    dismissed: bool | None = None


@router.get("/progress")
async def get_progress(request: Request):
    """Return setup_progress for the active brand, creating a row if absent."""
    brand_id = _brand_id(request)
    db = get_db()
    result = (
        db.from_("setup_progress")
        .select("*")
        .eq("brand_id", brand_id)
        .maybe_single()
        .execute()
    )
    if result.data:
        return result.data

    # Create default row on first access
    insert = (
        db.from_("setup_progress")
        .upsert({"brand_id": brand_id, "completed": {}, "wizard_state": {}, "dismissed": False})
        .execute()
    )
    return insert.data[0] if insert.data else {
        "brand_id": brand_id, "completed": {}, "wizard_state": {}, "dismissed": False
    }


@router.patch("/progress")
async def patch_progress(body: ProgressPatch, request: Request):
    """Merge updates into setup_progress for the active brand."""
    brand_id = _brand_id(request)
    db = get_db()

    # Fetch existing or create
    existing = (
        db.from_("setup_progress")
        .select("completed, wizard_state, dismissed")
        .eq("brand_id", brand_id)
        .maybe_single()
        .execute()
    )
    current = existing.data or {"completed": {}, "wizard_state": {}, "dismissed": False}

    updates: dict[str, Any] = {"brand_id": brand_id}
    if body.completed is not None:
        merged = {**current.get("completed", {}), **body.completed}
        updates["completed"] = merged
    if body.wizard_state is not None:
        merged_state = {**current.get("wizard_state", {}), **body.wizard_state}
        updates["wizard_state"] = merged_state
    if body.dismissed is not None:
        updates["dismissed"] = body.dismissed

    result = db.from_("setup_progress").upsert(updates).execute()
    return result.data[0] if result.data else updates
