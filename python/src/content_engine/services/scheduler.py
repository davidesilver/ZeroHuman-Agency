"""Scheduler service — automated research, scoring, and publishing."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from ..config import settings
from ..db import get_db
from ..models import TriggerRequest, ScoringRequest
from ..orchestrator.research import run_research
from ..scoring.engine import run_scoring
from .feedback_loop import update_feedback_bonus

import logging
logger = logging.getLogger("content_engine.scheduler")


async def daily_research_pipeline(brand_id: str) -> dict:
    """Run the full daily research + scoring pipeline.

    This is designed to be triggered by a cron job (e.g., at 07:00 daily).
    Steps:
    1. Run research across all retrievers
    2. Score new items
    3. Update feedback loop from analytics
    """
    results = {}

    # Step 1: Research
    research_result = await run_research(brand_id, TriggerRequest())
    results["research"] = {
        "items_found": research_result.items_found,
        "sources_scanned": research_result.sources_scanned,
        "status": research_result.status,
    }

    if research_result.items_found == 0:
        from .alerting import send_telegram_alert
        await send_telegram_alert(f"⚠️ Zero items found in daily research for brand `{brand_id}`. Check crawler/API endpoints.")

    # Step 2: Scoring
    scoring_result = await run_scoring(brand_id, ScoringRequest())
    results["scoring"] = scoring_result

    # Step 3: Feedback loop
    feedback_result = await update_feedback_bonus(brand_id)
    results["feedback"] = feedback_result

    return results


async def publish_scheduled_posts(brand_id: str) -> dict:
    """Publish any posts that are past their scheduled time."""
    db = get_db()

    # M-09: use timezone-aware datetime (utcnow() deprecated in Python 3.12)
    now = datetime.now(timezone.utc).isoformat()

    scheduled = db.table("content_drafts").select("id, platform, scheduled_at").eq(
        "brand_id", brand_id
    ).eq("status", "scheduled").lte("scheduled_at", now).execute().data

    published = []
    errors = []

    for draft in (scheduled or []):
        try:
            # For now, mark as published (actual platform delivery requires API keys)
            db.table("content_drafts").update({
                "status": "published",
            }).eq("id", draft["id"]).execute()
            published.append(draft["id"])
        except Exception as e:
            errors.append({"draft_id": draft["id"], "error": str(e)})

    return {
        "published": len(published),
        "errors": len(errors),
        "details": errors if errors else None,
    }
