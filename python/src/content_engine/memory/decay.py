"""TTL sweep helper — called by the nightly pg_cron job via the API endpoint
(or directly from the scheduler for on-demand cleanup).

The primary TTL sweep runs inside Postgres via the pg_cron job defined in
migration 018.  This Python module provides:
  1. An async `sweep()` function for on-demand Python-triggered cleanup.
  2. Stats reporting for the Memory Inspector UI.

Note: The pg_cron job at 03:30 UTC is the canonical sweep.
      This module is a secondary safety net and diagnostic tool.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from ..db import get_db

logger = logging.getLogger(__name__)


@dataclass
class SweepStats:
    hot_deleted: int = 0
    semantic_expired: int = 0   # rows with expires_at < now (still live, not deleted)
    errors: list[str] | None = None

    def summary(self) -> str:
        return (
            f"Sweep: {self.hot_deleted} hot rows deleted, "
            f"{self.semantic_expired} semantic rows expiring"
        )


async def sweep(brand_id: str | None = None) -> SweepStats:
    """Delete expired hot-store rows; report expiring semantic rows.

    If `brand_id` is None, sweeps ALL brands (system cron use).
    Returns a SweepStats summary.
    """
    stats = SweepStats(errors=[])
    db = get_db()
    now = datetime.now(UTC).isoformat()

    # ── Hot store: hard delete expired rows ────────────────────────────────
    try:
        q = db.table("memory_hot").delete().lt("expires_at", now)
        if brand_id:
            q = q.eq("brand_id", brand_id)
        resp = q.execute()
        stats.hot_deleted = len(resp.data or [])
    except Exception as e:
        msg = f"hot sweep failed: {e}"
        logger.error("decay.sweep: %s", msg)
        stats.errors.append(msg)  # type: ignore[union-attr]

    # ── Semantic store: count (not delete) expiring rows ──────────────────
    # We count but don't delete — expired rows are kept as history
    # (they appear in admin queries but are filtered in recall/list_facts).
    # Actual archival happens via pg_cron monthly partition sweep.
    try:
        q = (
            db.table("memory_semantic")
            .select("id", count="exact")
            .lt("expires_at", now)
            .not_.is_("expires_at", "null")
        )
        if brand_id:
            q = q.eq("brand_id", brand_id)
        resp = q.execute()
        stats.semantic_expired = resp.count or 0
    except Exception as e:
        msg = f"semantic count failed: {e}"
        logger.warning("decay.sweep: %s", msg)
        stats.errors.append(msg)  # type: ignore[union-attr]

    logger.info("decay.sweep %s", stats.summary())
    return stats


async def expiring_soon(brand_id: str, days: int = 7) -> list[dict]:
    """Return semantic facts expiring within `days` days (for UI warnings)."""
    from datetime import timedelta

    db = get_db()
    cutoff = (datetime.now(UTC) + timedelta(days=days)).isoformat()
    now = datetime.now(UTC).isoformat()

    resp = (
        db.table("memory_semantic")
        .select("id,kind,statement,tier,expires_at")
        .eq("brand_id", brand_id)
        .gt("expires_at", now)
        .lt("expires_at", cutoff)
        .order("expires_at")
        .limit(50)
        .execute()
    )
    return resp.data or []
