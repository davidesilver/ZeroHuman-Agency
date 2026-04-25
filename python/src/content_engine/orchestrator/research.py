"""Research Orchestrator — runs all retrievers in parallel, deduplicates, saves to DB."""

from __future__ import annotations

import asyncio
import logging
import time
from urllib.parse import urlparse, urlencode, parse_qs

from ..db import get_db
from ..models import (
    ResearchItemCreate,
    ResearchRunResult,
    RetrieverType,
    RunStatus,
    TriggerRequest,
)
from ..retrievers.base import BaseRetriever
from ..retrievers.rss import RSSRetriever
from ..retrievers.serper import SemanticRetriever, KeywordRetriever, PractitionerRetriever
from ..retrievers.youtube import YouTubeRetriever

logger = logging.getLogger("content_engine.research")

# H-09: Per-brand locks to prevent concurrent research pipelines.
# Without this, two simultaneous trigger requests both pass the
# "is a run already active?" DB check before either can create the record.
_research_locks: dict[str, asyncio.Lock] = {}
_locks_dict_lock = asyncio.Lock()  # protects _research_locks dict itself


async def _get_research_lock(brand_id: str) -> asyncio.Lock:
    """Return a brand-scoped asyncio.Lock, creating it lazily."""
    async with _locks_dict_lock:
        if brand_id not in _research_locks:
            _research_locks[brand_id] = asyncio.Lock()
        return _research_locks[brand_id]


def _normalize_url(url: str) -> str:
    parsed = urlparse(url)
    # Remove tracking params
    drop = {"utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term", "ref", "source"}
    qs = parse_qs(parsed.query)
    filtered = {k: v for k, v in qs.items() if k.lower() not in drop}
    clean_query = urlencode(filtered, doseq=True) if filtered else ""
    host = parsed.netloc.removeprefix("www.")
    path = parsed.path.rstrip("/")
    return f"{parsed.scheme}://{host}{path}{'?' + clean_query if clean_query else ''}"


def _deduplicate(items: list[ResearchItemCreate], threshold: float = 0.85) -> list[ResearchItemCreate]:
    """URL-based dedup. Semantic dedup runs post-insert via embeddings."""
    seen: dict[str, ResearchItemCreate] = {}
    for item in items:
        norm = _normalize_url(item.url)
        if norm not in seen:
            seen[norm] = item
    return list(seen.values())


RETRIEVER_MAP: dict[RetrieverType, type[BaseRetriever]] = {
    RetrieverType.TRUSTED_SOURCE: RSSRetriever,
    RetrieverType.SEMANTIC: SemanticRetriever,
    RetrieverType.KEYWORD: KeywordRetriever,
    RetrieverType.PRACTITIONER: PractitionerRetriever,
    RetrieverType.TREND: YouTubeRetriever,
}


