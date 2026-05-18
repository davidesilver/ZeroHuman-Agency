"""Audit trail — logs every publish operation with structured data.

Provides an immutable record of what was published, when, by whom,
and the outcome. Essential for debugging and compliance.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from ..db import get_db

logger = logging.getLogger("content_engine.audit")


async def log_publish_event(
    brand_id: str,
    draft_id: str,
    *,
    action: str,
    platform: str = "",
    status: str = "success",
    details: dict | None = None,
    error: str | None = None,
) -> dict:
    """Record a publish-related event to the audit trail.

    Args:
        brand_id: The brand performing the action.
        draft_id: The content draft involved.
        action: What happened (e.g., 'linkedin_publish', 'newsletter_send', 'schedule').
        platform: Target platform.
        status: 'success', 'failed', 'skipped'.
        details: Additional structured data about the event.
        error: Error message if status is 'failed'.
    """
    db = get_db()

    event = {
        "brand_id": brand_id,
        "draft_id": draft_id,
        "action": action,
        "platform": platform,
        "status": status,
        "details": details or {},
        "error": error,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    try:
        result = db.table("audit_trail").insert(event).execute()
        logger.info(
            "Audit: %s %s on %s → %s",
            action, draft_id[:8], platform or "system", status,
        )
        return result.data[0] if result.data else event
    except Exception as e:
        # Audit trail should never block the main flow
        logger.warning("Failed to write audit trail: %s", e)
        return event
