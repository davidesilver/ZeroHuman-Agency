"""Postiz Publisher — replaces the mock social_publisher.py

Dual-mode support:
  - self_hosted: calls local Docker Postiz instance
  - cloud:       calls Postiz SaaS / managed instance
  - disabled:    raises clear error (social publishing not available)

All platform OAuth is delegated to Postiz. Our app stores only opaque
integration_id references.
"""
from __future__ import annotations

import logging
from typing import Optional

from ..config import settings
from ..db import get_db
from ..utils.audit_trail import log_publish_event
from .postiz_client import PostizClient

_logger = logging.getLogger("content_engine.postiz_publisher")

# Supported platform mappings (normalize aliases like "x" → "twitter")
_PLATFORM_ALIASES = {
    "x": "twitter",
    "twitter": "twitter",
}


def _normalize_platform(platform: str) -> str:
    return _PLATFORM_ALIASES.get(platform.lower(), platform.lower())


def _is_postiz_enabled() -> bool:
    return settings.postiz_mode in ("self_hosted", "cloud")


async def _get_active_integrations(
    brand_id: str, platforms: list[str],
) -> list[dict]:
    """Resolve Postiz integration IDs for the given platforms.

    Returns list of dicts: [{"platform": "linkedin", "integration_id": "..."}, ...]
    Raises ValueError if any platform is missing an active integration.
    """
    db = get_db()
    normalized = [_normalize_platform(p) for p in platforms]

    rows = (
        db.table("brand_social_integrations")
        .select("platform, postiz_integration_id, postiz_channel_name")
        .eq("brand_id", brand_id)
        .eq("is_active", True)
        .in_("platform", normalized)
        .execute()
        .data
        or []
    )

    found = {r["platform"]: r for r in rows}
    missing = [p for p in normalized if p not in found]
    if missing:
        raise ValueError(
            f"No active Postiz integration for platforms: {', '.join(missing)}. "
            f"Connect them in Postiz UI, then paste integration IDs in Settings → Social Connections."
        )

    return [
        {"platform": p, "integration_id": found[p]["postiz_integration_id"], "channel_name": found[p].get("postiz_channel_name")}
        for p in normalized
    ]


async def publish_now(
    brand_id: str,
    draft_id: str,
    platforms: list[str],
    *,
    media_urls: Optional[list[str]] = None,
) -> dict:
    """Publish a draft immediately to one or more social platforms via Postiz.

    Returns:
        {
            "draft_id": str,
            "platforms": list[str],
            "postiz_post_ids": dict[str, str],  # platform → postiz_id
            "published_url": str | None,
            "status": "published",
        }
    """
    if not _is_postiz_enabled():
        raise RuntimeError(
            f"Social publishing is disabled (POSTIZ_MODE={settings.postiz_mode}). "
            "Set POSTIZ_MODE=self_hosted or cloud and configure POSTIZ_API_URL + POSTIZ_API_KEY."
        )

    db = get_db()
    draft = (
        db.table("content_drafts")
        .select("id, title, body, media_urls, status")
        .eq("id", draft_id)
        .single()
        .execute()
        .data
    )
    if not draft:
        raise ValueError(f"Draft {draft_id} not found")

    if draft.get("status") not in ("approved", "scheduled"):
        raise ValueError("Draft must be approved or scheduled before publishing")

    text = f"{draft.get('title', '')}\n\n{draft.get('body', '')}".strip()

    # Resolve integrations
    integrations = await _get_active_integrations(brand_id, platforms)
    integration_ids = [i["integration_id"] for i in integrations]

    # Attach generated media if available and caller didn't override
    post_media = media_urls or []
    if not post_media and draft.get("media_urls"):
        post_media = list(draft["media_urls"])

    # Call Postiz
    client = PostizClient()
    result = await client.create_post(
        integration_ids=integration_ids,
        content=text,
        media_urls=post_media or None,
    )

    # Postiz may return per-platform post IDs
    postiz_post_ids: dict[str, str] = {}
    if isinstance(result, dict):
        # Try to extract per-platform IDs from Postiz response
        for item in result.get("posts", []):
            plat = item.get("platform", "unknown")
            postiz_post_ids[_normalize_platform(plat)] = item.get("id", "")
        # Fallback: single top-level id
        if not postiz_post_ids and result.get("id"):
            postiz_post_ids["default"] = result["id"]

    published_url = result.get("url") or result.get("link", "")

    # Update draft — metadata column added in migration 029.
    # postiz_post_ids are also persisted via log_publish_event details below (audit_trail),
    # so analytics can still function even if migration 029 hasn't run yet.
    current_meta = draft.get("metadata") or {}
    if isinstance(current_meta, dict):
        current_meta["postiz_post_ids"] = postiz_post_ids
    else:
        current_meta = {"postiz_post_ids": postiz_post_ids}

    from datetime import datetime, timezone
    db.table("content_drafts").update({
        "status": "published",
        "published_at": datetime.now(timezone.utc).isoformat(),
        "published_url": published_url,
        "metadata": current_meta,
    }).eq("id", draft_id).execute()

    await log_publish_event(
        brand_id, draft_id,
        action="postiz_publish",
        platform=",".join(platforms),
        status="success",
        details={"postiz_post_ids": postiz_post_ids, "published_url": published_url},
    )

    return {
        "draft_id": draft_id,
        "platforms": platforms,
        "postiz_post_ids": postiz_post_ids,
        "published_url": published_url,
        "status": "published",
    }