async def _embed_and_dedup(
    db,
    brand_id: str,
    inserted_ids: list[str],
    items: list[ResearchItemCreate],
    threshold: float,
) -> int:
    """Generate embeddings for new items and archive semantic duplicates.

    Returns the number of items archived as semantic duplicates.
    """
    from ..config import settings
    from ..services.embeddings import generate_embeddings_batch

    if not settings.openrouter_api_key:
        logger.warning("Skipping semantic dedup — no OPENROUTER_API_KEY configured")
        return 0

    # Build text for embedding: title + summary
    texts = [f"{item.title}. {item.summary}" for item in items]

    try:
        embeddings = await generate_embeddings_batch(texts, brand_id=brand_id)
    except Exception as e:
        logger.error("Embedding generation failed, skipping semantic dedup: %s", e)
        return 0

    # Batched embedding writes.  The previous per-item .update() chain was the
    # single biggest source of latency in the research pipeline (one HTTP
    # round-trip per item × N items per run).  upsert() on the primary key
    # collapses the entire batch into one request and re-uses the connection.
    embedding_rows = [
        {"id": item_id, "embedding": embedding}
        for item_id, embedding in zip(inserted_ids, embeddings)
        if any(v != 0.0 for v in embedding)
    ]
    if embedding_rows:
        try:
            (
                db.table("research_items")
                .upsert(embedding_rows, on_conflict="id")
                .execute()
            )
        except Exception as e:
            logger.warning(
                "Batched embedding upsert failed (n=%d): %s — falling back to per-row updates",
                len(embedding_rows), e,
            )
            for row in embedding_rows:
                try:
                    db.table("research_items").update(
                        {"embedding": row["embedding"]}
                    ).eq("id", row["id"]).execute()
                except Exception as inner:
                    logger.warning(
                        "Failed to update embedding for item %s: %s", row["id"], inner
                    )

    # Run semantic dedup: for each new item, check if it's a near-duplicate of
    # older items.  The RPC call is unavoidably one-per-item (it's a vector
    # search), but the writes for archived duplicates are collected and flushed
    # in a single upsert at the end.
    archive_rows: list[dict] = []
    for item_id, embedding in zip(inserted_ids, embeddings):
        if not any(v != 0.0 for v in embedding):
            continue
        try:
            dupes = db.rpc("find_semantic_duplicates", {
                "p_brand_id": brand_id,
                "p_embedding": embedding,
                "p_threshold": threshold,
                "p_limit": 3,
            }).execute()

            if dupes.data:
                real_dupes = [d for d in dupes.data if d["id"] != item_id]
                if real_dupes:
                    logger.info(
                        "Item %s is semantic duplicate of %s (similarity: %.2f)",
                        item_id, real_dupes[0]["id"], real_dupes[0]["similarity"],
                    )
                    archive_rows.append({
                        "id": item_id,
                        "status": "archived",
                        "metadata": {
                            "semantic_duplicate_of": real_dupes[0]["id"],
                            "similarity": real_dupes[0]["similarity"],
                        },
                    })
        except Exception as e:
            logger.warning("Semantic dedup check failed for item %s: %s", item_id, e)

    archived = len(archive_rows)
    if archive_rows:
        try:
            (
                db.table("research_items")
                .upsert(archive_rows, on_conflict="id")
                .execute()
            )
        except Exception as e:
            logger.warning(
                "Batched dedup archive upsert failed (n=%d): %s — falling back to per-row updates",
                archived, e,
            )
            for row in archive_rows:
                try:
                    db.table("research_items").update(
                        {"status": row["status"], "metadata": row["metadata"]}
                    ).eq("id", row["id"]).execute()
                except Exception as inner:
                    logger.warning("Failed to archive duplicate %s: %s", row["id"], inner)

    if archived:
        logger.info("Archived %d semantic duplicates (threshold: %.2f)", archived, threshold)
    return archived


