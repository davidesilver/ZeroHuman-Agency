"""Automated shorts pipeline orchestration."""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Any

from ..db import get_db
from ..utils.brand_assets import get_brand_logo_url, get_brand_palette
from ..utils.llm_client import call_llm_with_json
from .media_sourcing import search_b_roll_videos
from .subtitle_generator import generate_subtitle_blocks
from .tts_provider import TTSResult, synthesize_tts
from .video_renderer import (
    VideoRenderError,
    render_composition_to_path,
    upload_rendered_video,
)

logger = logging.getLogger("content_engine.services.shorts_generator")

SHORTS_TEMPLATE_SLUG = "automated-shorts"


class ShortsPipelineError(Exception):
    """Raised when the shorts pipeline cannot complete."""


def _video_row(video_id: str, brand_id: str) -> dict[str, Any]:
    result = (
        get_db()
        .from_("videos")
        .select("id, brand_id, title, status, kind, render_props, pipeline_state, template_id, output_url, storage_path, duration_secs, error")
        .eq("id", video_id)
        .eq("brand_id", brand_id)
        .maybe_single()
        .execute()
    )
    if not result.data:
        raise ShortsPipelineError(f"Video {video_id} not found")
    return result.data


def _template_row() -> dict[str, Any]:
    result = (
        get_db()
        .from_("video_templates")
        .select("id, slug, composition_path")
        .eq("slug", SHORTS_TEMPLATE_SLUG)
        .maybe_single()
        .execute()
    )
    if not result.data:
        raise ShortsPipelineError(f"Template {SHORTS_TEMPLATE_SLUG!r} not found")
    return result.data


def _initial_state(
    *,
    topic: str,
    voice_id: str | None,
    pexels_keywords: list[str] | None,
    title: str | None,
) -> dict[str, Any]:
    return {
        "version": 1,
        "status": "queued",
        "current_step": "init",
        "inputs": {
            "topic": topic,
            "voice_id": voice_id,
            "pexels_keywords": pexels_keywords or [],
            "title": title,
        },
        "artifacts": {},
        "error": None,
    }


def _merge_state(existing: dict[str, Any] | None, initial: dict[str, Any]) -> dict[str, Any]:
    state = dict(existing or {})
    state.setdefault("version", initial["version"])
    state.setdefault("status", initial["status"])
    state.setdefault("current_step", initial["current_step"])
    state.setdefault("inputs", initial["inputs"])
    state.setdefault("artifacts", {})
    state.setdefault("error", None)
    if "inputs" in initial and not state.get("inputs"):
        state["inputs"] = initial["inputs"]
    state["artifacts"] = dict(state.get("artifacts") or {})
    return state


def _save_state(
    video_id: str,
    state: dict[str, Any],
    *,
    status: str | None = None,
    error: str | None = None,
    output_url: str | None = None,
    storage_path: str | None = None,
    duration_secs: float | None = None,
) -> None:
    payload: dict[str, Any] = {"pipeline_state": state}
    if status is not None:
        payload["status"] = status
    if error is not None:
        payload["error"] = error[:500]
    if output_url is not None:
        payload["output_url"] = output_url
    if storage_path is not None:
        payload["storage_path"] = storage_path
    if duration_secs is not None:
        payload["duration_secs"] = duration_secs
    get_db().from_("videos").update(payload).eq("id", video_id).execute()


async def _generate_script(
    topic: str,
    brand_id: str,
    brand_name: str,
    accent_color: str,
) -> dict[str, Any]:
    prompt = f"""
Create a vertical short script for the topic below.
Return JSON with:
- title: short hook line
- narration: voiceover copy, 25-40 seconds max
- b_roll_keywords: array of 3-6 concise search phrases for B-roll

Rules:
- Keep it in the same language as the topic.
- Make it concrete and useful.
- Avoid markdown, bullets, and self-referential filler.

Topic: {topic}
Brand: {brand_name}
Brand accent color: {accent_color}
""".strip()

    try:
        data = await call_llm_with_json(
            prompt=prompt,
            brand_id=brand_id,
            context="shorts_script",
            action="generate_shorts_script",
            system_prompt="You write concise social video scripts in JSON only.",
            task_type="creative",
            temperature=0.6,
            allow_partial=True,
        )
    except Exception as exc:
        logger.warning("LLM script generation failed, using deterministic fallback: %s", exc)
        data = {}

    title = str(data.get("title") or topic).strip()
    narration = str(data.get("narration") or "").strip()
    keywords = data.get("b_roll_keywords")
    if not isinstance(keywords, list):
        keywords = []
    keywords = [str(item).strip() for item in keywords if str(item).strip()]
    if not keywords:
        tokens = [part.strip(".,:;!?()[]{}") for part in topic.split()]
        keywords = [token for token in tokens if len(token) > 3][:5] or [topic]

    if not narration:
        narration = (
            f"{title}. {topic}. "
            "This short explains the core idea in a concise way and ends with a clear takeaway."
        )

    return {
        "title": title,
        "narration": narration,
        "b_roll_keywords": keywords,
    }


