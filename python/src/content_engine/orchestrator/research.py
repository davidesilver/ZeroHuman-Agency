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

    # Update each item with its embedding
    for item_id, embedding in zip(inserted_ids, embeddings):
        if any(v != 0.0 for v in embedding):  # skip zero embeddings
            try:
                db.table("research_items").update({
                    "embedding": embedding,
                }).eq("id", item_id).execute()
            except Exception as e:
                logger.warning("Failed to update embedding for item %s: %s", item_id, e)

    # Run semantic dedup: for each new item, check if it's a near-duplicate of older items
    archived = 0
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
                # Filter out self-matches
                real_dupes = [d for d in dupes.data if d["id"] != item_id]
                if real_dupes:
                    logger.info(
                        "Item %s is semantic duplicate of %s (similarity: %.2f)",
                        item_id, real_dupes[0]["id"], real_dupes[0]["similarity"],
                    )
                    db.table("research_items").update({
                        "status": "archived",
                        "metadata": {
                            "semantic_duplicate_of": real_dupes[0]["id"],
                            "similarity": real_dupes[0]["similarity"],
                        },
                    }).eq("id", item_id).execute()
                    archived += 1
        except Exception as e:
            logger.warning("Semantic dedup check failed for item %s: %s", item_id, e)

    if archived:
        logger.info("Archived %d semantic duplicates (threshold: %.2f)", archived, threshold)
    return archived


async def run_research(brand_id: str, request: TriggerRequest) -> ResearchRunResult:
    db = get_db()
    start = time.monotonic()

    # Check for running research
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

    # Create run record
    run_row = (
        db.table("research_runs")
        .insert({"brand_id": brand_id, "status": "running"})
        .execute()
    )
    run_id = run_row.data[0]["id"]

    # Load brand config
    brand = db.table("brands").select("*").eq("id", brand_id).single().execute()
    brand_data = brand.data

    retriever_config = {
        "topics": brand_data.get("topics") or [],
        "founder_principles": (brand_data.get("scoring_weights") or {}).get("founder_principles", []),
        "trusted_authors": [],
        "feeds": _build_feeds(brand_data),
        "youtube_channels": [],
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

    return ResearchRunResult(
        run_id=run_id,
        status=RunStatus.COMPLETED,
        total_items_found=total_found,
        items_after_dedup=final_count,
        retriever_stats=retriever_stats,
        duration_seconds=round(elapsed, 2),
    )


def _build_feeds(brand_data: dict) -> list[dict]:
    rss = brand_data.get("rss_sources") or []
    if isinstance(rss, list):
        return rss
    return []
