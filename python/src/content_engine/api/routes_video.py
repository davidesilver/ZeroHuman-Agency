"""Video rendering API routes (Phase 10 — HyperFrames).

Endpoints:
  POST  /video/render          — enqueue a render job
  GET   /video/:id/status      — poll render status
  GET   /video                 — list videos for active brand
  GET   /video/templates       — list available templates
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from ..services.video_renderer import (
    VideoRenderError,
    enqueue_render,
    get_video_status,
    list_videos,
)
from ..db import get_db

_logger = logging.getLogger("content_engine.video")

router = APIRouter(prefix="/video", tags=["video"])


def _brand_id(request: Request) -> str:
    brand_id = getattr(request.state, "brand_id", None)
    if not brand_id:
        raise HTTPException(401, "Not authenticated")
    return brand_id


class RenderRequest(BaseModel):
    template_slug: str
    render_props: dict
    title: Optional[str] = None


@router.post("/render", status_code=202)
async def start_render(body: RenderRequest, request: Request):
    """Start a video render job (async, returns 202 Accepted)."""
    brand_id = _brand_id(request)
    if not body.template_slug.strip():
        raise HTTPException(400, "template_slug is required")
    try:
        video_id = enqueue_render(brand_id, body.template_slug, body.render_props, body.title)
    except VideoRenderError as exc:
        raise HTTPException(422, str(exc))
    return {"video_id": video_id, "status": "accepted"}


@router.get("/{video_id}/status")
async def poll_status(video_id: str, request: Request):
    brand_id = _brand_id(request)
    try:
        return get_video_status(video_id, brand_id)
    except VideoRenderError as exc:
        raise HTTPException(404, str(exc))


@router.get("")
async def list_brand_videos(
    request: Request,
    limit: int = Query(20, le=100),
):
    brand_id = _brand_id(request)
    return list_videos(brand_id, limit=limit)


@router.get("/templates")
async def list_templates(request: Request):
    """List video templates available to the active brand (system + brand-specific)."""
    brand_id = _brand_id(request)
    result = (
        get_db()
        .from_("video_templates")
        .select("id, name, slug, description, props_schema, thumbnail_url")
        .or_(f"brand_id.is.null,brand_id.eq.{brand_id}")
        .order("name")
        .execute()
    )
    return result.data or []
