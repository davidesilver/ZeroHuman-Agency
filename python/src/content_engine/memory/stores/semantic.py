"""Semantic memory store — facts, rules, examples with pgvector retrieval.

All writes go through `insert_fact()`.  Reads use the `memory_search`
RPC (temporal-weighted composite score: 0.60·cosine + 0.25·decay + 0.15·importance).
Direct table reads are provided for management UIs.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from ...db import get_db
from ...utils.embedding_client import generate_embedding

logger = logging.getLogger(__name__)

MemoryKind = Literal[
    "tone_rule",
    "principle",
    "gold_example",
    "discard_example",
    "brand_fact",
    "audience_insight",
]
MemoryTier = Literal["core", "persistent", "standard", "transient"]

_TTL_DAYS: dict[str, int | None] = {
    "core": None,        # never expires
    "persistent": 365,
    "standard": 90,
    "transient": 7,
}


def _expires_at(tier: MemoryTier) -> str | None:
    from datetime import timedelta

    days = _TTL_DAYS.get(tier)
    if days is None:
        return None
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


async def insert_fact(
    brand_id: str,
    kind: MemoryKind,
    statement: str,
    tier: MemoryTier = "standard",
    importance: float = 0.50,
    source_kind: str | None = None,
    source_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    supersedes_id: str | None = None,
) -> str:
    """Insert a new semantic memory fact; returns the new row id."""
    embedding = await generate_embedding(statement, brand_id)

    row: dict[str, Any] = {
        "id": str(uuid4()),
        "brand_id": brand_id,
        "kind": kind,
        "statement": statement,
        "tier": tier,
        "importance": importance,
        "asserted_at": datetime.now(timezone.utc).isoformat(),
        "metadata": metadata or {},
    }
    if embedding:
        row["embedding"] = embedding
    if source_kind:
        row["source_kind"] = source_kind
    if source_id:
        row["source_id"] = source_id
    exp = _expires_at(tier)
    if exp:
        row["expires_at"] = exp
    if supersedes_id:
        row["supersedes_id"] = supersedes_id

    db = get_db()
    db.table("memory_semantic").insert(row).execute()
    logger.info(
        "memory_semantic.insert brand=%s kind=%s tier=%s id=%s",
        brand_id, kind, tier, row["id"],
    )
    return row["id"]


async def update_fact(
    fact_id: str,
    statement: str | None = None,
    tier: MemoryTier | None = None,
    importance: float | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Partial update of a semantic memory fact.  Re-embeds if statement changes."""
    patch: dict[str, Any] = {}

    if statement is not None:
        patch["statement"] = statement
        # Re-generate embedding lazily — we don't have brand_id here so we
        # use an empty brand placeholder for cost tracking.
        emb = await generate_embedding(statement, "system")
        if emb:
            patch["embedding"] = emb

    if tier is not None:
        patch["tier"] = tier
        exp = _expires_at(tier)
        patch["expires_at"] = exp  # None → DB NULL (no expiry)

    if importance is not None:
        patch["importance"] = importance

    if metadata is not None:
        patch["metadata"] = metadata

    if not patch:
        return

    db = get_db()
    db.table("memory_semantic").update(patch).eq("id", fact_id).execute()
    logger.info("memory_semantic.update id=%s fields=%s", fact_id, list(patch))


async def delete_fact(fact_id: str) -> None:
    """Hard-delete a semantic memory row (use sparingly; prefer supersede)."""
    db = get_db()
    db.table("memory_semantic").delete().eq("id", fact_id).execute()
    logger.info("memory_semantic.delete id=%s", fact_id)


async def list_facts(
    brand_id: str,
    kind: MemoryKind | None = None,
    tier: MemoryTier | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Return raw rows for the Memory Inspector UI."""
    db = get_db()
    q = (
        db.table("memory_semantic")
        .select(
            "id,kind,statement,tier,importance,asserted_at,expires_at,"
            "retrieval_hits,last_retrieved,source_kind,source_id,supersedes_id,metadata"
        )
        .eq("brand_id", brand_id)
        .or_("expires_at.is.null,expires_at.gt." + datetime.now(timezone.utc).isoformat())
        .order("asserted_at", desc=True)
        .limit(limit)
    )
    if kind:
        q = q.eq("kind", kind)
    if tier:
        q = q.eq("tier", tier)
    return q.execute().data or []


async def recall(
    brand_id: str,
    query: str,
    kind: MemoryKind | None = None,
    k: int = 5,
) -> list[dict[str, Any]]:
    """Retrieve top-k facts using the temporal-weighted composite score.

    Delegates to the `memory_search` SQL function so scoring is DB-side.
    Returns list of dicts with keys: id, statement, kind, tier, similarity,
    age_days, score.
    """
    embedding = await generate_embedding(query, brand_id)
    if not embedding:
        logger.warning("memory_semantic.recall: no embedding — returning empty")
        return []

    db = get_db()
    resp = db.rpc(
        "memory_search",
        {
            "p_brand_id": brand_id,
            "p_query_embedding": embedding,
            "p_kind": kind,
            "p_limit": k,
        },
    ).execute()
    return resp.data or []
