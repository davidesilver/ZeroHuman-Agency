"""Scheduler service — automated research, scoring, and publishing."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from ..db import get_db
from ..models import ScoringRequest, TriggerRequest
from ..orchestrator.content import generate_content
from ..orchestrator.research import run_research
from ..scoring.engine import run_scoring
from .feedback_loop import update_feedback_bonus

logger = logging.getLogger("content_engine.scheduler")


async def daily_research_pipeline(brand_id: str) -> dict:
    """Run the full daily research + scoring + draft generation pipeline.

    This is designed to be triggered by a cron job (e.g., at 07:00 daily).
    Steps:
    0. Daily cost cap check — abort early if exceeded
    1. Run research across all retrievers
    2. Score new items
    3. Generate drafts for recently approved items (up to 3)
    4. Update feedback loop from analytics
    """
    from ..utils.cost_tracker import check_daily_cost_cap

    # Step 0: Daily cost cap guard
    try:
        await check_daily_cost_cap(brand_id)
    except RuntimeError as e:
        logger.error("Daily cost cap exceeded for brand %s: %s", brand_id, e)
        return {"aborted": True, "reason": str(e)}

    results = {}

    # Step 1: Research
    research_result = await run_research(brand_id, TriggerRequest())
    results["research"] = {
        "items_found": research_result.items_found,
        "sources_scanned": research_result.sources_scanned,
        "status": research_result.status,
    }

    if research_result.items_found == 0:
        try:
            from .notification import emit_event
            await emit_event(
                event_type="research_zero_items",
                title="Zero items found in daily research",
                severity="warning",
                brand_id=brand_id,
                detail={"sources_scanned": research_result.sources_scanned},
            )
        except Exception as alert_err:
            logger.warning("Notification failed for brand %s: %s", brand_id, alert_err)

    # Step 2: Scoring
    scoring_result = await run_scoring(brand_id, ScoringRequest())
    results["scoring"] = scoring_result

    # Step 3: Draft generation for recently approved items
    drafts_generated = []
    try:
        from datetime import datetime, timedelta

        db = get_db()
        cutoff = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
        approved_resp = (
            db.table("research_items")
            .select("id")
            .eq("brand_id", brand_id)
            .eq("status", "approved")
            .gte("created_at", cutoff)
            .limit(3)
            .execute()
        )
        approved_items = approved_resp.data or []

        for item in approved_items:
            try:
                draft_result = await generate_content(brand_id, research_item_id=item["id"])
                drafts_generated.append({"item_id": item["id"], "draft_id": draft_result["draft_id"]})
                logger.info(
                    "Draft generated for brand %s, item %s -> draft %s",
                    brand_id, item["id"], draft_result["draft_id"],
                )
            except Exception as draft_err:
                logger.error(
                    "Draft generation failed for brand %s, item %s: %s",
                    brand_id, item["id"], draft_err,
                )
    except Exception as e:
        logger.error("Step 3 (draft generation) failed for brand %s: %s", brand_id, e)

    results["drafts_generated"] = drafts_generated

    # Step 4: Feedback loop
    feedback_result = await update_feedback_bonus(brand_id)
    results["feedback"] = feedback_result

    # Step 5: Daily digest — always sent, even on full success
    try:
        from .notification import send_digest
        await send_digest(brand_id, results)
    except Exception as digest_err:
        logger.warning("Daily digest failed for brand %s: %s", brand_id, digest_err)

    return results


async def publish_scheduled_posts(brand_id: str) -> dict:
    """Publish any posts that are past their scheduled time via Postiz."""
    db = get_db()

    # M-09: use timezone-aware datetime (utcnow() deprecated in Python 3.12)
    now = datetime.now(UTC).isoformat()

    scheduled = db.table("content_drafts").select("id, platform, scheduled_at, metadata").eq(
        "brand_id", brand_id
    ).eq("status", "scheduled").lte("scheduled_at", now).execute().data

    published = []
    errors = []

    for draft in (scheduled or []):
        try:
            from .postiz_publisher import publish_scheduled_via_postiz
            result = await publish_scheduled_via_postiz(brand_id, draft)

            if result.get("status") == "published":
                published.append(draft["id"])
            elif result.get("status") == "scheduled_on_platform":
                # Already on Postiz — mark as published in our DB
                db.table("content_drafts").update({
                    "status": "published",
                }).eq("id", draft["id"]).execute()
                published.append(draft["id"])
            else:
                errors.append({"draft_id": draft["id"], "error": "Unexpected status from Postiz"})
        except Exception as e:
            logger.exception("Failed to publish scheduled draft %s", draft["id"])
            errors.append({"draft_id": draft["id"], "error": str(e)})
            # Mark as failed after max retries logic could be added here

    return {
        "published": len(published),
        "errors": len(errors),
        "details": errors if errors else None,
    }
