"""Research Orchestrator — runs all retrievers in parallel, deduplicates, saves to DB."""

from __future__ import annotations

import asyncio
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
    """URL-based dedup. Semantic dedup (pgvector) will be done post-insert via SQL."""
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

    # Deduplicate
    deduped = _deduplicate(all_items, request.dedup_threshold)

    # Save to database (columns must match DB schema)
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
        db.table("research_items").insert(rows).execute()

    elapsed = time.monotonic() - start

    # Update run (columns: status, completed_at, items_found, sources_scanned, retriever_stats)
    db.table("research_runs").update({
        "status": "completed",
        "completed_at": "now()",
        "items_found": len(deduped),
        "sources_scanned": total_found,
        "retriever_stats": retriever_stats,
    }).eq("id", run_id).execute()

    return ResearchRunResult(
        run_id=run_id,
        status=RunStatus.COMPLETED,
        total_items_found=total_found,
        items_after_dedup=len(deduped),
        retriever_stats=retriever_stats,
        duration_seconds=round(elapsed, 2),
    )


def _build_feeds(brand_data: dict) -> list[dict]:
    rss = brand_data.get("rss_sources") or []
    if isinstance(rss, list):
        return rss
    return []
