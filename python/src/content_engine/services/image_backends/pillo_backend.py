# pillo_backend.py
"""Pillo / PostNitro carousel generation backend.

Pillo's API is optimized for multi-slide carousels rather than single images.
When the caller requests a single image we still ask Pillo for a 1-slide
carousel and return slide 0. Requires PILLO_API_KEY.
"""
from __future__ import annotations

import httpx

from ...config import settings
from .base import GeneratedImage


class PilloBackend:
    name = "pillo"

    async def generate(self, *, prompt: str, negative_prompt: str | None,
                       model_id: str, width: int, height: int,
                       seed: int | None) -> GeneratedImage:
        if not settings.pillo_api_key:
            raise RuntimeError("PILLO_API_KEY not configured")

        headers = {"Authorization": f"Bearer {settings.pillo_api_key}",
                   "Content-Type": "application/json"}
        body = {
            "topic": prompt,
            "slides": 1,
            "style": model_id or "default",  # Pillo treats 'model' as style preset id
            "size": f"{width}x{height}",
        }
        async with httpx.AsyncClient(timeout=120) as c:
            r = await c.post("https://api.pillo.ai/v1/carousels", json=body, headers=headers)
            r.raise_for_status()
            data = r.json()
            slide_url = data["slides"][0]["image_url"]
            img = await c.get(slide_url)
            img.raise_for_status()

        return GeneratedImage(
            image_bytes=img.content, mime_type=img.headers.get("content-type","image/png"),
            width_px=width, height_px=height,
            cost_usd=float(data.get("cost_usd", 0.02)),
            model_id=model_id, seed=seed, raw_response=data,
        )
