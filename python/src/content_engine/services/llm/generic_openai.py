"""GenericOpenAIProvider — covers every OpenAI-compatible endpoint.

This single class handles Groq, OpenAI, Google AI, DeepSeek, Mistral, xAI,
Together, Fireworks, NVIDIA, Perplexity, Moonshot, Cerebras, SambaNova, Qwen,
and all local gateways (Ollama, OpenClaw, LM Studio, vLLM, LiteLLM, Cloudflare).

Usage:
    provider = GenericOpenAIProvider.from_brand_config("groq", brand_id)
    if provider:
        result = provider.complete(request)
"""

from __future__ import annotations

import logging
import time
from typing import Optional

import httpx

from .provider import LLMProvider, LLMRequest, LLMResult
from .provider_catalog import PROVIDER_CATALOG

logger = logging.getLogger("content_engine.llm.generic_openai")

# Per-model cost estimates (USD per 1K tokens) — placeholder until real pricing API
_COST_PER_1K: dict[str, float] = {
    # OpenAI
    "gpt-4o": 0.005,
    "gpt-4o-mini": 0.00015,
    "gpt-4-turbo": 0.01,
    # Google
    "gemini-2.5-pro": 0.00125,
    "gemini-2.5-flash": 0.000075,
    # Groq (free)
    "llama-3.3-70b-versatile": 0.0,
    "llama-3.1-8b-instant": 0.0,
    # DeepSeek
    "deepseek-chat": 0.00027,
    "deepseek-reasoner": 0.00055,
    # Mistral
    "mistral-large-latest": 0.002,
    "mistral-small-latest": 0.0002,
    # xAI
    "grok-3": 0.003,
    "grok-3-mini": 0.0003,
    # Together
    "meta-llama/Llama-3.3-70B-Instruct-Turbo": 0.00088,
    # Moonshot
    "moonshot-v1-8k": 0.00012,
    "moonshot-v1-128k": 0.00054,
    # Cerebras (free)
    "llama3.1-70b": 0.0,
    "llama3.1-8b": 0.0,
}


class GenericOpenAIProvider(LLMProvider):
    """OpenAI-compatible provider. Works with any base_url that speaks /v1/chat/completions."""

    def __init__(
        self,
        provider_id: str,
        base_url: str,
        api_key: Optional[str] = None,
        default_model: Optional[str] = None,
    ) -> None:
        self._provider_id = provider_id
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._default_model = default_model

    @property
    def name(self) -> str:
        return self._provider_id

    def is_available(self, brand_id: str) -> bool:
        defn = PROVIDER_CATALOG.get(self._provider_id)
        if not defn:
            return False
        if defn.auth_type == "none":
            return True
        if defn.auth_type == "optional_key":
            return True
        return bool(self._api_key)

    def complete(self, request: LLMRequest) -> LLMResult:
        defn = PROVIDER_CATALOG.get(self._provider_id)
        default = (defn.models[0] if defn and defn.models else None)
        model = request.model or self._default_model or default or "gpt-4o"

        messages: list[dict] = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        t0 = time.monotonic()
        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(
                    f"{self._base_url}/chat/completions",
                    headers=headers,
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
            total_tokens = usage.get("total_tokens", 0)
            cost = round(total_tokens / 1000 * _COST_PER_1K.get(model, 0.002), 6)

            return LLMResult(
                content=choice,
                model_used=data.get("model", model),
                provider=self._provider_id,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                latency_ms=latency_ms,
                cost_usd=cost,
            )
        except Exception as exc:
            latency_ms = int((time.monotonic() - t0) * 1000)
            logger.warning("%s request failed: %s", self._provider_id, exc)
            return LLMResult(
                content="",
                model_used=model,
                provider=self._provider_id,
                prompt_tokens=0,
                completion_tokens=0,
                latency_ms=latency_ms,
                error=str(exc),
            )

    def list_models(self) -> list[str]:
        """Fetch available models from /v1/models. Returns [] on failure."""
        headers: dict[str, str] = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(f"{self._base_url}/models", headers=headers)
                resp.raise_for_status()
                data = resp.json()
            return [m["id"] for m in data.get("data", [])]
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_brand_config(
        cls,
        provider_id: str,
        brand_id: str,
        custom_base_url: Optional[str] = None,
    ) -> "GenericOpenAIProvider | None":
        """Build from brand_integrations + optional custom URL.

        Returns None if the provider requires an api_key and none is found.
        """
        from ..brand_secrets import get_brand_secret

        defn = PROVIDER_CATALOG.get(provider_id)
        if not defn or defn.api_type != "openai_compatible":
            return None

        base_url = custom_base_url or get_brand_secret(brand_id, provider_id, "base_url") or defn.default_base_url

        api_key: Optional[str] = None
        if defn.auth_type in ("api_key", "optional_key"):
            api_key = get_brand_secret(brand_id, provider_id, "api_key")
            if defn.auth_type == "api_key" and not api_key:
                return None  # required key missing — not configured for this brand

        default_model = get_brand_secret(brand_id, provider_id, "default_model")
        return cls(provider_id, base_url, api_key, default_model)