def _mux_audio_and_video(
    silent_video_path: Path,
    audio_path: str,
    output_path: Path,
) -> None:
    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        raise ShortsPipelineError("ffmpeg is not installed on the host/container")

    cmd = [
        ffmpeg_bin,
        "-y",
        "-i",
        str(silent_video_path),
        "-i",
        audio_path,
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        str(output_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        raise ShortsPipelineError(f"ffmpeg exited {proc.returncode}: {proc.stderr[-500:]}")
    if not output_path.exists():
        raise ShortsPipelineError("ffmpeg completed but final video file is missing")


def _brand_theme(brand_id: str) -> dict[str, str]:
    db = get_db()
    result = db.table("brands").select("name, primary_color, logo_url").eq("id", brand_id).maybe_single().execute()
    brand = result.data or {}
    palette = get_brand_palette(brand_id)
    brand_name = str(brand.get("name") or "Brand")
    accent_color = str(brand.get("primary_color") or (palette[0] if palette else "#6366f1"))
    logo_url = str(brand.get("logo_url") or get_brand_logo_url(brand_id) or "")
    return {
        "brand_name": brand_name,
        "accent_color": accent_color,
        "logo_url": logo_url,
    }


async def _run_pipeline(
    video_id: str,
    brand_id: str,
    template_slug: str,
    composition_path: str,
    topic: str,
    voice_id: str | None,
    pexels_keywords: list[str] | None,
    title: str | None,
) -> dict[str, Any]:
    logger.info("Starting automated shorts pipeline for video %s (template=%s)", video_id, template_slug)
    row = _video_row(video_id, brand_id)
    state = _merge_state(row.get("pipeline_state"), _initial_state(
        topic=topic,
        voice_id=voice_id,
        pexels_keywords=pexels_keywords,
        title=title,
    ))
    state["status"] = "running"
    state["current_step"] = "script"
    _save_state(video_id, state, status="rendering")

    theme = _brand_theme(brand_id)

    artifacts = state["artifacts"]

    if "script" not in artifacts:
        script = await _generate_script(topic, brand_id, theme["brand_name"], theme["accent_color"])
        artifacts["script"] = script
        _save_state(video_id, state, status="rendering")
    else:
        script = artifacts["script"]

    state["current_step"] = "tts"
    _save_state(video_id, state, status="rendering")

    if "audio" not in artifacts:
        tts_result: TTSResult = await synthesize_tts(
            str(script["narration"]),
            brand_id,
            provider="auto",
            voice_id=voice_id,
        )
        audio_duration = tts_result.duration_seconds
        artifacts["audio"] = {
            "path": tts_result.audio_path,
            "provider_used": tts_result.provider_used,
            "mime_type": tts_result.mime_type,
            "duration_seconds": audio_duration,
            "voice_id": tts_result.voice_id,
        }
    else:
        tts_result = TTSResult(
            audio_path=str(artifacts["audio"]["path"]),
            provider_used=str(artifacts["audio"].get("provider_used") or "auto"),
            mime_type=str(artifacts["audio"].get("mime_type") or "audio/mpeg"),
            duration_seconds=artifacts["audio"].get("duration_seconds"),
            voice_id=artifacts["audio"].get("voice_id"),
        )
        audio_duration = tts_result.duration_seconds
    _save_state(video_id, state, status="rendering")

    state["current_step"] = "subtitles"
    _save_state(video_id, state, status="rendering")

    if "subtitles" not in artifacts:
        subtitles = await generate_subtitle_blocks(
            tts_result.audio_path,
            fallback_text=str(script["narration"]),
            fallback_duration_seconds=audio_duration,
        )
        artifacts["subtitles"] = subtitles
    else:
        subtitles = artifacts["subtitles"]
    _save_state(video_id, state, status="rendering")

    state["current_step"] = "b_roll"
    _save_state(video_id, state, status="rendering")

    if "b_roll_urls" not in artifacts:
        keywords = pexels_keywords or script.get("b_roll_keywords") or [topic]
        b_roll_urls = await search_b_roll_videos(keywords, brand_id, limit=5)
        artifacts["b_roll_urls"] = b_roll_urls
    else:
        b_roll_urls = list(artifacts["b_roll_urls"])
    _save_state(video_id, state, status="rendering")

    state["current_step"] = "render_props"
    _save_state(video_id, state, status="rendering")

    duration_seconds = float(audio_duration or (subtitles[-1]["end"] if subtitles else 30.0))
    render_props = {
        "brand_name": theme["brand_name"],
        "accent_color": theme["accent_color"],
        "logo_url": theme["logo_url"],
        "title": str(title or script["title"]),
        "topic": topic,
        "narration": str(script["narration"]),
        "subtitle_blocks_json": json.dumps(subtitles, ensure_ascii=False),
        "b_roll_urls_json": json.dumps(b_roll_urls, ensure_ascii=False),
        "duration_seconds": round(duration_seconds, 2),
        "watermark_text": theme["brand_name"],
        "progress_label": "Shorts",
    }
    artifacts["render_props"] = render_props
    _save_state(video_id, state, status="rendering")

    state["current_step"] = "render"
    _save_state(video_id, state, status="rendering")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        silent_path = tmpdir_path / "shorts-silent.mp4"
        final_path = tmpdir_path / "shorts-final.mp4"

        try:
            render_composition_to_path(
                composition_path=composition_path,
                render_props=render_props,
                output_path=silent_path,
                timeout=600,
            )
        except VideoRenderError as exc:
            raise ShortsPipelineError(str(exc)) from exc

        state["current_step"] = "mux"
        _save_state(video_id, state, status="rendering")

        try:
            _mux_audio_and_video(silent_path, tts_result.audio_path, final_path)
        except ShortsPipelineError:
            raise
        except Exception as exc:  # pragma: no cover - defensive
            raise ShortsPipelineError(str(exc)) from exc

        output_url, storage_path = upload_rendered_video(brand_id, video_id, final_path)

    state["current_step"] = "complete"
    state["status"] = "completed"
    state["artifacts"] = artifacts
    _save_state(
        video_id,
        state,
        status="completed",
        output_url=output_url,
        storage_path=storage_path,
        duration_secs=duration_seconds,
    )
    return {
        "video_id": video_id,
        "status": "completed",
        "output_url": output_url,
        "storage_path": storage_path,
        "duration_secs": duration_seconds,
    }


def _worker(
    video_id: str,
    brand_id: str,
    template_slug: str,
    composition_path: str,
    topic: str,
    voice_id: str | None,
    pexels_keywords: list[str] | None,
    title: str | None,
) -> None:
    try:
        asyncio.run(
            _run_pipeline(
                video_id=video_id,
                brand_id=brand_id,
                template_slug=template_slug,
                composition_path=composition_path,
                topic=topic,
                voice_id=voice_id,
                pexels_keywords=pexels_keywords,
                title=title,
            )
        )
    except Exception as exc:
        logger.exception("Shorts pipeline failed for video %s", video_id)
        row = _video_row(video_id, brand_id)
        state = _merge_state(row.get("pipeline_state"), _initial_state(
            topic=topic,
            voice_id=voice_id,
            pexels_keywords=pexels_keywords,
            title=title,
        ))
        state["status"] = "failed"
        state["current_step"] = state.get("current_step") or "unknown"
        state["error"] = str(exc)
        _save_state(video_id, state, status="failed", error=str(exc))


def enqueue_shorts_generation(
    brand_id: str,
    topic: str,
    voice_id: str | None = None,
    pexels_keywords: list[str] | None = None,
    title: str | None = None,
) -> str:
    """Create a shorts video record and start the background pipeline."""
    template = _template_row()
    render_props = {
        "topic": topic,
        "voice_id": voice_id,
        "pexels_keywords": pexels_keywords or [],
    }
    initial_state = _initial_state(
        topic=topic,
        voice_id=voice_id,
        pexels_keywords=pexels_keywords,
        title=title,
    )
    result = (
        get_db()
        .from_("videos")
        .insert({
            "brand_id": brand_id,
            "template_id": template["id"],
            "title": (title or topic).strip(),
            "status": "pending",
            "kind": "automated-shorts",
            "render_props": render_props,
            "pipeline_state": initial_state,
        })
        .execute()
    )
    if not result.data:
        raise ShortsPipelineError("Failed to create shorts video record")

    video_id = result.data[0]["id"]

    thread = threading.Thread(
        target=_worker,
        args=(
            video_id,
            brand_id,
            SHORTS_TEMPLATE_SLUG,
            template["composition_path"],
            topic,
            voice_id,
            pexels_keywords,
            title,
        ),
        daemon=True,
    )
    thread.start()

    return video_id


def get_shorts_video_status(video_id: str, brand_id: str) -> dict[str, Any]:
    result = (
        get_db()
        .from_("videos")
        .select("id, title, status, kind, output_url, storage_path, duration_secs, error, pipeline_state, render_props, created_at, updated_at")
        .eq("id", video_id)
        .eq("brand_id", brand_id)
        .maybe_single()
        .execute()
    )
    if not result.data:
        raise ShortsPipelineError(f"Video {video_id} not found")
    return result.data
