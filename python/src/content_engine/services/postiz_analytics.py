"""Postiz Analytics Puller — fetch engagement metrics and compute dynamic feedback_bonus."""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Optional

import httpx

from ..config import settings
from ..db import get_db


async def fetch_post_analytics(postiz_id: str) -> Optional[dict]:
    """
    Fetch analytics for a single post from Postiz API.

    Returns:
        {
            "platform": str,
            "impressions": int,
            "likes": int,
            "shares": int,
            "comments": int,
            "saves": int,
        } or None if error
    """
    if not settings.postiz_api_key or not settings.postiz_base_url:
        return None

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{settings.postiz_base_url}/public/v1/analytics/post/{postiz_id}",
                headers={"Authorization": f"Bearer {settings.postiz_api_key}"}
            )

        if resp.status_code != 200:
            return None

        data = resp.json()
        return {
            "platform": data.get("platform", "unknown"),
            "impressions": data.get("impressions", 0),
            "likes": data.get("likes", 0),
            "shares": data.get("shares", 0),
            "comments": data.get("comments", 0),
            "saves": data.get("saves", 0),
        }
    except Exception:
        return None


async def pull_daily_metrics(brand_id: str, days_back: int = 7) -> dict:
    """
    Pull daily metrics for all published posts from the last N days.

    Args:
        brand_id: Brand ID to pull metrics for
        days_back: Number of days to look back (default 7)

    Returns:
        {
            "posts_processed": int,
            "metrics_fetched": int,
            "errors": list[str]
        }
    """
    db = get_db()
    errors = []
    processed = 0
    metrics_fetched = 0

    # Get published drafts with real postiz_id from last N days
    cutoff = datetime.utcnow() - timedelta(days=days_back)
    drafts_resp = db.table("content_drafts")\
        .select("id, metadata, published_at")\
        .eq("brand_id", brand_id)\
        .eq("status", "published")\
        .gte("published_at", cutoff.isoformat())\
        .not_.is_("research_item_id", "null")\
        .execute()

    for draft in drafts_resp.data or []:
        postiz_id = (draft.get("metadata") or {}).get("postiz_id")
        if not postiz_id or postiz_id == "fake_postiz_id":
            continue

        metrics = await fetch_post_analytics(postiz_id)
        if metrics:
            await record_social_metrics(
                draft_id=draft["id"],
                platform=metrics["platform"],
                impressions=metrics["impressions"],
                likes=metrics["likes"],
                shares=metrics["shares"],
                comments=metrics["comments"],
                saves=metrics.get("saves", 0),
            )
            metrics_fetched += 1

        processed += 1

    return {
        "posts_processed": processed,
        "metrics_fetched": metrics_fetched,
        "errors": errors,
    }


async def record_social_metrics(
    draft_id: str,
    platform: str,
    impressions: int,
    likes: int,
    shares: int,
    comments: int,
    saves: int = 0,
) -> None:
    """
    Record social metrics for a published draft.

    Args:
        draft_id: Draft ID (not research_item_id)
        platform: Platform name (linkedin, instagram, tiktok, etc.)
        impressions: Number of impressions
        likes: Number of likes
        shares: Number of shares
        comments: Number of comments
        saves: Number of saves (Instagram only)
    """
    db = get_db()

    db.table("social_metrics").upsert({
        "draft_id": draft_id,
        "platform": platform,
        "impressions": impressions,
        "likes": likes,
        "shares": shares,
        "comments": comments,
        "saves": saves,
        "recorded_at": datetime.utcnow().isoformat(),
    }, on_conflict="draft_id,platform").execute()


