"""OpenRouter LLM provider — wraps the existing call_llm() engine.

Adapts the existing call_llm() function to the LLMProvider interface so the
registrar can treat it the same as future providers (OpenClaw, Anthropic direct).
"""

from __future__ import annotations

import asyncio
import logging
import time

from .provider import LLMProvider, LLMRequest, LLMResult

logger = logging.getLogger("content_engine.llm.openrouter")


class OpenRouterProvider(LLMProvider):
    """Delegates to the existing call_llm() implementation in utils/llm_client.py."""

    @property
    def name(self) -> str:
        return "openrouter"

    def complete(self, request: LLMRequest) -> LLMResult:
        from ...utils.llm_client import call_llm

        t0 = time.monotonic()
        try:
            # call_llm is async — run it synchronously from the provider layer.
            # In production FastAPI routes, use the async version directly.
            loop = asyncio.new_event_loop()
            try:
                resp = loop.run_until_complete(
                    call_llm(
                        prompt=request.prompt,
                        brand_id=request.brand_id,
                        context=request.context,
                        action=request.action,
                        system_prompt=request.system_prompt,
                        task_type=request.task_type,
                        temperature=request.temperature,
                    )
                )
            finally:
                loop.close()

            latency_ms = int((time.monotonic() - t0) * 1000)
            return LLMResult(
                content=resp.content,
                model_used=resp.model_used,
                provider=self.name,
                prompt_tokens=resp.tokens_prompt,
                completion_tokens=resp.tokens_completion,
                latency_ms=resp.latency_ms or latency_ms,
                cost_usd=resp.cost_usd,
                is_fallback=resp.used_fallback,
            )
        except Exception as exc:
            latency_ms = int((time.monotonic() - t0) * 1000)
            return LLMResult(
                content="",
                model_used="",
                provider=self.name,
                prompt_tokens=0,
                completion_tokens=0,
                latency_ms=latency_ms,
                error=str(exc),
            )
