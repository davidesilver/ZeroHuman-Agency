# openai_backend.py
"""OpenAI image generation (gpt-image-1 / DALL-E 3)."""
from __future__ import annotations

import base64

import httpx

from ...config import settings
from .base import GeneratedImage


class OpenAIBackend:
    name = "openai"

    async def generate(self, *, prompt: str, negative_prompt: str | None,
                       model_id: str, width: int, height: int,
                       seed: int | None) -> GeneratedImage:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY not configured")
        # gpt-image-1 supports 1024x1024, 1024x1536, 1536x1024
        size = f"{width}x{height}"
        body = {"model": model_id, "prompt": prompt, "size": size, "n": 1, "response_format": "b64_json"}
        headers = {"Authorization": f"Bearer {settings.openai_api_key}",
                   "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=90) as c:
            r = await c.post("https://api.openai.com/v1/images/generations", json=body, headers=headers)
            r.raise_for_status()
            payload = r.json()
        b64 = payload["data"][0]["b64_json"]
        # DALL-E 3 1024² ~ $0.040; gpt-image-1 ~ $0.011 for medium.
        cost = 0.040 if "dall-e-3" in model_id else 0.011
        return GeneratedImage(
            image_bytes=base64.b64decode(b64), mime_type="image/png",
            width_px=width, height_px=height, cost_usd=cost,
            model_id=model_id, seed=seed, raw_response=payload,
        )