async def schedule_post(
    brand_id: str,
    draft_id: str,
    scheduled_at: str,
    platforms: Optional[list[str]] = None,
) -> dict:
    """Schedule a draft for future publishing via Postiz.

    If platforms are provided, the post is scheduled on Postiz immediately.
    If not, the draft is only marked scheduled locally and will be sent to
    Postiz by the daily scheduler when the time arrives.
    """
    if not _is_postiz_enabled():
        # Allow local-only scheduling even if Postiz disabled
        _logger.warning("Postiz disabled — scheduling locally only. Publish will fail.")

    db = get_db()
    draft = (
        db.table("content_drafts")
        .select("id, title, body, media_urls, status")
        .eq("id", draft_id)
        .single()
        .execute()
        .data
    )
    if not draft:
        raise ValueError(f"Draft {draft_id} not found")

    text = f"{draft.get('title', '')}\n\n{draft.get('body', '')}".strip()

    postiz_post_ids: dict[str, str] = {}

    # If platforms provided and Postiz enabled, schedule on Postiz now
    if platforms and _is_postiz_enabled():
        integrations = await _get_active_integrations(brand_id, platforms)
        integration_ids = [i["integration_id"] for i in integrations]
        post_media = list(draft.get("media_urls") or [])

        client = PostizClient()
        result = await client.create_post(
            integration_ids=integration_ids,
            content=text,
            scheduled_at=scheduled_at,
            media_urls=post_media or None,
        )

        if isinstance(result, dict):
            for item in result.get("posts", []):
                plat = item.get("platform", "unknown")
                postiz_post_ids[_normalize_platform(plat)] = item.get("id", "")
            if not postiz_post_ids and result.get("id"):
                postiz_post_ids["default"] = result["id"]

    # Update draft
    current_meta = draft.get("metadata") or {}
    if isinstance(current_meta, dict):
        current_meta["postiz_post_ids"] = postiz_post_ids
        current_meta["scheduled_platforms"] = platforms or []
    else:
        current_meta = {
            "postiz_post_ids": postiz_post_ids,
            "scheduled_platforms": platforms or [],
        }

    db.table("content_drafts").update({
        "status": "scheduled",
        "scheduled_at": scheduled_at,
        "metadata": current_meta,
    }).eq("id", draft_id).execute()

    # Calendar event — schema uses scheduled_date/scheduled_time (not scheduled_at).
    # event_status enum: 'planned' | 'confirmed' | 'published'  (no 'scheduled').
    # event_type enum: 'newsletter' | 'social' | 'blog_video' | 'sponsorship'.
    from datetime import datetime as _dt
    try:
        _parsed = _dt.fromisoformat(scheduled_at.replace("Z", "+00:00"))
        _sched_date = _parsed.date().isoformat()
        _sched_time = _parsed.time().isoformat()
    except (ValueError, AttributeError):
        _sched_date = scheduled_at[:10]  # fallback: first 10 chars
        _sched_time = None

    db.table("calendar_events").insert({
        "brand_id": brand_id,
        "title": draft.get("title", "Scheduled Post"),
        "event_type": "social",
        "scheduled_date": _sched_date,
        "scheduled_time": _sched_time,
        "draft_id": draft_id,
        "status": "planned",
    }).execute()

    await log_publish_event(
        brand_id, draft_id,
        action="schedule_post",
        platform=",".join(platforms or []),
        status="success",
        details={"scheduled_at": scheduled_at, "postiz_post_ids": postiz_post_ids},
    )

    return {
        "draft_id": draft_id,
        "status": "scheduled",
        "scheduled_at": scheduled_at,
        "postiz_post_ids": postiz_post_ids,
    }


async def publish_scheduled_via_postiz(brand_id: str, draft: dict) -> dict:
    """Called by scheduler to publish a draft that has reached its scheduled time.

    If the draft was already scheduled on Postiz (has postiz_post_ids), this is
    a no-op because Postiz handles the actual publish. Otherwise, we publish now.
    """
    if not _is_postiz_enabled():
        raise RuntimeError("Postiz not enabled — cannot publish scheduled posts")

    metadata = draft.get("metadata") or {}
    existing_postiz_ids = metadata.get("postiz_post_ids", {})

    # If already scheduled on Postiz, it's Postiz's job to publish at the right time
    if existing_postiz_ids:
        _logger.info("Draft %s already scheduled on Postiz — skipping", draft["id"])
        return {
            "draft_id": draft["id"],
            "status": "scheduled_on_platform",
            "postiz_post_ids": existing_postiz_ids,
        }

    # Otherwise publish now
    scheduled_platforms = metadata.get("scheduled_platforms", [])
    if not scheduled_platforms:
        # Fallback: use draft.platform as single target
        scheduled_platforms = [draft.get("platform", "linkedin")]

    return await publish_now(
        brand_id=brand_id,
        draft_id=draft["id"],
        platforms=scheduled_platforms,
    )