async def run_research(brand_id: str, request: TriggerRequest) -> ResearchRunResult:
    db = get_db()
    start = time.monotonic()

    # H-09: Acquire per-brand lock to prevent concurrent pipeline race conditions.
    # Two simultaneous requests cannot both pass the DB check and start duplicates.
    brand_lock = await _get_research_lock(brand_id)
    async with brand_lock:
        # Check for running research (now safe from TOCTOU within same process)
        if not request.force:
            existing = (
                db.table("research_runs")
                .select("id")
                .eq("brand_id", brand_id)
                .eq("status", "running")
                .execute()
            )
            if existing.data:
                return ResearchRunResult(
                    run_id=existing.data[0]["id"],
                    status=RunStatus.RUNNING,
                )

        # Create run record — done inside lock so no second request sneaks through
        run_row = (
            db.table("research_runs")
            .insert({"brand_id": brand_id, "status": "running"})
            .execute()
        )
    # Lock released here — the run record exists, subsequent triggers will see it
    run_id = run_row.data[0]["id"]

    # Load brand config
    brand = db.table("brands").select("*").eq("id", brand_id).single().execute()
    brand_data = brand.data

    retriever_config = {
        "topics": brand_data.get("topics") or [],
        "founder_principles": (brand_data.get("scoring_weights") or {}).get("founder_principles", []),
        "trusted_authors": [],
        "feeds": _build_feeds(brand_data),
        "youtube_channels": (brand_data.get("research_sources") or {}).get("youtube_channels") or [],
        "gmail_label": (brand_data.get("research_sources") or {}).get("gmail_label") or "newsletters",
        "x_accounts": (brand_data.get("research_sources") or {}).get("x_accounts") or [],
        "exclude_domains": ["reddit.com", "quora.com"],
        "language": "it",
        "max_items": request.max_items_per_retriever,
    }

    # Select which retrievers to run
    retriever_types = request.retrievers or list(RETRIEVER_MAP.keys())

    # Run retrievers in parallel
    retrievers = [
        RETRIEVER_MAP[rt](brand_id, run_id)
        for rt in retriever_types
        if rt in RETRIEVER_MAP
    ]
    # P6.7: Gmail and X retrievers (string-keyed, not in RetrieverType enum yet)
    from ..retrievers.gmail import GmailRetriever
    from ..retrievers.x import XRetriever
    extra_retrievers = [
        GmailRetriever(brand_id, run_id),
        XRetriever(brand_id, run_id),
    ]
    retrievers.extend(extra_retrievers)
    results = await asyncio.gather(
        *(r.execute(retriever_config) for r in retrievers),
        return_exceptions=True,
    )

    # Collect all items + stats
    all_items: list[ResearchItemCreate] = []
    retriever_stats: dict[str, dict] = {}
    for res in results:
        if isinstance(res, Exception):
            continue
        all_items.extend(res.items)
        retriever_stats[res.retriever] = {
            "items_found": len(res.items),
            "duration_ms": res.duration_ms,
            "errors": res.errors,
        }

    total_found = len(all_items)

    # URL-based deduplication (fast, pre-insert)
    deduped = _deduplicate(all_items, request.dedup_threshold)

    # Save to database (columns must match DB schema)
    inserted_ids: list[str] = []
    if deduped:
        rows = [
            {
                "brand_id": item.brand_id,
                "run_id": item.run_id,
                "retriever_type": item.retriever,
                "source_type": item.source_type,
                "title": item.title,
                "url": item.url,
                "source_name": item.source_name,
                "summary": item.summary,
                "metadata": item.metadata,
                "status": "new",
            }
            for item in deduped
        ]
        insert_result = db.table("research_items").insert(rows).execute()
        inserted_ids = [r["id"] for r in insert_result.data]

    # Content enrichment: replace short snippets with full article text
    if inserted_ids:
        try:
            from ..services.content_enrichment import enrich_research_items
            enrichment_results = await enrich_research_items(inserted_ids, max_concurrent=3)
            enriched_count = sum(1 for v in enrichment_results.values() if v)
            logger.info("Enriched %d/%d items with full text", enriched_count, len(inserted_ids))
        except Exception as e:
            logger.warning("Content enrichment step failed (non-blocking): %s", e)

    # Semantic deduplication (post-insert, uses embeddings)
    semantic_archived = 0
    if inserted_ids:
        semantic_archived = await _embed_and_dedup(
            db, brand_id, inserted_ids, deduped, request.dedup_threshold,
        )

    elapsed = time.monotonic() - start
    final_count = len(deduped) - semantic_archived

    # Update run (columns: status, completed_at, items_found, sources_scanned, retriever_stats)
    db.table("research_runs").update({
        "status": "completed",
        "completed_at": "now()",
        "items_found": final_count,
        "sources_scanned": total_found,
        "retriever_stats": {
            **retriever_stats,
            "semantic_dedup": {"archived": semantic_archived},
        },
    }).eq("id", run_id).execute()

    # P6.7: Log research_harvested event to memory_events
    try:
        from ..memory import events as _memory_events
        await _memory_events.log(
            brand_id=brand_id,
            kind="research_harvested",
            summary=(
                f"Research run {run_id}: {final_count} items harvested "
                f"({semantic_archived} semantic dupes removed) in {elapsed:.1f}s"
            ),
            subject_kind="research_run",
            subject_id=run_id,
            payload={
                "items_found": total_found,
                "items_after_dedup": final_count,
                "semantic_archived": semantic_archived,
                "retriever_stats": retriever_stats,
            },
        )
    except Exception as _e:
        logger.warning("Failed to log research_harvested event: %s", _e)

    return ResearchRunResult(
        run_id=run_id,
        status=RunStatus.COMPLETED,
        total_items_found=total_found,
        items_after_dedup=final_count,
        retriever_stats=retriever_stats,
        duration_seconds=round(elapsed, 2),
    )


def _build_feeds(brand_data: dict) -> list[dict]:
    # Legacy: brands.rss_sources (flat list of URLs or dicts)
    legacy = brand_data.get("rss_sources") or []
    # New: brands.research_sources.rss_feeds (list of {url, name} dicts)
    new_feeds = (brand_data.get("research_sources") or {}).get("rss_feeds") or []
    result = []
    seen = set()
    for item in (legacy + new_feeds):
        if isinstance(item, str):
            item = {"url": item, "name": item}
        url = item.get("url", "")
        if url and url not in seen:
            seen.add(url)
            result.append(item)
    return result
