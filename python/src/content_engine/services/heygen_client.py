"""Heygen talking-head video generation client.

Auth: per-brand API key from brand_integrations (provider='heygen', key_name='api_key').
Quota: per-brand monthly minutes cap from feature_flags ('heygen_minutes_per_month', default 30).
       Usage tracked in heygen_usage table.

Heygen V2 API endpoints used:
  POST /v2/video/generate          → submit render
  GET  /v1/video_status.get?video_id=  → poll status
  GET  /v2/avatars                 → list avatars
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import httpx

from ..db import get_db
from ..services.brand_secrets import get_brand_secret

logger = logging.getLogger("content_engine.services.heygen")

HEYGEN_BASE = "https://api.heygen.com"
DEFAULT_QUOTA_MINUTES = 30
ALERT_THRESHOLD = 0.8  # alert at 80% usage


class HeygenError(Exception):
    """Heygen API or quota error."""


def _api_key(brand_id: str) -> str:
    key = get_brand_secret(brand_id, "heygen", "api_key")
    if not key:
        raise HeygenError(
            "Heygen API key not configured. "
            "Set it in Settings → Brand → Integrations → Heygen."
        )
    return key


def _quota_minutes(brand_id: str) -> int:
    try:
        result = (
            get_db()
            .from_("feature_flags")
            .select("value")
            .eq("brand_id", brand_id)
            .eq("key", "heygen_minutes_per_month")
            .maybe_single()
            .execute()
        )
        if result.data and result.data.get("value") is not None:
            return int(result.data["value"])
    except Exception:
        pass
    return DEFAULT_QUOTA_MINUTES


def _current_usage(brand_id: str) -> float:
    year_month = datetime.now(UTC).strftime("%Y-%m")
    result = (
        get_db()
        .from_("heygen_usage")
        .select("minutes_used")
        .eq("brand_id", brand_id)
        .eq("year_month", year_month)
        .maybe_single()
        .execute()
    )
    if result.data:
        return float(result.data["minutes_used"])
    return 0.0


def _add_usage(brand_id: str, minutes: float) -> None:
    year_month = datetime.now(UTC).strftime("%Y-%m")
    try:
        get_db().from_("heygen_usage").upsert({
            "brand_id": brand_id,
            "year_month": year_month,
            "minutes_used": minutes,
        }, on_conflict="brand_id,year_month").execute()
    except Exception:
        # Try increment approach if upsert with arithmetic isn't supported
        current = _current_usage(brand_id)
        get_db().from_("heygen_usage").upsert({
            "brand_id": brand_id,
            "year_month": year_month,
            "minutes_used": current + minutes,
        }, on_conflict="brand_id,year_month").execute()


def _check_quota(brand_id: str, estimated_minutes: float) -> None:
    quota = _quota_minutes(brand_id)
    used = _current_usage(brand_id)
    if used + estimated_minutes > quota:
        raise HeygenError(
            f"Heygen quota exceeded: {used:.1f}/{quota} minutes used this month."
        )
    if (used + estimated_minutes) / quota >= ALERT_THRESHOLD:
        logger.warning(
            "Heygen quota alert for brand %s: %.1f%% used (%s/%s min)",
            brand_id,
            (used + estimated_minutes) / quota * 100,
            used,
            quota,
        )


def list_avatars(brand_id: str) -> list[dict]:
    """List available Heygen avatars for the brand's account."""
    api_key = _api_key(brand_id)
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(
            f"{HEYGEN_BASE}/v2/avatars",
            headers={"X-Api-Key": api_key},
        )
        resp.raise_for_status()
    data = resp.json()
    return data.get("data", {}).get("avatars", [])


def generate_talking_head(
    brand_id: str,
    script: str,
    avatar_id: str,
    voice_id: str | None = None,
    title: str | None = None,
) -> str:
    """Submit a Heygen talking-head video render. Returns the local videos.id UUID.

    Estimated duration: 1 minute per ~150 words (conservative).
    """
    api_key = _api_key(brand_id)

    word_count = len(script.split())
    estimated_minutes = max(1.0, word_count / 150)
    _check_quota(brand_id, estimated_minutes)

    payload: dict = {
        "video_inputs": [
            {
                "character": {
                    "type": "avatar",
                    "avatar_id": avatar_id,
                    "avatar_style": "normal",
                },
                "voice": {
                    "type": "text",
                    "input_text": script,
                },
            }
        ],
        "dimension": {"width": 1080, "height": 1920},
        "aspect_ratio": "9:16",
    }
    if voice_id:
        payload["video_inputs"][0]["voice"]["voice_id"] = voice_id

    with httpx.Client(timeout=60.0) as client:
        resp = client.post(
            f"{HEYGEN_BASE}/v2/video/generate",
            headers={"X-Api-Key": api_key, "Content-Type": "application/json"},
            json=payload,
        )
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise HeygenError(f"Heygen API error {exc.response.status_code}: {exc.response.text[:300]}") from exc

    heygen_video_id = resp.json().get("data", {}).get("video_id")
    if not heygen_video_id:
        raise HeygenError(f"Heygen did not return a video_id: {resp.text[:300]}")

    # Create local videos record
    insert_res = get_db().from_("videos").insert({
        "brand_id": brand_id,
        "title": (title or "Talking Head").strip(),
        "status": "rendering",
        "kind": "heygen",
        "heygen_video_id": heygen_video_id,
        "render_props": {
            "avatar_id": avatar_id,
            "script_words": word_count,
            "voice_id": voice_id,
        },
    }).execute()

    if not insert_res.data:
        raise HeygenError("Failed to create videos record for Heygen job")

    video_id = insert_res.data[0]["id"]

    # Record optimistic quota usage
    _add_usage(brand_id, estimated_minutes)

    logger.info("Heygen job %s submitted as video %s", heygen_video_id, video_id)
    return video_id


def poll_heygen_status(brand_id: str, video_id: str) -> dict:
    """Poll Heygen for status of a talking-head video and update the DB record.

    Returns the current videos row.
    """
    row_res = (
        get_db()
        .from_("videos")
        .select("id, status, heygen_video_id")
        .eq("id", video_id)
        .eq("brand_id", brand_id)
        .maybe_single()
        .execute()
    )
    if not row_res.data:
        raise HeygenError(f"Video {video_id} not found")

    row = row_res.data
    heygen_video_id = row.get("heygen_video_id")

    if row["status"] in ("completed", "failed") or not heygen_video_id:
        return row

    api_key = _api_key(brand_id)
    with httpx.Client(timeout=20.0) as client:
        resp = client.get(
            f"{HEYGEN_BASE}/v1/video_status.get",
            params={"video_id": heygen_video_id},
            headers={"X-Api-Key": api_key},
        )
        resp.raise_for_status()

    data = resp.json().get("data", {})
    heygen_status = data.get("status", "")

    update: dict = {}
    if heygen_status == "completed":
        update = {
            "status": "completed",
            "output_url": data.get("video_url", ""),
            "duration_secs": data.get("duration"),
        }
    elif heygen_status in ("failed", "error"):
        update = {
            "status": "failed",
            "error": data.get("error", "Heygen render failed"),
        }

    if update:
        get_db().from_("videos").update(update).eq("id", video_id).execute()

    return {**row, **update}
