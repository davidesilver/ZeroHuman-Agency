"""AnthropicDirectProvider — Anthropic SDK (messages API).

The Anthropic API is not OpenAI-compatible so it gets its own provider class.
Uses the brand's BYOK key if present, falls back to system ANTHROPIC_API_KEY.

Usage:
    provider = AnthropicDirectProvider.from_brand_config(brand_id)
    if provider:
        result = provider.complete(request)
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from .provider import LLMProvider, LLMRequest, LLMResult

logger = logging.getLogger("content_engine.llm.anthropic_direct")

_DEFAULT_MODEL = "claude-sonnet-4-20250514"

_COST_PER_1K: dict[str, dict[str, float]] = {
    "claude-sonnet-4-20250514": {"input": 0.003, "output": 0.015},
    "claude-opus-4-20250514":   {"input": 0.015, "output": 0.075},
    "claude-haiku-4-20250514":  {"input": 0.00025, "output": 0.00125},
}


class AnthropicDirectProvider(LLMProvider):
    """Anthropic Claude via official anthropic SDK."""

    def __init__(self, api_key: str, default_model: str = _DEFAULT_MODEL) -> None:
        self._api_key = api_key
        self._default_model = default_model

    @property
    def name(self) -> str:
        return "anthropic"

    def complete(self, request: LLMRequest) -> LLMResult:
        try:
            import anthropic as _anthropic
        except ImportError:
            return LLMResult(
                content="",
                model_used="",
                provider=self.name,
                prompt_tokens=0,
                completion_tokens=0,
                error="anthropic SDK not installed — run: pip install anthropic",
            )

        model = request.model or self._default_model
        t0 = time.monotonic()
        try:
            client = _anthropic.Anthropic(api_key=self._api_key)
            kwargs: dict = {
                "model": model,
                "max_tokens": 4096,
                "messages": [{"role": "user", "content": request.prompt}],
            }
            if request.system_prompt:
                kwargs["system"] = request.system_prompt

            msg = client.messages.create(**kwargs)
            latency_ms = int((time.monotonic() - t0) * 1000)

            content = msg.content[0].text if msg.content else ""
            usage = msg.usage
            pricing = _COST_PER_1K.get(model, {"input": 0.003, "output": 0.015})
            cost = round(
                usage.input_tokens / 1000 * pricing["input"]
                + usage.output_tokens / 1000 * pricing["output"],
                6,
            )

            return LLMResult(
                content=content,
                model_used=model,
                provider=self.name,
                prompt_tokens=usage.input_tokens,
                completion_tokens=usage.output_tokens,
                latency_ms=latency_ms,
                cost_usd=cost,
            )
        except Exception as exc:
            latency_ms = int((time.monotonic() - t0) * 1000)
            logger.warning("Anthropic request failed: %s", exc)
            return LLMResult(
                content="",
                model_used=model,
                provider=self.name,
                prompt_tokens=0,
                completion_tokens=0,
                latency_ms=latency_ms,
                error=str(exc),
            )

    @classmethod
    def from_brand_config(cls, brand_id: str) -> Optional["AnthropicDirectProvider"]:
        """Build from BYOK key if available, else system env var."""
        from ..brand_secrets import get_brand_secret
        from ...config import settings

        api_key = get_brand_secret(brand_id, "anthropic", "api_key") or settings.anthropic_api_key
        if not api_key:
            return None

        default_model = (
            get_brand_secret(brand_id, "anthropic", "default_model") or _DEFAULT_MODEL
        )
        return cls(api_key, default_model)
