"""Pipeline Health Dashboard — track scoring pipeline metrics and alert on anomalies."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from ..db import get_db


async def get_pipeline_health(brand_id: Optional[str] = None) -> dict:
    """
    Get pipeline health metrics for a brand or all brands.

    Args:
        brand_id: Optional brand ID. If None, aggregates across all brands.

    Returns:
        {
            "summary": {
                "total_items": int,
                "scored": int,
                "approved": int,
                "rejected": int,
                "anti_hype_discarded": int,
                "archived_duplicates": int,
                "pending_review": int,
                "errors": int,
                "approval_rate": float,
                "hype_filter_rate": float,
                "dedup_rate": float,
            },
            "alerts": list[str],
            "last_scoring_run": str | None,
            "trends": {
                "7_day_avg": dict,
                "30_day_avg": dict,
            }
        }
    """
    db = get_db()

    # Build query
    query = db.table("research_items").select("*")
    if brand_id:
        query = query.eq("brand_id", brand_id)

    # Get recent items (last 7 days)
    cutoff = datetime.utcnow() - timedelta(days=7)
    items_resp = query.gte("created_at", cutoff.isoformat()).execute()
    items = items_resp.data or []

    # Calculate metrics
    total_items = len(items)
    scored = sum(1 for i in items if i.get("status") in ["scored", "approved", "rejected"])
    approved = sum(1 for i in items if i.get("status") == "approved")
    rejected = sum(1 for i in items if i.get("status") == "rejected")
    anti_hype_discarded = sum(
        1 for i in items
        if i.get("metadata", {}).get("rejection_reason") == "anti_hype_gate"
    )
    archived_duplicates = sum(
        1 for i in items
        if i.get("status") == "archived"
    )
    # 'scored' items are awaiting human review/approval — that is what
    # "pending_review" means in this pipeline context. The item_status enum
    # has no 'pending_review' value; 'scored' is the correct equivalent.
    pending_review = sum(
        1 for i in items
        if i.get("status") == "scored"
    )
    errors = 0  # Would need to track this in DB or logs

    # Calculate rates
    approval_rate = (approved / scored * 100) if scored > 0 else 0.0
    hype_filter_rate = (anti_hype_discarded / total_items * 100) if total_items > 0 else 0.0
    dedup_rate = (archived_duplicates / total_items * 100) if total_items > 0 else 0.0

    # Generate alerts
    alerts = []

    # Alert: Hype filter too aggressive (> 30%)
    if hype_filter_rate > 30.0:
        alerts.append(
            f"⚠️ Hype filter rate {hype_filter_rate:.1f}% > 30%. "
            f"Gate may be too strict. Review gold_examples and discard_examples."
        )

    # Alert: Approval rate too low (< 20%)
    if approval_rate < 20.0 and scored > 10:
        alerts.append(
            f"⚠️ Approval rate {approval_rate:.1f}% < 20%. "
            f"Content quality may be declining. Review scoring thresholds and principles."
        )

    # Alert: High error rate (> 10%)
    if errors > 0 and (errors / total_items * 100) > 10.0:
        alerts.append(
            f"⚠️ Error rate {(errors/total_items*100):.1f}% > 10%. "
            f"Check pipeline logs for issues."
        )

    # Alert: High pending review rate (> 15%)
    pending_rate = (pending_review / total_items * 100) if total_items > 0 else 0.0
    if pending_rate > 15.0:
        alerts.append(
            f"⚠️ Pending review rate {pending_rate:.1f}% > 15%. "
            f"Anti-hype gate may need calibration. Check borderline items."
        )

    # Get last scoring run timestamp (would need to track this)
    last_scoring_run = None  # TODO: Track last run in DB

    # Calculate trends (simplified - would need historical data)
    trends = {
        "7_day_avg": {
            "items_per_day": round(total_items / 7, 1),
            "approved_per_day": round(approved / 7, 1),
            "hype_per_day": round(anti_hype_discarded / 7, 1),
        },
        "30_day_avg": {},
    }

    return {
        "summary": {
            "total_items": total_items,
            "scored": scored,
            "approved": approved,
            "rejected": rejected,
            "anti_hype_discarded": anti_hype_discarded,
            "archived_duplicates": archived_duplicates,
            "pending_review": pending_review,
            "errors": errors,
            "approval_rate": round(approval_rate, 1),
            "hype_filter_rate": round(hype_filter_rate, 1),
            "dedup_rate": round(dedup_rate, 1),
        },
        "alerts": alerts,
        "last_scoring_run": last_scoring_run,
        "trends": trends,
    }


def round(value: float, decimals: int = 1) -> float:
    """Round value to specified decimals."""
    return int(value * (10 ** decimals)) / (10 ** decimals)


async def send_alerts(alerts: list[str], channel: str = "telegram") -> bool:
    """
    Send pipeline alerts via configured channel.

    Args:
        alerts: List of alert messages
        channel: "telegram" or "slack"

    Returns:
        bool: True if sent successfully
    """
    if not alerts:
        return True

    from ..config import settings

    if channel == "telegram":
        if not settings.telegram_bot_token or not settings.telegram_chat_id:
            return False

        import httpx

        message = "🚨 Pipeline Health Alerts:\n\n" + "\n".join(alerts)
        url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
        payload = {
            "chat_id": settings.telegram_chat_id,
            "text": message,
            "parse_mode": "Markdown",
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json=payload)
            return resp.status_code == 200
        except Exception:
            return False

    elif channel == "slack":
        # TODO: Implement Slack webhook integration
        return False

    return False


async def run_health_check(brand_id: Optional[str] = None) -> dict:
    """
    Run health check and send alerts if needed.

    Returns:
        Same as get_pipeline_health plus alert delivery status
    """
    health = await get_pipeline_health(brand_id)

    # Send alerts if any
    alert_status = False
    if health["alerts"]:
        alert_status = await send_alerts(health["alerts"])

    return {
        **health,
        "alert_delivered": alert_status,
        "checked_at": datetime.utcnow().isoformat(),
    }


def format_health_report(health: dict) -> str:
    """
    Format pipeline health report as human-readable text.

    Returns:
        str: Formatted report
    """
    summary = health["summary"]

    report = f"""📊 Pipeline Health Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Summary (Last 7 days):
  • Total items processed: {summary['total_items']}
  • Scored: {summary['scored']} | Approved: {summary['approved']} ({summary['approval_rate']}%)
  • Rejected: {summary['rejected']} | Hype filtered: {summary['anti_hype_discarded']} ({summary['hype_filter_rate']}%)
  • Archived duplicates: {summary['archived_duplicates']} ({summary['dedup_rate']}%)
  • Pending review: {summary['pending_review']}
  • Errors: {summary['errors']}

Metrics:
  • Approval rate: {summary['approval_rate']}%
  • Hype filter rate: {summary['hype_filter_rate']}%
  • Deduplication rate: {summary['dedup_rate']}%
  • Items/day (7d avg): {health['trends']['7_day_avg']['items_per_day']}

"""

    if health["alerts"]:
        report += f"\n🚨️ Alerts ({len(health['alerts'])}):\n"
        for alert in health["alerts"]:
            report += f"  • {alert}\n"

    return report
