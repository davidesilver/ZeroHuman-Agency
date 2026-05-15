"""LLM provider API routes (Phase 4).

GET /llm/providers         — list registered providers
GET /llm/providers/metrics — aggregated telemetry (last 24h / 7d / 30d)
"""

from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request

from ..services.llm.registrar import list_providers
from ..db import get_db

_logger = logging.getLogger("content_engine.llm_providers")

router = APIRouter(prefix="/llm", tags=["llm-providers"])


def _brand_id(request: Request) -> str:
    brand_id = getattr(request.state, "brand_id", None)
    if not brand_id:
        raise HTTPException(401, "Not authenticated")
    return brand_id


@router.get("/providers")
async def get_providers(request: Request):
    """List all registered LLM providers."""
    _brand_id(request)  # auth check
    return list_providers()


@router.get("/providers/metrics")
async def get_provider_metrics(
    request: Request,
    window: Literal["24h", "7d", "30d"] = Query("7d"),
):
    """Return aggregated provider metrics for the active brand.

    Returns per-provider stats: total_calls, avg_latency_ms, total_cost_usd,
    avg_cost_per_1k_tokens, error_rate.
    """
    brand_id = _brand_id(request)
    interval = {"24h": "1 day", "7d": "7 days", "30d": "30 days"}[window]

    try:
        result = get_db().rpc(
            "llm_provider_stats",
            {"p_brand_id": brand_id, "p_interval": interval},
        ).execute()
        return result.data or []
    except Exception:
        # RPC may not exist yet — fall back to direct query
        rows = (
            get_db()
            .from_("llm_provider_metrics")
            .select("provider, model, latency_ms, cost_usd, is_fallback, error, prompt_tokens, completion_tokens")
            .eq("brand_id", brand_id)
            .gte("ts", f"now() - interval '{interval}'")
            .execute()
        )
        if not rows.data:
            return []

        # Aggregate in Python
        from collections import defaultdict
        stats: dict[str, dict] = defaultdict(lambda: {
            "total_calls": 0,
            "error_calls": 0,
            "total_latency_ms": 0,
            "total_cost_usd": 0.0,
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
        })
        for row in rows.data:
            p = row["provider"]
            stats[p]["total_calls"] += 1
            if row.get("error"):
                stats[p]["error_calls"] += 1
            if row.get("latency_ms"):
                stats[p]["total_latency_ms"] += row["latency_ms"]
            if row.get("cost_usd"):
                stats[p]["total_cost_usd"] += float(row["cost_usd"])
            stats[p]["total_prompt_tokens"] += row.get("prompt_tokens", 0) or 0
            stats[p]["total_completion_tokens"] += row.get("completion_tokens", 0) or 0

        result = []
        for provider, s in stats.items():
            total = s["total_calls"]
            total_tokens = s["total_prompt_tokens"] + s["total_completion_tokens"]
            result.append({
                "provider": provider,
                "window": window,
                "total_calls": total,
                "error_rate": round(s["error_calls"] / total, 4) if total else 0,
                "avg_latency_ms": round(s["total_latency_ms"] / total) if total else None,
                "total_cost_usd": round(s["total_cost_usd"], 6),
                "cost_per_1k_tokens": round(
                    s["total_cost_usd"] / (total_tokens / 1000), 6
                ) if total_tokens else None,
            })
        return result
