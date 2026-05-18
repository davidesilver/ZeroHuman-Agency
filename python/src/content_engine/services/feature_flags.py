"""Per-brand feature flags helper.

Reads from the `feature_flags` table (migration 031).

Usage:
    from content_engine.services.feature_flags import get_feature_flag, set_feature_flag

    if await get_feature_flag(brand_id, "video_enabled"):
        ...
"""

from __future__ import annotations

import logging

from ..db import get_db

logger = logging.getLogger(__name__)

# ── known flag keys (convenience constants) ────────────────────────────────
VIDEO_ENABLED = "video_enabled"
EMAIL_MARKETING_ENABLED = "email_marketing_enabled"
DEEP_RESEARCH_ENABLED = "deep_research_enabled"
COMPETITOR_MONITORING_ENABLED = "competitor_monitoring_enabled"
LLM_PROVIDER_OPENCLAW_SHARE = "llm_provider_openclaw_share"


def get_feature_flag(brand_id: str, key: str, default: bool = False) -> bool:
    """Return the boolean value of a feature flag for a brand.

    Falls back to *default* (False) if the row does not exist.
    Uses the service-role client — safe for background jobs and server-side calls.
    """
    try:
        result = (
            get_db()
            .from_("feature_flags")
            .select("value")
            .eq("brand_id", brand_id)
            .eq("key", key)
            .maybe_single()
            .execute()
        )
        if result.data:
            return bool(result.data["value"])
    except Exception:
        logger.exception("feature_flags: read error for brand=%s key=%s", brand_id, key)
    return default


def set_feature_flag(brand_id: str, key: str, value: bool) -> None:
    """Upsert a feature flag for a brand."""
    get_db().from_("feature_flags").upsert(
        {"brand_id": brand_id, "key": key, "value": value},
        on_conflict="brand_id,key",
    ).execute()
