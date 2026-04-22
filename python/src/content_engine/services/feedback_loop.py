"""Analytics feedback loop — adjusts scoring based on content performance."""

from __future__ import annotations

from ..db import get_db


async def record_social_metrics(
    draft_id: str,
    platform: str,
    impressions: int = 0,
    clicks: int = 0,
    likes: int = 0,
    shares: int = 0,
    comments: int = 0,
    saves: int = 0,
) -> dict:
    """Record social media performance metrics for a published draft."""
    db = get_db()

    data = {
        "draft_id": draft_id,
        "platform": platform,
        "impressions": impressions,
        "clicks": clicks,
        "likes": likes,
        "shares": shares,
        "comments": comments,
        "saves": saves,
    }

    result = db.table("social_metrics").upsert(
        data,
        on_conflict="draft_id,platform",
    ).execute()
    return result.data[0] if result.data else data


async def compute_engagement_score(draft_id: str) -> float:
    """Compute an engagement score (0-10) from social metrics."""
    db = get_db()

    metrics = db.table("social_metrics").select("*").eq(
        "draft_id", draft_id
    ).execute().data

    if not metrics:
        return 5.0  # neutral default

    total_impressions = sum(m.get("impressions", 0) for m in metrics)
    total_engagement = sum(
        m.get("likes", 0) + m.get("comments", 0) * 3 + m.get("shares", 0) * 5 + m.get("saves", 0) * 2
        for m in metrics
    )

    if total_impressions == 0:
        return 5.0

    # Engagement rate: weighted actions / impressions
    engagement_rate = total_engagement / total_impressions

    # Map to 0-10 scale (1% = 5.0, 3% = 7.5, 5%+ = 10.0)
    score = min(10.0, 5.0 + (engagement_rate * 100))
    return round(score, 2)


async def update_feedback_bonus(brand_id: str) -> dict:
    """Update feedback_bonus scores for research items based on content performance.

    This creates the feedback loop: high-performing content boosts the score
    of its source research item, influencing future scoring.
    """
    db = get_db()

    # Get published drafts with metrics
    drafts = db.table("content_drafts").select(
        "id, research_item_id"
    ).eq("brand_id", brand_id).eq("status", "published").not_.is_(
        "research_item_id", "null"
    ).execute().data

    updated = 0
    for draft in (drafts or []):
        research_item_id = draft.get("research_item_id")
        if not research_item_id:
            continue

        engagement_score = await compute_engagement_score(draft["id"])

        # Update the feedback_bonus in scores table
        scores = db.table("scores").select("id, feedback_bonus").eq(
            "research_item_id", research_item_id
        ).execute().data

        if scores:
            # Blend existing bonus with new engagement data (weighted average)
            current_bonus = scores[0].get("feedback_bonus", 5.0)
            new_bonus = round(current_bonus * 0.6 + engagement_score * 0.4, 2)
            db.table("scores").update({"feedback_bonus": new_bonus}).eq(
                "id", scores[0]["id"]
            ).execute()
            updated += 1

    # Record feedback entries
    db.table("feedback").insert({
        "brand_id": brand_id,
        "feedback_type": "comment",
        "value": f"Feedback loop updated {updated} scores",
        "source": "analytics",
    }).execute()

    return {
        "updated_scores": updated,
        "total_drafts_analyzed": len(drafts or []),
    }
