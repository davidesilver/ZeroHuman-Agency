"""OpenClaw LLM provider (Phase 14 — A/B POC).

OpenClaw exposes an OpenAI-compatible API endpoint.
Auth: per-brand API key in brand_integrations (provider='openclaw', key_name='api_key').
Traffic split: controlled by feature flag 'llm_provider_openclaw_share' (0.0 .. 1.0).

Usage:
    from content_engine.services.llm.openclaw import OpenClawProvider
    provider = OpenClawProvider()
    result = provider.complete(request)
"""

from __future__ import annotations

import logging
import os
import random
import time

import httpx

from ..brand_secrets import get_brand_secret
from ..feature_flags import get_feature_flag
from .provider import LLMProvider, LLMRequest, LLMResult

logger = logging.getLogger("content_engine.llm.openclaw")

OPENCLAW_BASE = os.environ.get("OPENCLAW_API_URL", "https://api.openclaw.ai/v1")
OPENCLAW_DEFAULT_MODEL = os.environ.get("OPENCLAW_DEFAULT_MODEL", "openclaw-v1")
OPENCLAW_SHARE_FLAG = "llm_provider_openclaw_share"


class OpenClawProvider(LLMProvider):
    """OpenAI-compatible provider targeting the OpenClaw inference API."""

    @property
    def name(self) -> str:
        return "openclaw"

    def is_available(self, brand_id: str) -> bool:
        """True if the brand has an OpenClaw API key configured."""
        key = get_brand_secret(brand_id, "openclaw", "api_key")
        return bool(key)

    def should_route(self, brand_id: str) -> bool:
        """True if a random roll falls within the configured share (0..1)."""
        try:
            share_raw = get_feature_flag(brand_id, OPENCLAW_SHARE_FLAG, default=False)
            share = float(share_raw) if share_raw is not False else 0.0
        except (ValueError, TypeError):
            share = 0.0
        if share <= 0.0:
            return False
        if share >= 1.0:
            return True
        return random.random() < share

    def complete(self, request: LLMRequest) -> LLMResult:
        api_key = get_brand_secret(request.brand_id, "openclaw", "api_key")
        if not api_key:
            return LLMResult(
                content="",
                model_used="",
                provider=self.name,
                prompt_tokens=0,
                completion_tokens=0,
                error="OpenClaw API key not configured",
            )

        model = request.model or OPENCLAW_DEFAULT_MODEL
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        t0 = time.monotonic()
        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(
                    f"{OPENCLAW_BASE}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": messages,
                        "temperature": request.temperature,
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            latency_ms = int((time.monotonic() - t0) * 1000)
            choice = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})

            # Cost estimate: $0.002 per 1K tokens (placeholder until OpenClaw publishes pricing)
            total_tokens = usage.get("total_tokens", 0)
            cost_usd = round(total_tokens / 1000 * 0.002, 6)

            return LLMResult(
                content=choice,
                model_used=data.get("model", model),
                provider=self.name,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                latency_ms=latency_ms,
                cost_usd=cost_usd,
            )
        except Exception as exc:
            latency_ms = int((time.monotonic() - t0) * 1000)
            logger.warning("OpenClaw request failed: %s", exc)
            return LLMResult(
                content="",
                model_used=model,
                provider=self.name,
                prompt_tokens=0,
                completion_tokens=0,
                latency_ms=latency_ms,
                error=str(exc),
            )