def compute_engagement_score_optimized(metrics: list[dict]) -> float:
    """
    Compute weighted engagement score with temporal decay and platform normalization.

    Features:
    - Temporal weight: Recent metrics matter more (exponential decay over 30 days)
    - Platform normalization: Different baselines for LinkedIn vs Instagram vs TikTok
    - Volume threshold: Ignore posts with < 100 impressions (low signal)
    - Formula: 5.0 + (weighted_avg * 2.5), clamped to [0.0, 10.0]

    Args:
        metrics: List of metric dicts from social_metrics table

    Returns:
        float: Score in [0.0, 10.0] range
    """
    if not metrics:
        return 5.0

    scored_metrics = []
    now = datetime.utcnow()

    for m in metrics:
        # Volume threshold: ignore low-impression posts
        if m.get("impressions", 0) < 100:
            continue

        # Engagement rate normalized by platform
        platform_baseline = {
            "linkedin": 0.02,   # 2% engagement is average on LinkedIn
            "instagram": 0.04,  # 4% is average on Instagram
            "tiktok": 0.06,    # 6% is average on TikTok
            "twitter": 0.03,    # 3% is average on Twitter/X
        }
        baseline = platform_baseline.get(m.get("platform", "linkedin"), 0.02)

        # Weighted engagement: likes + 3*comments + 5*shares + 2*saves
        weighted_engagement = (
            m.get("likes", 0)
            + m.get("comments", 0) * 3
            + m.get("shares", 0) * 5
            + m.get("saves", 0) * 2
        )

        rate = weighted_engagement / m.get("impressions", 1)
        normalized = rate / baseline if baseline > 0 else rate

        # Temporal decay: exponential over 30 days
        recorded_at = m.get("recorded_at")
        if recorded_at:
            try:
                recorded_dt = datetime.fromisoformat(recorded_at)
                days_ago = (now - recorded_dt).days
                weight = math.exp(-0.05 * days_ago)
            except (ValueError, TypeError):
                weight = 0.5  # Fallback for invalid dates
        else:
            weight = 0.5  # Fallback for missing dates

        scored_metrics.append(normalized * weight)

    if not scored_metrics:
        return 5.0

    avg = sum(scored_metrics) / len(scored_metrics)
    return min(10.0, max(0.0, 5.0 + avg * 2.5))


async def update_feedback_bonus(brand_id: str) -> dict:
    """
    Update feedback_bonus for a brand based on recent engagement metrics.

    Args:
        brand_id: Brand ID to update

    Returns:
        {
            "previous_score": float,
            "new_score": float,
            "metrics_used": int,
            "updated_at": str
        }
    """
    db = get_db()

    # Get current feedback_bonus
    brand = db.table("brands").select("feedback_bonus").eq("id", brand_id).single().execute()
    previous = brand.data.get("feedback_bonus", 5.0) if brand.data else 5.0

    # Get metrics from last 30 days
    cutoff = datetime.utcnow() - timedelta(days=30)
    draft_ids_resp = db.table("content_drafts")\
        .select("id")\
        .eq("brand_id", brand_id)\
        .eq("status", "published")\
        .execute()
    draft_ids = [row["id"] for row in (draft_ids_resp.data or [])]

    if draft_ids:
        metrics_resp = db.table("social_metrics")\
            .select("*")\
            .gte("recorded_at", cutoff.isoformat())\
            .in_("draft_id", draft_ids)\
            .execute()
    else:
        class _EmptyResp:
            data: list[dict] = []
        metrics_resp = _EmptyResp()

    # Compute new score
    new_score = compute_engagement_score_optimized(metrics_resp.data or [])

    # Update in database
    db.table("brands").update({
        "feedback_bonus": new_score,
        "updated_at": datetime.utcnow().isoformat(),
    }).eq("id", brand_id).execute()

    return {
        "previous_score": previous,
        "new_score": new_score,
        "metrics_used": len(metrics_resp.data or []),
        "updated_at": datetime.utcnow().isoformat(),
    }


async def run_daily_analytics_cycle() -> dict:
    """
    Run the complete daily analytics cycle for all active brands.

    This is the entry point for pg_cron scheduling.

    Returns:
        {
            "brands_processed": int,
            "total_posts_processed": int,
            "total_metrics_fetched": int,
            "brands_updated": int,
            "errors": list[str]
        }
    """
    db = get_db()

    # Get all active brands
    brands_resp = db.table("brands").select("id, name").execute()
    brands = brands_resp.data or []

    results = {
        "brands_processed": 0,
        "total_posts_processed": 0,
        "total_metrics_fetched": 0,
        "brands_updated": 0,
        "errors": [],
    }

    for brand in brands:
        brand_id = brand["id"]
        try:
            # Step 1: Pull daily metrics
            pull_result = await pull_daily_metrics(brand_id, days_back=7)

            # Step 2: Update feedback_bonus
            update_result = await update_feedback_bonus(brand_id)

            results["brands_processed"] += 1
            results["total_posts_processed"] += pull_result.get("posts_processed", 0)
            results["total_metrics_fetched"] += pull_result.get("metrics_fetched", 0)
            if update_result.get("metrics_used", 0) > 0:
                results["brands_updated"] += 1

        except Exception as e:
            results["errors"].append(f"Brand {brand.get('name', brand_id)}: {e}")

    return results
