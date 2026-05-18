"""OpenRouter image generation backend.

OpenRouter supports image models through an OpenAI-compatible
/api/v1/images/generations endpoint. This lets users switch image models
using the same OpenRouter API key already configured for text agents.
"""
from __future__ import annotations

import base64

import httpx

from ...config import settings
from .base import GeneratedImage


class OpenRouterBackend:
    name = "openrouter"

    async def generate(self, *, prompt: str, negative_prompt: str | None,
                       model_id: str, width: int, height: int,
                       seed: int | None) -> GeneratedImage:
        if not settings.openrouter_api_key:
            raise RuntimeError("OPENROUTER_API_KEY not configured")

        size = f"{width}x{height}"
        body = {
            "model": model_id,
            "prompt": prompt,
            "size": size,
            "n": 1,
            "response_format": "b64_json",
        }
        if seed is not None:
            body["seed"] = seed

        headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://content-engine.local",
            "X-Title": "Content Engine",
        }

        async with httpx.AsyncClient(timeout=120) as c:
            r = await c.post(
                "https://openrouter.ai/api/v1/images/generations",
                json=body,
                headers=headers,
            )
            r.raise_for_status()
            payload = r.json()

        b64 = payload["data"][0]["b64_json"]

        # OpenRouter pricing varies by model. We try to extract cost from
        # response headers (OpenRouter returns usage info) or fall back to
        # rough estimates for known models.
        cost = self._estimate_cost(payload, model_id)

        return GeneratedImage(
            image_bytes=base64.b64decode(b64),
            mime_type="image/png",
            width_px=width,
            height_px=height,
            cost_usd=cost,
            model_id=model_id,
            seed=seed,
            raw_response=payload,
        )

    def _estimate_cost(self, payload: dict, model_id: str) -> float:
        # OpenRouter may return usage in the payload
        usage = payload.get("usage", {})
        if "total_cost" in usage:
            return float(usage["total_cost"])

        # Rough per-image estimates (USD) for known models — updated 2025-06
        estimates = {
            "stabilityai/stable-diffusion-3-medium": 0.035,
            "black-forest-labs/flux-1-schnell": 0.003,
            "black-forest-labs/flux-1-dev": 0.025,
            "black-forest-labs/flux-1.1-pro": 0.040,
        }
        return estimates.get(model_id, 0.020)
