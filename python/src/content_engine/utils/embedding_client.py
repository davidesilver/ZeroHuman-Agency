"""Embedding Client for semantic deduplication using OpenAI."""

from __future__ import annotations

import logging

import httpx

from ..config import settings
from .cost_tracker import track_cost

logger = logging.getLogger(__name__)

async def generate_embedding(text: str, brand_id: str) -> list[float]:
    """
    Generate an embedding vector for standard semantic similarity operations.
    Defaults to text-embedding-3-small (1536 dim).
    """
    if not settings.openai_api_key:
        logger.warning("No openai_api_key set. Skipping embedding generation.")
        return []

    # Clean the text roughly to avoid excessively large embedding calls 
    # OpenAI accepts up to 8191 tokens for text-embedding-3-small, but let's be safe
    safe_text = text[:8000].replace("\n", " ")

    url = "https://api.openai.com/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "input": safe_text,
        "model": "text-embedding-3-small"
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            
            # Extract embedding
            embedding = data["data"][0]["embedding"]
            
            # Track cost (openai text-embedding-3-small is very cheap: ~$0.02 / 1M tokens)
            prompt_tokens = data.get("usage", {}).get("prompt_tokens", 0)
            await track_cost(brand_id, "semantic_dedup", "text-embedding-3-small", "embedding", prompt_tokens, 0)
            
            return embedding
    except Exception as e:
        logger.error(f"Failed to generate embedding: {e}")
        return []
