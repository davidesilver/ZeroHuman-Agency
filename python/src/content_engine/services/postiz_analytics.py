"""Postiz Analytics Puller — fetch engagement metrics and compute dynamic feedback_bonus.

Uses the typed PostizClient so it works for both self-hosted and cloud mode.
"""
from __future__ import annotations

import logging
import math
from datetime import UTC, datetime, timedelta

from ..config import settings
from ..db import get_db
from .postiz_client import PostizClient

_logger = logging.getLogger("content_engine.postiz_analytics")


async def fetch_post_analytics(postiz_id: str) -> dict | None:
    """Fetch analytics for a single post from Postiz API.

    Returns None on failure but logs the error — the caller decides whether
    partial-result recovery is acceptable. Silent failure here previously
    masked analytics pipeline gaps.
    """
    if not _postiz_available():
        return None
    try:
        client = PostizClient()
        data = await client.get_post_analytics(postiz_id)
        return {
            "platform": data.get("platform", "unknown"),
            "impressions": data.get("impressions", 0),
            "likes": data.get("likes", 0),
            "shares": data.get("shares", 0),
            "comments": data.get("comments", 0),
            "saves": data.get("saves", 0),
        }
    except Exception as e:
        _logger.error(
            "fetch_post_analytics failed for postiz_id=%s: %s",
            postiz_id, e, exc_info=True,
        )
        return None


def _postiz_available() -> bool:
    return settings.postiz_mode in ("self_hosted", "cloud")


async def pull_daily_metrics(brand_id: str, days_back: int = 7) -> dict:
    """Pull daily metrics for all published posts from the last N days."""
    db = get_db()
    errors = []
    processed = 0
    metrics_fetched = 0

    cutoff = datetime.now(UTC) - timedelta(days=days_back)
    drafts_resp = (
        db.table("content_drafts")
        .select("id, metadata, published_at")
        .eq("brand_id", brand_id)
        .eq("status", "published")
        .gte("published_at", cutoff.isoformat())
        .execute()
    )

    for draft in drafts_resp.data or []:
        metadata = draft.get("metadata") or {}
        postiz_ids = metadata.get("postiz_post_ids", {})
        if not postiz_ids or isinstance(postiz_ids, str):
            continue

        for platform, postiz_id in postiz_ids.items():
            if not postiz_id or postiz_id.startswith("fake_"):
                continue
            metrics = await fetch_post_analytics(postiz_id)
            if metrics:
                await record_social_metrics(
                    draft_id=draft["id"],
                    platform=platform,
                    impressions=metrics["impressions"],
                    likes=metrics["likes"],
                    shares=metrics["shares"],
                    comments=metrics["comments"],
                    saves=metrics.get("saves", 0),
                )
                metrics_fetched += 1
            else:
                errors.append(
                    f"draft={draft['id']} platform={platform} postiz_id={postiz_id}: no metrics"
                )

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
    """Record social metrics for a published draft."""
    db = get_db()
    db.table("social_metrics").upsert({
        "draft_id": draft_id,
        "platform": platform,
        "impressions": impressions,
        "likes": likes,
        "shares": shares,
        "comments": comments,
        "saves": saves,
        "recorded_at": datetime.now(UTC).isoformat(),
    }, on_conflict="draft_id,platform").execute()


def compute_engagement_score_optimized(metrics: list[dict]) -> float:
    """Compute weighted engagement score with temporal decay and platform normalization."""
    if not metrics:
        return 5.0

    scored_metrics = []
    now = datetime.now(UTC)

    for m in metrics:
        if m.get("impressions", 0) < 100:
            continue

        platform_baseline = {
            "linkedin": 0.02,
            "instagram": 0.04,
            "tiktok": 0.06,
            "twitter": 0.03,
            "x": 0.03,
        }
        baseline = platform_baseline.get(m.get("platform", "linkedin"), 0.02)

        weighted_engagement = (
            m.get("likes", 0)
            + m.get("comments", 0) * 3
            + m.get("shares", 0) * 5
            + m.get("saves", 0) * 2
        )

        rate = weighted_engagement / m.get("impressions", 1)
        normalized = rate / baseline if baseline > 0 else rate

        recorded_at = m.get("recorded_at")
        if recorded_at:
            try:
                recorded_dt = datetime.fromisoformat(recorded_at)
                days_ago = (now - recorded_dt).days
                weight = math.exp(-0.05 * days_ago)
            except (ValueError, TypeError):
                weight = 0.5
        else:
            weight = 0.5

        scored_metrics.append(normalized * weight)

    if not scored_metrics:
        return 5.0

    avg = sum(scored_metrics) / len(scored_metrics)
    return min(10.0, max(0.0, 5.0 + avg * 2.5))


async def update_feedback_bonus(brand_id: str) -> dict:
    """Update feedback_bonus for a brand based on recent engagement metrics."""
    db = get_db()

    brand = db.table("brands").select("feedback_bonus").eq("id", brand_id).single().execute()
    previous = brand.data.get("feedback_bonus", 5.0) if brand.data else 5.0

    cutoff = datetime.now(UTC) - timedelta(days=30)
    draft_ids_resp = (
        db.table("content_drafts")
        .select("id")
        .eq("brand_id", brand_id)
        .eq("status", "published")
        .execute()
    )
    draft_ids = [row["id"] for row in (draft_ids_resp.data or [])]

    if draft_ids:
        metrics_resp = (
            db.table("social_metrics")
            .select("*")
            .gte("recorded_at", cutoff.isoformat())
            .in_("draft_id", draft_ids)
            .execute()
        )
        metrics_data = metrics_resp.data or []
    else:
        metrics_data = []

    new_score = compute_engagement_score_optimized(metrics_data)

    db.table("brands").update({
        "feedback_bonus": new_score,
        "updated_at": datetime.now(UTC).isoformat(),
    }).eq("id", brand_id).execute()

    return {
        "previous_score": previous,
        "new_score": new_score,
        "metrics_used": len(metrics_data),
        "updated_at": datetime.now(UTC).isoformat(),
    }


async def run_daily_analytics_cycle() -> dict:
    """Run the complete daily analytics cycle for all active brands."""
    db = get_db()
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
            pull_result = await pull_daily_metrics(brand_id, days_back=7)
            update_result = await update_feedback_bonus(brand_id)

            results["brands_processed"] += 1
            results["total_posts_processed"] += pull_result.get("posts_processed", 0)
            results["total_metrics_fetched"] += pull_result.get("metrics_fetched", 0)
            if update_result.get("metrics_used", 0) > 0:
                results["brands_updated"] += 1
        except Exception as e:
            results["errors"].append(f"Brand {brand.get('name', brand_id)}: {e}")

    return results
