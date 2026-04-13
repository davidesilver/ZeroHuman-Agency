"""Social publishing service — posts content to LinkedIn and other platforms.

C-03: OAuth access_tokens are NEVER received from the client request body.
      Tokens are stored in brands.social_accounts (JSONB) and read from the DB
      server-side. The frontend only sends brand_id (via JWT) and draft_id.
"""

from __future__ import annotations

import logging

import httpx

from ..config import settings
from ..db import get_db
from ..utils.audit_trail import log_publish_event

_logger = logging.getLogger("content_engine.social")


def get_social_token(brand_id: str, platform: str) -> str | None:
    """C-03: Read OAuth token for a platform from brands.social_accounts in DB.

    Tokens are stored server-side in the DB and never sent over the wire
    from the frontend. The JSONB structure is:
      { "linkedin": {"access_token": "...", "expires_at": "..."}, ... }

    Returns None if no token is configured for the given platform.
    """
    db = get_db()
    result = (
        db.table("brands")
        .select("social_accounts")
        .eq("id", brand_id)
        .single()
        .execute()
    )
    if not result.data:
        return None
    accounts: dict = result.data.get("social_accounts") or {}
    platform_data = accounts.get(platform, {})
    return platform_data.get("access_token")


async def publish_to_postiz(brand_id: str, draft_id: str, platforms: list[str]) -> dict:
    """Publish a draft to multiple socials using Postiz Command Center API.

    C-03: Platforms list comes from the request, but NO access_token is accepted
    from the client. If direct platform publishing is ever needed, tokens are
    read from brands.social_accounts via get_social_token().
    """
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
        _logger.warning("Postiz API keys missing — simulating publish for dev.")
        post_id = "fake_postiz_id"
    else:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{settings.postiz_base_url}/api/v1/posts",
                headers={
                    "Authorization": f"Bearer {settings.postiz_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "content": text,
                    "platforms": platforms,
                    "status": "PUBLISHED",
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
