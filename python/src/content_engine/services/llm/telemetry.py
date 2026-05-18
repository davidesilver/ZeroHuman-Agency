"""LLM call telemetry — writes to llm_provider_metrics (migration 034).

Two entry points:
  record_llm_call()     — fire-and-forget insert from any existing call site
  call_with_telemetry() — async wrapper: calls call_llm() and records the metric
"""

from __future__ import annotations

import logging
import time

from ...db import get_db
from .provider import LLMResult

logger = logging.getLogger("content_engine.llm.telemetry")


def record_llm_call(
    brand_id: str,
    result: LLMResult,
    task_type: str = "general",
) -> None:
    """Insert a telemetry row into llm_provider_metrics.

    Fire-and-forget: errors are logged but not propagated so they never
    affect the caller's happy path.
    """
    try:
        get_db().from_("llm_provider_metrics").insert(
            {
                "brand_id": brand_id,
                "provider": result.provider or "unknown",
                "model": result.model_used or "unknown",
                "task_type": task_type,
                "prompt_tokens": result.prompt_tokens,
                "completion_tokens": result.completion_tokens,
                "latency_ms": result.latency_ms,
                "cost_usd": str(result.cost_usd) if result.cost_usd is not None else None,
                "is_fallback": result.is_fallback,
                "error": result.error,
            }
        ).execute()
    except Exception:
        logger.exception("Failed to record LLM telemetry for brand %s", brand_id)


async def call_with_telemetry(
    prompt: str,
    brand_id: str,
    *,
    system_prompt: str | None = None,
    task_type: str = "creative",
    temperature: float = 0.7,
    context: str = "general",
    action: str = "call_llm",
):
    """Call call_llm() and emit a telemetry row on completion.

    Returns the same LLMResponse as call_llm() for full backward-compatibility.
    """
    from ...utils.llm_client import call_llm

    t0 = time.monotonic()
    resp = await call_llm(
        prompt=prompt,
        brand_id=brand_id,
        context=context,
        action=action,
        system_prompt=system_prompt,
        task_type=task_type,
        temperature=temperature,
    )
    latency_ms = int((time.monotonic() - t0) * 1000)

    record_llm_call(
        brand_id=brand_id,
        result=LLMResult(
            content=resp.content,
            model_used=resp.model_used,
            provider=resp.engine if resp.engine != "unknown" else "openrouter",
            prompt_tokens=resp.tokens_prompt,
            completion_tokens=resp.tokens_completion,
            latency_ms=resp.latency_ms or latency_ms,
            cost_usd=resp.cost_usd,
            is_fallback=resp.used_fallback,
        ),
        task_type=task_type,
    )
    return resp
