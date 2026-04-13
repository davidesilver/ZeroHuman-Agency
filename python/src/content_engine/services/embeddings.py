"""Embedding service — generates text embeddings for semantic similarity.

Uses OpenAI text-embedding-3-small (1536 dimensions) via:
1. Anthropic (if available, via OpenRouter for embeddings)
2. OpenRouter (direct)

The model matches the vector(1536) column in research_items.
"""

from __future__ import annotations

import logging
from typing import Sequence

import httpx

from ..config import settings
from ..utils.cost_tracker import track_cost

logger = logging.getLogger("content_engine.embeddings")

EMBEDDING_MODEL = "openai/text-embedding-3-small"
EMBEDDING_DIM = 1536


async def generate_embedding(text: str, *, brand_id: str = "") -> list[float]:
    """Generate a 1536-dim embedding for a single text.

    Args:
        text: The text to embed (title + summary concatenated).
        brand_id: For cost tracking.

    Returns:
        List of 1536 floats.

    Raises:
        RuntimeError: If no API key configured.
        httpx.HTTPStatusError: If the API call fails.
    """
    if not text.strip():
        return [0.0] * EMBEDDING_DIM

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://openrouter.ai/api/v1/embeddings",
            json={
                "model": EMBEDDING_MODEL,
                "input": text[:8000],  # text-embedding-3-small max ~8191 tokens
            },
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    embedding = data["data"][0]["embedding"]

    if brand_id:
        await track_cost(
            brand_id, "embedding", EMBEDDING_MODEL, "embed_text",
            len(text), 0,
        )

    return embedding


async def generate_embeddings_batch(
    texts: Sequence[str],
    *,
    brand_id: str = "",
) -> list[list[float]]:
    """Generate embeddings for multiple texts in a single API call.

    Args:
        texts: List of texts to embed.
        brand_id: For cost tracking.

    Returns:
        List of embeddings (same order as input).
    """
    if not texts:
        return []

    # Filter empty texts, keep track of indices
    non_empty = [(i, t[:8000]) for i, t in enumerate(texts) if t.strip()]

    if not non_empty:
        return [[0.0] * EMBEDDING_DIM for _ in texts]

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://openrouter.ai/api/v1/embeddings",
            json={
                "model": EMBEDDING_MODEL,
                "input": [t for _, t in non_empty],
            },
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    # Map results back to original indices
    results: list[list[float]] = [[0.0] * EMBEDDING_DIM for _ in texts]
    for item in data["data"]:
        orig_idx = non_empty[item["index"]][0]
        results[orig_idx] = item["embedding"]

    if brand_id:
        total_chars = sum(len(t) for _, t in non_empty)
        await track_cost(
            brand_id, "embedding", EMBEDDING_MODEL, "embed_batch",
            total_chars, 0,
        )

    logger.info("Generated %d embeddings (%d non-empty)", len(texts), len(non_empty))
    return results
