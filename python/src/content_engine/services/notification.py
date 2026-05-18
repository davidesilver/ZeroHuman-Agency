"""Notification service — structured event persistence and Telegram delivery.

Replaces the ad-hoc send_telegram_alert() calls scattered across the codebase
with a single service that:
  - Persists every event to notification_events
  - Routes by severity: error/warning/success → immediate Telegram alert
  - info severity → digest-only (batched into the daily digest)
  - Composes daily digest messages per brand

All methods are best-effort: failures are logged but never raise.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from ..config import settings
from ..db import get_db

logger = logging.getLogger(__name__)

# Severities that trigger an immediate Telegram alert (not just digest)
_IMMEDIATE_SEVERITIES = {"error", "warning", "success"}

# Emoji prefix per severity
_SEVERITY_EMOJI = {
    "success": "✅",
    "warning": "⚠️",
    "error": "🔴",
    "info": "ℹ️",
}

# Dashboard base URL for deep links
_DASHBOARD_BASE = settings.dashboard_url

_ENTITY_PATHS = {
    "newsletter": "/newsletter/{id}",
    "draft": "/drafts/{id}",
    "research_item": "/research/{id}",
    "brand": "/settings",
}


def _entity_link(entity_type: str | None, entity_id: str | None) -> str:
    if not entity_type or not entity_id or not _DASHBOARD_BASE:
        return ""
    path_template = _ENTITY_PATHS.get(entity_type, "")
    if not path_template:
        return ""
    return f"{_DASHBOARD_BASE}{path_template.format(id=entity_id)}"


def _escape_md(text: str) -> str:
    """Escape Telegram Markdown special chars."""
    for ch in r"\_*[]()~`>#+-=|{}.!":
        text = text.replace(ch, f"\\{ch}")
    return text


async def _send_telegram(text: str) -> bool:
    bot_token = settings.telegram_bot_token
    chat_id = settings.telegram_chat_id
    if not bot_token or not chat_id:
        logger.warning("Telegram skipped: token or chat_id not configured")
        return False
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return True
    except Exception as exc:
        logger.error("Telegram send failed: %s", exc)
        return False


async def emit_event(
    event_type: str,
    title: str,
    severity: str = "info",
    brand_id: str | None = None,
    detail: dict[str, Any] | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
) -> None:
    """Persist a notification event and send an immediate Telegram alert if warranted."""
    try:
        db = get_db()
        row = {
            "event_type": event_type,
            "severity": severity,
            "title": title,
            "detail": detail or {},
            "entity_type": entity_type,
            "entity_id": entity_id,
        }
        if brand_id:
            row["brand_id"] = brand_id
        db.table("notification_events").insert(row).execute()
    except Exception as exc:
        logger.error("Failed to persist notification event %s: %s", event_type, exc)

    if severity in _IMMEDIATE_SEVERITIES:
        try:
            emoji = _SEVERITY_EMOJI.get(severity, "")
            brand_label = f" — Brand `{brand_id[:8]}`" if brand_id else ""
            link = _entity_link(entity_type, entity_id)
            lines = [f"{emoji} *{_escape_md(title)}*{brand_label}"]
            if detail:
                for k, v in detail.items():
                    lines.append(f"• {_escape_md(str(k))}: `{_escape_md(str(v))}`")
            if link:
                lines.append(f"🔗 {link}")
            await _send_telegram("\n".join(lines))
        except Exception as exc:
            logger.error("Failed to send immediate Telegram alert for %s: %s", event_type, exc)


async def send_digest(brand_id: str, pipeline_results: dict[str, Any]) -> None:
    """Compose and send a per-brand daily digest after the pipeline run."""
    try:
        db = get_db()

        # Find last digest sent for this brand
        last_digest = (
            db.table("notification_events")
            .select("created_at")
            .eq("brand_id", brand_id)
            .eq("event_type", "daily_digest_sent")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
            .data
        )
        since = (
            last_digest[0]["created_at"]
            if last_digest
            else (datetime.now(UTC) - timedelta(hours=25)).isoformat()
        )

        events = (
            db.table("notification_events")
            .select("event_type, severity, title, detail")
            .eq("brand_id", brand_id)
            .gte("created_at", since)
            .neq("event_type", "daily_digest_sent")
            .order("created_at")
            .execute()
            .data
        ) or []

        # Fetch brand name
        brand_row = (
            db.table("brands").select("name").eq("id", brand_id).maybe_single().execute().data
        )
        brand_name = brand_row["name"] if brand_row else brand_id[:8]

        now_str = datetime.now(UTC).strftime("%-d %B")
        lines = [f"📋 *Daily Report — {_escape_md(brand_name)} — {now_str}*\n"]

        # Research section
        research = pipeline_results.get("research", {})
        items_found = research.get("items_found", 0)
        sources = research.get("sources_scanned", 0)
        lines.append(f"• *Research*: {items_found} items found, {sources} sources scanned")

        # Scoring section
        scoring = pipeline_results.get("scoring", {})
        if isinstance(scoring, dict):
            avg = scoring.get("average_score", "—")
            lines.append(f"• *Scoring*: avg {avg}/10")
        else:
            lines.append("• *Scoring*: completed")

        # Drafts section
        drafts = pipeline_results.get("drafts_generated", [])
        lines.append(f"• *Drafts*: {len(drafts)} generated")

        # Issues from recent events
        issues = [e for e in events if e["severity"] in ("error", "warning")]
        if issues:
            lines.append(f"\n⚠️ *Issues \\({len(issues)}\\)*:")
            for issue in issues[:5]:
                lines.append(f"  • {_escape_md(issue['title'])}")
            if len(issues) > 5:
                lines.append(f"  • \\.\\.\\. and {len(issues) - 5} more")
        else:
            lines.append("\n✅ No issues")

        # Persist digest event
        db.table("notification_events").insert({
            "brand_id": brand_id,
            "event_type": "daily_digest_sent",
            "severity": "info",
            "title": f"Daily digest sent for {brand_name}",
            "detail": {"events_included": len(events)},
        }).execute()

        await _send_telegram("\n".join(lines))

    except Exception as exc:
        logger.error("Failed to send digest for brand %s: %s", brand_id, exc)


# ---------------------------------------------------------------------------
# Legacy shim — existing call sites migrated here during Phase 1
# ---------------------------------------------------------------------------

async def send_telegram_alert(message: str) -> bool:
    """Backward-compatible shim for legacy send_telegram_alert calls."""
    try:
        await emit_event(
            event_type="legacy_alert",
            title=message[:200],
            severity="warning",
            detail={"message": message},
        )
        return True
    except Exception:
        return False
