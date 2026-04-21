"""Cost tracking utility — logs every LLM call to api_costs table."""

from __future__ import annotations

from ..db import get_db

# Approximate pricing per 1M tokens (input/output) — updated May 2025
MODEL_PRICING = {
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
    "claude-opus-4-20250514": {"input": 15.0, "output": 75.0},
    "anthropic/claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
    "anthropic/claude-opus-4-20250514": {"input": 15.0, "output": 75.0},
}

# Rough approximation: 1 char ≈ 0.25 tokens for English/Italian text
CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    """Rough token estimate from character count."""
    return max(1, len(text) // CHARS_PER_TOKEN)


def estimate_cost(model: str, tokens_input: int, tokens_output: int) -> float:
    """Estimate cost in USD based on model pricing."""
    pricing = MODEL_PRICING.get(model, {"input": 3.0, "output": 15.0})
    cost = (tokens_input * pricing["input"] + tokens_output * pricing["output"]) / 1_000_000
    return round(cost, 6)


class CostTracker:
    """Singleton helper used by llm_client to retrieve per-call cost estimates."""

    async def get_cost_by_model(self, model: str, brand_id: str) -> float:
        """Return estimated USD cost for a single average call on this model.

        This is an in-process estimate (not a DB aggregate) — it gives the
        LLMResponse a non-null cost_usd without an extra round-trip.
        Actual logged costs live in the api_costs table via track_cost().
        """
        # Use the same pricing table as estimate_cost; assume ~1k tokens each
        # direction as a representative single-call value.
        return estimate_cost(model, tokens_input=1000, tokens_output=500)


cost_tracker = CostTracker()


async def track_cost(
    brand_id: str,
    agent_name: str,
    model: str,
    operation: str,
    input_chars: int,
    output_chars: int,
    latency_ms: int | None = None,
) -> None:
    """Log an API call cost to the api_costs table."""
    # M-12: Derive token estimates directly from char counts — do NOT allocate
    # large strings of 'x' * chars just to call len() on them.
    tokens_in = max(1, input_chars // CHARS_PER_TOKEN)
    tokens_out = max(1, output_chars // CHARS_PER_TOKEN)
    cost = estimate_cost(model, tokens_in, tokens_out)

    db = get_db()
    db.table("api_costs").insert({
        "brand_id": brand_id,
        "agent_name": agent_name,
        "model": model,
        "operation": operation,
        "tokens_input": tokens_in,
        "tokens_output": tokens_out,
        "cost_usd": cost,
        "latency_ms": latency_ms,
    }).execute()
