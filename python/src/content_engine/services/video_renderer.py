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
from typing import Optional

from ..db import get_db

logger = logging.getLogger("content_engine.services.video_renderer")

# Absolute path to compositions/ directory (repo root)
_REPO_ROOT = Path(__file__).resolve().parents[5]
COMPOSITIONS_DIR = _REPO_ROOT / "compositions"

# hyperframes binary — resolved via PATH (installed by npm)
HYPERFRAMES_BIN = os.environ.get("HYPERFRAMES_BIN", "hyperframes")

SUPABASE_STORAGE_BUCKET = os.environ.get("VIDEO_STORAGE_BUCKET", "videos")


class VideoRenderError(Exception):
    """Raised on render failures."""


def enqueue_render(
    brand_id: str,
    template_slug: str,
    render_props: dict,
    title: Optional[str] = None,
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
        .select("id, title, status, output_url, duration_secs, error, created_at, updated_at")
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
        .select("id, title, status, output_url, duration_secs, created_at, template_id")
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

    comp_dir = COMPOSITIONS_DIR / composition_path
    if not comp_dir.exists():
        _fail(video_id, f"Composition directory not found: {comp_dir}")
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "output.mp4"
        variables_json = json.dumps(render_props)

        cmd = [
            HYPERFRAMES_BIN, "render", str(comp_dir),
            "--output", str(output_path),
            "--variables", variables_json,
            "--format", "mp4",
        ]

        logger.info("Rendering video %s: %s", video_id, " ".join(cmd[:4]))
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 min max
            )
        except subprocess.TimeoutExpired:
            _fail(video_id, "Render timed out after 5 minutes")
            return
        except FileNotFoundError:
            _fail(video_id, f"hyperframes binary not found: {HYPERFRAMES_BIN}")
            return

        if proc.returncode != 0:
            _fail(video_id, f"hyperframes exited {proc.returncode}: {proc.stderr[-500:]}")
            return

        if not output_path.exists():
            _fail(video_id, "hyperframes completed but output file not found")
            return

        # Upload to Supabase Storage
        storage_path = f"{brand_id}/{video_id}/output.mp4"
        try:
            with open(output_path, "rb") as f:
                db.storage.from_(SUPABASE_STORAGE_BUCKET).upload(
                    storage_path,
                    f.read(),
                    {"content-type": "video/mp4", "upsert": "true"},
                )
            # Generate a signed URL (1 hour default; callers can re-sign)
            signed = db.storage.from_(SUPABASE_STORAGE_BUCKET).create_signed_url(
                storage_path, 3600
            )
            output_url = signed.get("signedURL") or signed.get("signedUrl", "")
        except Exception as exc:
            _fail(video_id, f"Storage upload failed: {exc}")
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
