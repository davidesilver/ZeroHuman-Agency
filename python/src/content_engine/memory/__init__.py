"""content_engine.memory — multi-layer brand memory system.

Public API (import from here):

    from content_engine.memory import hot, semantic, events, recall, consolidate, arbiter

Hot store (session KV, 24h TTL):
    await memory.hot.put(brand_id, session_id, key, value)
    value = await memory.hot.get(brand_id, session_id, key)
    kv = await memory.hot.get_session(brand_id, session_id)
    await memory.hot.clear_session(brand_id, session_id)

Events (supplementary episodic log):
    await memory.events.log(brand_id, kind, summary, subject_kind, subject_id, payload)

Semantic recall (temporal-weighted):
    facts = await memory.recall(brand_id, query, kind="tone_rule", k=5)

Consolidation (extract → verify → write):
    report = await memory.consolidate.run(brand_id, session_id, source_texts=[...])

Arbiter (conflict resolution via supersede):
    new_id = await memory.arbiter.supersede(old_fact_id, new_statement, brand_id)

Decay sweep:
    stats = await memory.decay.sweep(brand_id)
"""

from __future__ import annotations

from datetime import UTC

from . import arbiter, decay
from . import consolidation as consolidate
from .retrieval import recall, recall_batch
from .stores import hot, semantic

# Convenience re-export of the main consolidation entry point
run_consolidation = consolidate.run_consolidation


class _Events:
    """Thin wrapper so callers can do `memory.events.log(...)` symmetrically."""

    async def log(
        self,
        brand_id: str,
        kind: str,
        summary: str,
        subject_kind: str | None = None,
        subject_id: str | None = None,
        payload: dict | None = None,
        ttl_days: int = 90,
    ) -> None:
        """Append a supplementary event to memory_events (episodic feed)."""
        from datetime import datetime, timedelta

        from ..db import get_db

        expires_at = (
            datetime.now(UTC) + timedelta(days=ttl_days)
        ).isoformat()

        db = get_db()
        db.table("memory_events").insert(
            {
                "brand_id": brand_id,
                "event_kind": kind,
                "subject_kind": subject_kind,
                "subject_id": subject_id,
                "summary": summary,
                "payload": payload or {},
                "occurred_at": datetime.now(UTC).isoformat(),
                "expires_at": expires_at,
            }
        ).execute()


events = _Events()

__all__ = [
    "hot",
    "semantic",
    "events",
    "recall",
    "recall_batch",
    "arbiter",
    "decay",
    "consolidate",
    "run_consolidation",
]
