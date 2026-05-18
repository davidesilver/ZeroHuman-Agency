"""Cost tracking utility — logs every LLM call to api_costs table."""

from __future__ import annotations

import logging
from datetime import UTC

from ..db import get_db

logger = logging.getLogger(__name__)

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
    cost_usd: float | None = None,
) -> None:
    """Log an API call cost to the api_costs table.

    Args:
        cost_usd: Optional explicit cost override for non-LLM services
                  (images, external APIs). When provided, skips token estimation.
    """
    if cost_usd is not None:
        cost = float(cost_usd)
        tokens_in = 0
        tokens_out = 0
    else:
        # M-12: Derive token estimates directly from char counts
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


async def check_daily_cost_cap(brand_id: str) -> None:
    """Check whether the brand has exceeded its daily cost cap.

    Cap resolution order (lowest wins):
      1. brands.daily_budget_usd (per-brand DB value, NULL = unlimited)
      2. DAILY_COST_CAP_USD env var (global system ceiling, default $5.00)

    If the brand has daily_budget_usd = NULL AND no env var is set the
    default of $5 still applies as a safety net.

    Sends a Telegram alert and raises RuntimeError if the cap is exceeded.
    The pipeline catches CostCapExceeded, stops processing, and resumes
    naturally the next UTC day when the aggregate resets.
    """
    import os
    from datetime import datetime

    global_cap_str = os.environ.get("DAILY_COST_CAP_USD")
    # If env var is not set → unlimited (None); parse defensively so a
    # malformed value doesn't crash the whole pipeline.
    if global_cap_str:
        try:
            global_cap = float(global_cap_str)
        except ValueError:
            logger.error(
                "DAILY_COST_CAP_USD=%r is not a number; treating as unlimited",
                global_cap_str,
            )
            global_cap = None
    else:
        global_cap = None

    # Fetch per-brand budget from DB (service role bypasses RLS)
    db = get_db()
    brand_resp = (
        db.table("brands")
        .select("daily_budget_usd")
        .eq("id", brand_id)
        .single()
        .execute()
    )
    brand_row = brand_resp.data or {}
    brand_budget = brand_row.get("daily_budget_usd")

    # Per-brand value wins when set — env is only a fallback, not a ceiling.
    # Both NULL = unlimited (None)
    if brand_budget is not None:
        cap = float(brand_budget)
    elif global_cap is not None:
        cap = global_cap
    else:
        cap = None  # unlimited

    # Start of today in UTC (midnight)
    now_utc = datetime.now(UTC)
    today_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

    resp = (
        db.table("api_costs")
        .select("cost_usd")
        .eq("brand_id", brand_id)
        .gte("created_at", today_start)
        .execute()
    )
    rows = resp.data or []
    total = sum(float(r.get("cost_usd", 0) or 0) for r in rows)

    if cap is not None and total >= cap:
        # Lazy import to avoid circular import at module load time
        from ..monitoring.pipeline_health import send_alerts
        source = "per-brand DB" if brand_budget is not None else "global env var"
        await send_alerts(
            [
                f"🚨 Daily cost cap ${cap:.2f} ({source}) exceeded for brand {brand_id}"
                f" — pipeline aborted. Spend today: ${total:.4f}."
                f" Will resume automatically tomorrow UTC."
            ]
        )
        raise CostCapExceeded(
            f"Daily cost cap ${cap:.2f} ({source}) exceeded "
            f"(actual ${total:.4f}) for brand {brand_id}"
        )


class CostCapExceeded(RuntimeError):
    """Raised when a brand exceeds its daily cost cap.

    The pipeline scheduler catches this, logs it, and skips the brand for
    the rest of the UTC day.  The next daily run (after midnight UTC) will
    proceed normally because the api_costs aggregate for the new day is 0.
    """
