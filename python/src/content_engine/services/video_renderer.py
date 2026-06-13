"""HyperFrames video rendering service.

Renders HTML compositions to MP4 via the `hyperframes` CLI (Node.js).
Jobs are tracked in the `videos` table and output is stored in Supabase Storage.

Usage:
    from content_engine.services.video_renderer import enqueue_render, get_video_status
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
import threading
from pathlib import Path

from ..db import get_db

logger = logging.getLogger("content_engine.services.video_renderer")

# Absolute path to the repo root.
REPO_ROOT = Path(__file__).resolve().parents[4]

# hyperframes binary — resolved via PATH (installed by npm)
HYPERFRAMES_BIN = os.environ.get("HYPERFRAMES_BIN", "hyperframes")

SUPABASE_STORAGE_BUCKET = os.environ.get("VIDEO_STORAGE_BUCKET", "videos")


class VideoRenderError(Exception):
    """Raised on render failures."""


def render_composition_to_path(
    composition_path: str,
    render_props: dict,
    output_path: Path,
    timeout: int = 300,
) -> None:
    """Render a HyperFrames composition to a local MP4 path."""
    comp_dir = REPO_ROOT / composition_path
    if not comp_dir.exists():
        raise VideoRenderError(f"Composition directory not found: {comp_dir}")

    variables_json = json.dumps(render_props)
    cmd = [
        HYPERFRAMES_BIN, "render", str(comp_dir),
        "--output", str(output_path),
        "--variables", variables_json,
        "--format", "mp4",
    ]

    logger.info("Rendering composition %s", comp_dir)
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise VideoRenderError("Render timed out after 5 minutes") from exc
    except FileNotFoundError as exc:
        raise VideoRenderError(f"hyperframes binary not found: {HYPERFRAMES_BIN}") from exc

    if proc.returncode != 0:
        raise VideoRenderError(f"hyperframes exited {proc.returncode}: {proc.stderr[-500:]}")

    if not output_path.exists():
        raise VideoRenderError("hyperframes completed but output file not found")


def upload_rendered_video(
    brand_id: str,
    video_id: str,
    source_path: Path,
) -> tuple[str, str]:
    """Upload a rendered MP4 to Supabase Storage and return (output_url, storage_path)."""
    db = get_db()
    storage_path = f"{brand_id}/{video_id}/output.mp4"

    try:
        with open(source_path, "rb") as f:
            db.storage.from_(SUPABASE_STORAGE_BUCKET).upload(
                storage_path,
                f.read(),
                {"content-type": "video/mp4", "upsert": "true"},
            )
        signed = db.storage.from_(SUPABASE_STORAGE_BUCKET).create_signed_url(
            storage_path, 3600
        )
        output_url = signed.get("signedURL") or signed.get("signedUrl", "")
    except Exception as exc:
        raise VideoRenderError(f"Storage upload failed: {exc}") from exc

    return output_url, storage_path


def enqueue_render(
    brand_id: str,
    template_slug: str,
    render_props: dict,
    title: str | None = None,
) -> str:
    """Create a video record and start a background render. Returns the video UUID."""
    # Resolve template
    tmpl = (
        get_db()
        .from_("video_templates")
        .select("id, slug, composition_path")
        .eq("slug", template_slug)
        .maybe_single()
        .execute()
    )
    if not tmpl.data:
        raise VideoRenderError(f"Template '{template_slug}' not found")

    template_id = tmpl.data["id"]
    composition_path = tmpl.data["composition_path"]

    display_title = title or f"{template_slug.replace('-', ' ').title()} – {render_props.get('week_start', '')}"

    result = (
        get_db()
        .from_("videos")
        .insert({
            "brand_id": brand_id,
            "template_id": template_id,
            "title": display_title.strip(" –"),
            "status": "pending",
            "render_props": render_props,
        })
        .execute()
    )
    if not result.data:
        raise VideoRenderError("Failed to create videos record")

    video_id = result.data[0]["id"]

    t = threading.Thread(
        target=_render_worker,
        args=(video_id, brand_id, composition_path, render_props),
        daemon=True,
    )
    t.start()

    return video_id


def get_video_status(video_id: str, brand_id: str) -> dict:
    result = (
        get_db()
        .from_("videos")
        .select("id, title, status, kind, output_url, storage_path, duration_secs, error, pipeline_state, created_at, updated_at")
        .eq("id", video_id)
        .eq("brand_id", brand_id)
        .maybe_single()
        .execute()
    )
    if not result.data:
        raise VideoRenderError(f"Video {video_id} not found")
    return result.data


def list_videos(brand_id: str, limit: int = 20) -> list[dict]:
    result = (
        get_db()
        .from_("videos")
        .select("id, title, status, kind, output_url, duration_secs, created_at, template_id")
        .eq("brand_id", brand_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []


def _render_worker(video_id: str, brand_id: str, composition_path: str, render_props: dict) -> None:
    """Background thread: render via hyperframes CLI, upload to Supabase Storage."""
    db = get_db()
    db.from_("videos").update({"status": "rendering"}).eq("id", video_id).execute()

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "output.mp4"
        try:
            render_composition_to_path(composition_path, render_props, output_path)
        except VideoRenderError as exc:
            _fail(video_id, str(exc))
            return

        try:
            output_url, storage_path = upload_rendered_video(brand_id, video_id, output_path)
        except VideoRenderError as exc:
            _fail(video_id, str(exc))
            return

        db.from_("videos").update({
            "status": "completed",
            "output_url": output_url,
            "storage_path": storage_path,
        }).eq("id", video_id).execute()

        logger.info("Video %s rendered and uploaded to %s", video_id, storage_path)


def _fail(video_id: str, error: str) -> None:
    logger.error("Video render failed %s: %s", video_id, error)
    get_db().from_("videos").update({
        "status": "failed",
        "error": error[:500],
    }).eq("id", video_id).execute()
