"""Video rendering API routes (Phase 10 — HyperFrames).

Endpoints:
  POST  /video/render          — enqueue a render job
  GET   /video/:id/status      — poll render status
  GET   /video                 — list videos for active brand
  GET   /video/templates       — list available templates
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from ..db import get_db
from ..services.heygen_client import (
    HeygenError,
    generate_talking_head,
    list_avatars,
    poll_heygen_status,
)
from ..services.video_renderer import (
    VideoRenderError,
    enqueue_render,
    get_video_status,
    list_videos,
)

_logger = logging.getLogger("content_engine.video")

router = APIRouter(prefix="/video", tags=["video"])


def _brand_id(request: Request) -> str:
    brand_id = getattr(request.state, "brand_id", None)
    if not brand_id:
        raise HTTPException(401, "Not authenticated")
    return brand_id


class CreateTemplateRequest(BaseModel):
    name: str
    slug: str
    description: str | None = None
    composition_path: str
    props_schema: dict = {}


@router.post("/templates", status_code=201)
async def create_template(body: CreateTemplateRequest, request: Request):
    """Create a brand-specific video template."""
    brand_id = _brand_id(request)
    if not body.name.strip() or not body.slug.strip():
        raise HTTPException(400, "name and slug are required")
    result = (
        get_db()
        .from_("video_templates")
        .insert({
            "brand_id": brand_id,
            "name": body.name.strip(),
            "slug": body.slug.strip().lower().replace(" ", "-"),
            "description": body.description,
            "composition_path": body.composition_path.strip(),
            "props_schema": body.props_schema,
        })
        .execute()
    )
    return result.data[0] if result.data else {}


class RenderRequest(BaseModel):
    template_slug: str
    render_props: dict
    title: str | None = None


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


# ── Heygen talking-head ────────────────────────────────────────────────────

class TalkingHeadRequest(BaseModel):
    script: str
    avatar_id: str
    voice_id: str | None = None
    title: str | None = None


@router.get("/heygen/avatars")
async def get_heygen_avatars(request: Request):
    brand_id = _brand_id(request)
    try:
        return list_avatars(brand_id)
    except HeygenError as exc:
        raise HTTPException(422, str(exc))


@router.post("/generate", status_code=202)
async def generate_video(body: TalkingHeadRequest, request: Request):
    """Start a Heygen talking-head render (async, returns 202 Accepted)."""
    brand_id = _brand_id(request)
    if not body.script.strip():
        raise HTTPException(400, "script is required")
    if not body.avatar_id.strip():
        raise HTTPException(400, "avatar_id is required")
    try:
        video_id = generate_talking_head(
            brand_id,
            body.script.strip(),
            body.avatar_id.strip(),
            voice_id=body.voice_id,
            title=body.title,
        )
    except HeygenError as exc:
        raise HTTPException(422, str(exc))
    return {"video_id": video_id, "status": "accepted"}


@router.post("/{video_id}/poll-heygen")
async def poll_heygen(video_id: str, request: Request):
    """Manually poll Heygen status for a talking-head video."""
    brand_id = _brand_id(request)
    try:
        return poll_heygen_status(brand_id, video_id)
    except HeygenError as exc:
        raise HTTPException(404, str(exc))
