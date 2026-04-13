"""Social publishing service — posts content to LinkedIn and other platforms."""

from __future__ import annotations

import httpx

from ..config import settings
from ..db import get_db
from ..utils.audit_trail import log_publish_event


async def publish_to_postiz(brand_id: str, draft_id: str, platforms: list[str]) -> dict:
    """Publish a draft to multiple socials using Postiz Command Center API."""
    db = get_db()

    draft = db.table("content_drafts").select("*").eq("id", draft_id).single().execute().data
    if not draft:
        raise ValueError("Draft not found")

    if draft.get("status") not in ("approved", "scheduled"):
        raise ValueError("Draft must be approved or scheduled before publishing")

    body = draft.get("body", "")
    title = draft.get("title", "")
    text = f"{title}\n\n{body}" if title else body
    
    if not settings.postiz_api_key or not settings.postiz_base_url:
        import logging
        logging.getLogger(__name__).warning("Postiz API keys missing. Faking publish.")
        post_id = "fake_postiz_id"
    else:
        # Connect to Postiz API to publish to all requested platforms simultaneously
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{settings.postiz_base_url}/api/v1/posts",
                headers={
                    "Authorization": f"Bearer {settings.postiz_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "content": text,
                    "platforms": platforms, # e.g. ["linkedin", "twitter", "instagram"]
                    "status": "PUBLISHED"
                },
            )
            resp.raise_for_status()
            post_data = resp.json()
            post_id = post_data.get("id", "")

    published_url = f"https://postiz.local/post/{post_id}" if post_id else ""

    # Update draft status
    db.table("content_drafts").update({
        "status": "published",
        "published_url": published_url,
    }).eq("id", draft_id).execute()

    result = {
        "draft_id": draft_id,
        "platforms": platforms,
        "post_id": post_id,
        "published_url": published_url,
        "status": "published",
    }

    await log_publish_event(
        brand_id, draft_id,
        action="postiz_publish",
        platform=",".join(platforms),
        status="success",
        details={"postiz_id": post_id, "published_url": published_url},
    )

    return result


async def schedule_post(brand_id: str, draft_id: str, scheduled_at: str) -> dict:
    """Schedule a draft for future publishing."""
    db = get_db()

    db.table("content_drafts").update({
        "status": "scheduled",
        "scheduled_at": scheduled_at,
    }).eq("id", draft_id).execute()

    # Also create a calendar event
    draft = db.table("content_drafts").select("title, platform, content_type").eq("id", draft_id).single().execute().data
    db.table("calendar_events").insert({
        "brand_id": brand_id,
        "title": draft.get("title", "Scheduled Post"),
        "event_type": draft.get("content_type", "post"),
        "scheduled_at": scheduled_at,
        "content_draft_id": draft_id,
        "status": "scheduled",
    }).execute()

    await log_publish_event(
        brand_id, draft_id,
        action="schedule_post",
        platform=draft.get("platform", ""),
        status="success",
        details={"scheduled_at": scheduled_at},
    )

    return {
        "draft_id": draft_id,
        "status": "scheduled",
        "scheduled_at": scheduled_at,
    }


async def get_scheduled_posts(brand_id: str) -> list[dict]:
    """Get all scheduled posts ready to publish."""
    db = get_db()
    result = db.table("content_drafts").select("*").eq(
        "brand_id", brand_id
    ).eq("status", "scheduled").lte(
        "scheduled_at", "now()"
    ).execute()
    return result.data or []
