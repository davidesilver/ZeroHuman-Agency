"""Consolidation worker — async driver that processes a brand's raw events
into verified semantic memories.

Flow:
1. Fetch recent events from vw_memory_episodic for the brand+session
2. For each event summary, call extractor to get candidate facts
3. Run each candidate through verifier
4. Deduplicate against existing semantic memories (embedding similarity)
5. Write passing facts to memory_semantic
6. Send Telegram alert with summary (P2.T hook)
7. Log a memory_event for auditing

Called by:
  - POST /memory/consolidate  (manual trigger, scheduler-secret protected)
  - Optionally at session end (future: post-session consolidation)
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from ...db import get_db
from ...services.notification import emit_event
from ..stores import semantic as sem_store
from .extractor import extract_facts_from_text
from .verifier import verify

logger = logging.getLogger(__name__)

# Cosine similarity threshold below which we consider the fact "novel"
# (not yet in memory).  0.92 is tighter than the global dedup threshold
# because memory_semantic should be factually deduplicated.
_DEDUP_SIM_THRESHOLD = 0.92


@dataclass
class ConsolidationReport:
    brand_id: str
    session_id: str | None
    facts_added: list[str] = field(default_factory=list)
    facts_rejected_verify: list[str] = field(default_factory=list)
    facts_rejected_dedup: list[str] = field(default_factory=list)
    facts_superseded: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None

    def finish(self) -> "ConsolidationReport":
        self.finished_at = datetime.now(timezone.utc)
        return self

    @property
    def duration_s(self) -> float:
        if self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return 0.0

    def telegram_summary(self) -> str:
        return (
            f"🧠 *Memory Consolidation*\n\n"
            f"Brand: `{self.brand_id[:8]}…`\n"
            f"Session: `{self.session_id or 'batch'}`\n\n"
            f"✅ Added: {len(self.facts_added)}\n"
            f"🔄 Superseded: {len(self.facts_superseded)}\n"
            f"❌ Rejected (verify): {len(self.facts_rejected_verify)}\n"
            f"↩️ Skipped (dedup): {len(self.facts_rejected_dedup)}\n"
            f"⏱ Duration: {self.duration_s:.1f}s"
        )


async def run_consolidation(
    brand_id: str,
    session_id: str | None = None,
    source_texts: list[dict] | None = None,
) -> ConsolidationReport:
    """Main entry point for a single brand consolidation pass.

    Args:
        brand_id:     Target brand.
        session_id:   Optional session identifier for scoped consolidation.
        source_texts: Optional list of {"text": str, "source_kind": str,
                      "source_id": str} dicts to consolidate. If None, the
                      worker falls back to fetching recent episodic events.
    """
    report = ConsolidationReport(brand_id=brand_id, session_id=session_id)
    logger.info(
        "consolidation.run brand=%s session=%s", brand_id, session_id or "batch"
    )

    # ── 1. Gather source texts ──────────────────────────────────────────────
    if not source_texts:
        source_texts = await _fetch_recent_episodic(brand_id, session_id)

    if not source_texts:
        logger.info("consolidation: no source texts for brand=%s", brand_id)
        report.finish()
        return report

    # ── 2. Extract + verify + write ─────────────────────────────────────────
    tasks = [
        _process_source(src, brand_id, report)
        for src in source_texts
    ]
    await asyncio.gather(*tasks, return_exceptions=True)

    report.finish()

    # ── 3. Telegram alert (P2.T) ────────────────────────────────────────────
    asyncio.create_task(
        _send_consolidation_alert(report)
    )

    # ── 4. Log memory_event ─────────────────────────────────────────────────
    asyncio.create_task(
        _log_consolidation_event(report)
    )

    logger.info(
        "consolidation.done brand=%s added=%d rejected_v=%d rejected_d=%d dur=%.1fs",
        brand_id,
        len(report.facts_added),
        len(report.facts_rejected_verify),
        len(report.facts_rejected_dedup),
        report.duration_s,
    )
    return report


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _fetch_recent_episodic(
    brand_id: str,
    session_id: str | None,
    hours: int = 24,
) -> list[dict]:
    """Fetch recent episodic summaries from vw_memory_episodic as source texts."""
    from datetime import timedelta

    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    db = get_db()
    q = (
        db.table("vw_memory_episodic")
        .select("summary,event_kind,subject_kind,subject_id")
        .eq("brand_id", brand_id)
        .gte("occurred_at", cutoff)
        .limit(50)
    )
    if session_id:
        # Best effort: filter summaries mentioning the session_id token
        q = q.ilike("summary", f"%{session_id}%")

    rows = q.execute().data or []
    return [
        {
            "text": row["summary"],
            "source_kind": row.get("subject_kind") or row.get("event_kind") or "episodic",
            "source_id": row.get("subject_id"),
        }
        for row in rows
        if row.get("summary")
    ]


async def _process_source(
    src: dict,
    brand_id: str,
    report: ConsolidationReport,
) -> None:
    """Extract, verify, dedup, and write facts from a single source text."""
    try:
        candidates = await extract_facts_from_text(
            text=src["text"],
            brand_id=brand_id,
            source_kind=src.get("source_kind", "text"),
            source_id=src.get("source_id"),
        )
    except Exception as e:
        logger.error("consolidation._process_source extract failed: %s", e)
        report.errors.append(str(e))
        return

    for cand in candidates:
        statement = cand["statement"]

        # Verify
        vr = verify(statement)
        if not vr.passed:
            report.facts_rejected_verify.append(statement)
            logger.debug("consolidation: VERIFY FAIL %s | %s", statement[:60], vr.failures)
            continue

        # Dedup: check against existing semantic memories
        is_dup = await _is_duplicate(brand_id, statement, cand.get("kind"))
        if is_dup:
            report.facts_rejected_dedup.append(statement)
            logger.debug("consolidation: DEDUP skip %s", statement[:60])
            continue

        # Write
        try:
            await sem_store.insert_fact(
                brand_id=brand_id,
                kind=cand.get("kind", "brand_fact"),
                statement=statement,
                tier=cand.get("tier", "standard"),
                importance=float(cand.get("importance", 0.5)),
                source_kind=cand.get("source_kind"),
                source_id=cand.get("source_id"),
            )
            report.facts_added.append(statement)
        except Exception as e:
            logger.error("consolidation: insert failed for '%s': %s", statement[:60], e)
            report.errors.append(str(e))


async def _is_duplicate(brand_id: str, statement: str, kind: str | None) -> bool:
    """Return True if a very similar fact already exists in memory_semantic."""
    try:
        hits = await sem_store.recall(brand_id, query=statement, kind=kind, k=1)  # type: ignore[arg-type]
        if hits and hits[0].get("similarity", 0) >= _DEDUP_SIM_THRESHOLD:
            return True
    except Exception:
        pass
    return False


async def _send_consolidation_alert(report: ConsolidationReport) -> None:
    """Emit consolidation event — never fails the main pipeline."""
    try:
        await emit_event(
            event_type="memory_consolidation",
            title="Memory consolidation completed",
            severity="info",
            brand_id=report.brand_id,
            detail={"summary": report.telegram_summary()},
        )
    except Exception as e:
        logger.warning("consolidation: notification failed: %s", e)


async def _log_consolidation_event(report: ConsolidationReport) -> None:
    """Write a memory_events row for audit / episodic feed."""
    try:
        db = get_db()
        db.table("memory_events").insert(
            {
                "brand_id": report.brand_id,
                "event_kind": "memory_consolidation",
                "subject_kind": "brand",
                "subject_id": None,
                "summary": (
                    f"Consolidation: +{len(report.facts_added)} added, "
                    f"{len(report.facts_rejected_verify)} verify-rejected, "
                    f"{len(report.facts_rejected_dedup)} dedup-skipped"
                ),
                "payload": {
                    "session_id": report.session_id,
                    "added": len(report.facts_added),
                    "rejected_verify": len(report.facts_rejected_verify),
                    "rejected_dedup": len(report.facts_rejected_dedup),
                    "superseded": len(report.facts_superseded),
                    "errors": report.errors[:5],
                    "duration_s": report.duration_s,
                },
            }
        ).execute()
    except Exception as e:
        logger.warning("consolidation: event log failed: %s", e)
