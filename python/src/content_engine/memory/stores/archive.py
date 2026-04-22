"""Archive (cold) memory store — read-only access to partitioned monthly archive.

Writes happen automatically via the nightly hot→cold sweep in the DB
(pg_cron job in migration 018).  This module only provides read access
for audit / admin purposes.
"""

from __future__ import annotations

import logging
from typing import Any

from ...db import get_db

logger = logging.getLogger(__name__)


async def list_archived(
    brand_id: str,
    kind: str | None = None,
    year_month: str | None = None,   # e.g. "2026-04"
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Return archived facts for a brand.

    `year_month` filters by the partition key `archived_at` using a date
    range (first to last day of that month).
    """
    db = get_db()
    q = (
        db.table("memory_archive")
        .select(
            "id,brand_id,kind,statement,tier,importance,asserted_at,"
            "archived_at,source_kind,source_id,metadata"
        )
        .eq("brand_id", brand_id)
        .order("archived_at", desc=True)
        .limit(limit)
    )
    if kind:
        q = q.eq("kind", kind)
    if year_month:
        try:
            import calendar
            from datetime import date

            y, m = map(int, year_month.split("-"))
            first = date(y, m, 1).isoformat()
            last_day = calendar.monthrange(y, m)[1]
            last = date(y, m, last_day).isoformat()
            q = q.gte("archived_at", first).lte("archived_at", last)
        except Exception:
            logger.warning("archive.list_archived: invalid year_month=%s", year_month)

    return q.execute().data or []


async def count_archived(brand_id: str) -> int:
    """Fast count of all archived rows for a brand."""
    db = get_db()
    resp = (
        db.table("memory_archive")
        .select("id", count="exact")
        .eq("brand_id", brand_id)
        .execute()
    )
    return resp.count or 0
