"""Anthropic image generation backend.

Uses Anthropic's Messages API with image output capability.
This lets users leverage their existing Anthropic API key / Claude subscription
for image generation, matching the text-agent provider pattern.

Requires a model that supports image output (Claude 3.7 Sonnet+, Claude 4).
"""
from __future__ import annotations

import base64

import httpx

from ...config import settings
from .base import GeneratedImage


class AnthropicBackend:
    name = "anthropic"

    async def generate(self, *, prompt: str, negative_prompt: str | None,
                       model_id: str, width: int, height: int,
                       seed: int | None) -> GeneratedImage:
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not configured")

        # Anthropic image generation uses the standard Messages API with
        # a specific beta header. The model generates an image as a content
        # block in the assistant response.
        headers = {
            "x-api-key": settings.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
            # Beta header required for image output as of 2025
            "anthropic-beta": "output-128k-2025-02-19",
        }

        body = {
            "model": model_id,
            "max_tokens": 4096,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                f"Generate an image of size {width}x{height} pixels. "
                                f"Description: {prompt}"
                            ),
                        }
                    ],
                }
            ],
        }

        async with httpx.AsyncClient(timeout=120) as c:
            r = await c.post(
                "https://api.anthropic.com/v1/messages",
                json=body,
                headers=headers,
            )
            r.raise_for_status()
            payload = r.json()

        # Extract image from response content blocks
        content_blocks = payload.get("content", [])
        image_block = None
        for block in content_blocks:
            if block.get("type") == "image":
                image_block = block
                break

        if image_block is None:
            raise RuntimeError(
                "Anthropic response did not contain an image block. "
                "Ensure the model supports image output."
            )

        source = image_block.get("source", {})
        mime_type = source.get("media_type", "image/png")
        image_bytes = base64.b64decode(source.get("data", ""))

        # Anthropic image pricing: ~$0.008 per image for Claude Sonnet
        # (actual cost varies; this is a conservative estimate)
        cost = 0.008

        return GeneratedImage(
            image_bytes=image_bytes,
            mime_type=mime_type,
            width_px=width,
            height_px=height,
            cost_usd=cost,
            model_id=model_id,
            seed=seed,
            raw_response=payload,
        )
