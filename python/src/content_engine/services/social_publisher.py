"""Social publishing service — posts content to LinkedIn and other platforms."""

from __future__ import annotations

import httpx

from ..config import settings
from ..db import get_db


async def publish_to_linkedin(brand_id: str, draft_id: str, access_token: str) -> dict:
    """Publish a draft to LinkedIn using the Community Management API."""
    db = get_db()

    draft = db.table("content_drafts").select("*").eq("id", draft_id).single().execute().data
    if not draft:
        raise ValueError("Draft not found")

    if draft.get("status") not in ("approved", "scheduled"):
        raise ValueError("Draft must be approved or scheduled before publishing")

    body = draft.get("body", "")
    title = draft.get("title", "")
    text = f"{title}\n\n{body}" if title else body

    # LinkedIn UGC Post API
    async with httpx.AsyncClient(timeout=30) as client:
        # Get user profile URN
        me_resp = await client.get(
            "https://api.linkedin.com/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        me_resp.raise_for_status()
        user_sub = me_resp.json().get("sub")
        author_urn = f"urn:li:person:{user_sub}"

        # Create post
        post_resp = await client.post(
            "https://api.linkedin.com/v2/ugcPosts",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0",
            },
            json={
                "author": author_urn,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {"text": text},
                        "shareMediaCategory": "NONE",
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                },
            },
        )
        post_resp.raise_for_status()
        post_data = post_resp.json()
        post_id = post_data.get("id", "")

    published_url = f"https://www.linkedin.com/feed/update/{post_id}" if post_id else ""

    # Update draft status
    db.table("content_drafts").update({
        "status": "published",
        "published_url": published_url,
    }).eq("id", draft_id).execute()

    return {
        "draft_id": draft_id,
        "platform": "linkedin",
        "post_id": post_id,
        "published_url": published_url,
        "status": "published",
    }


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
