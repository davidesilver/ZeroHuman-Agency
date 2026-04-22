"""Fact extractor — uses claude-haiku-3-5 via OpenRouter for cheap extraction.

Given a free-text source (brand document, call transcript, web page body),
returns a structured list of candidate facts suitable for memory_semantic.

Haiku is ~10× cheaper than Sonnet for this extraction pass — it doesn't need
deep reasoning, just reliable JSON output.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from ...utils.llm_client import call_llm

logger = logging.getLogger(__name__)

# Haiku via OpenRouter — cheapest capable model for structured extraction
_HAIKU_MODEL = "anthropic/claude-haiku-3-5"

_SYSTEM_PROMPT = """\
You are a brand memory extractor.  Your task is to read source text about a brand
and extract structured facts suitable for long-term memory storage.

Output ONLY a valid JSON array.  Each element must be an object with:
  - "statement": string — a single, self-contained factual sentence (max 80 words)
  - "kind": one of ["tone_rule","principle","gold_example","discard_example","brand_fact","audience_insight"]
  - "importance": float 0.0–1.0 (how critical is this fact for the brand identity)
  - "tier": one of ["core","persistent","standard","transient"]

Rules:
- Each statement must be a complete sentence with a clear subject and verb.
- Do NOT include vague generalities like "The brand cares about quality."
- DO include specific rules, examples, named attributes, and verifiable claims.
- Maximum 20 facts per extraction.
- If the source text contains nothing useful, return an empty array [].

Respond with ONLY the JSON array — no markdown fences, no explanation.
"""


async def extract_facts_from_text(
    text: str,
    brand_id: str,
    source_kind: str = "text",
    source_id: str | None = None,
) -> list[dict[str, Any]]:
    """Extract structured facts from free-text using Haiku.

    Returns a list of dicts ready to be passed to memory_semantic.insert_fact().
    Each dict includes: statement, kind, importance, tier, source_kind, source_id.
    """
    # Truncate to keep cost bounded (~8k chars ≈ 2k tokens for Haiku)
    safe_text = text[:8000]
    prompt = f"Extract brand memory facts from this text:\n\n{safe_text}"

    try:
        resp = await call_llm(
            prompt=prompt,
            brand_id=brand_id,
            context="memory_extraction",
            action="extract_facts",
            system_prompt=_SYSTEM_PROMPT,
            task_type="fact_check",
            temperature=0.2,
        )
    except Exception as e:
        logger.error("extractor: LLM call failed: %s", e)
        return []

    raw = resp.content.strip()

    # Strip accidental markdown code fences if present
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(
            line for line in lines if not line.startswith("```")
        ).strip()

    try:
        facts: list[dict[str, Any]] = json.loads(raw)
        if not isinstance(facts, list):
            raise ValueError("expected JSON array")
    except Exception as e:
        logger.warning("extractor: JSON parse failed (%s); raw=%s", e, raw[:200])
        return []

    # Normalise / attach source provenance
    result = []
    for item in facts[:20]:  # hard cap
        if not isinstance(item, dict) or not item.get("statement"):
            continue
        result.append(
            {
                "statement": str(item.get("statement", "")).strip(),
                "kind": item.get("kind", "brand_fact"),
                "importance": float(item.get("importance", 0.5)),
                "tier": item.get("tier", "standard"),
                "source_kind": source_kind,
                "source_id": source_id,
            }
        )

    logger.info(
        "extractor: extracted %d facts from %d chars (brand=%s)",
        len(result), len(safe_text), brand_id,
    )
    return result
