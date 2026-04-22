"""Unified recall interface — the public entrypoint for all agent memory reads.

Usage:
    from content_engine.memory import recall

    facts = await recall(brand_id, "brand tone of voice", kind="tone_rule", k=5)

`recall()` delegates to `memory_search()` SQL RPC which applies temporal-weighted
composite scoring:  0.60·cosine + 0.25·exp(-0.02·age_days) + 0.15·importance

The function also calls `memory_touch()` on each returned row to:
  - increment retrieval_hits counter
  - refresh the expires_at TTL (refresh-on-read pattern)
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from ..db import get_db
from .stores.semantic import recall as _semantic_recall

logger = logging.getLogger(__name__)


async def recall(
    brand_id: str,
    query: str,
    kind: str | None = None,
    k: int = 5,
    touch: bool = True,
) -> list[dict[str, Any]]:
    """Return top-k memory facts for `brand_id` matching `query`.

    Args:
        brand_id:  Target brand (must be in brand_members for the caller).
        query:     Natural language query — embedded to cosine-compare.
        kind:      Optional fact kind filter (tone_rule, principle, …).
        k:         Max number of results (default 5).
        touch:     If True, refresh TTL + increment hit counts (default True).

    Returns:
        List of dicts: id, statement, kind, tier, similarity, age_days, score.
    """
    results = await _semantic_recall(brand_id=brand_id, query=query, kind=kind, k=k)  # type: ignore[arg-type]

    if touch and results:
        asyncio.create_task(_touch_all([r["id"] for r in results]))

    return results


async def recall_batch(
    brand_id: str,
    queries: list[str],
    kind: str | None = None,
    k: int = 5,
) -> list[list[dict[str, Any]]]:
    """Run multiple recall queries concurrently; returns one list per query."""
    tasks = [recall(brand_id, q, kind=kind, k=k, touch=True) for q in queries]
    return list(await asyncio.gather(*tasks))


async def _touch_all(fact_ids: list[str]) -> None:
    """Call memory_touch() for each id — fires-and-forgets, never raises."""
    db = get_db()
    for fid in fact_ids:
        try:
            db.rpc("memory_touch", {"p_id": fid}).execute()
        except Exception as e:
            logger.debug("recall._touch_all: failed for %s: %s", fid, e)
