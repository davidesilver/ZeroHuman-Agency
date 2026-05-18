"""Replicate backend — calls replicate.run() with the brand's configured model.

We use the HTTP API directly (not the replicate SDK) so httpx-mock fixtures
work identically to the rest of the codebase.
"""
from __future__ import annotations

import asyncio
import time

import httpx

from ...config import settings
from .base import GeneratedImage


class ReplicateBackend:
    name = "replicate"

    async def generate(self, *, prompt: str, negative_prompt: str | None,
                       model_id: str, width: int, height: int,
                       seed: int | None) -> GeneratedImage:
        if not settings.replicate_api_token:
            raise RuntimeError("REPLICATE_API_TOKEN not configured")

        inputs = {
            "prompt": prompt,
            "width": width, "height": height,
            "num_outputs": 1, "num_inference_steps": 4,  # flux-schnell default
        }
        if negative_prompt:
            inputs["negative_prompt"] = negative_prompt
        if seed is not None:
            inputs["seed"] = seed

        headers = {
            "Authorization": f"Token {settings.replicate_api_token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=60) as c:
            create = await c.post(
                f"https://api.replicate.com/v1/models/{model_id}/predictions",
                json={"input": inputs}, headers=headers,
            )
            create.raise_for_status()
            pred = create.json()

            # Poll until succeeded|failed|canceled. Replicate typical = 3–10s for flux-schnell.
            started = time.time()
            while pred["status"] not in ("succeeded", "failed", "canceled"):
                if time.time() - started > 120:
                    raise TimeoutError("Replicate prediction timed out after 120s")
                await asyncio.sleep(1.5)
                poll = await c.get(pred["urls"]["get"], headers=headers)
                poll.raise_for_status()
                pred = poll.json()

            if pred["status"] != "succeeded":
                raise RuntimeError(f"Replicate prediction {pred['status']}: {pred.get('error')}")

            output = pred.get("output")
            url = output[0] if isinstance(output, list) else output
            img = await c.get(url)
            img.raise_for_status()

        # flux-schnell ~ $0.003 / image. Use Replicate metrics if present.
        cost = float(pred.get("metrics", {}).get("predict_time", 0)) * 0.000725
        return GeneratedImage(
            image_bytes=img.content,
            mime_type=img.headers.get("content-type", "image/png"),
            width_px=width, height_px=height,
            cost_usd=round(cost, 5),
            model_id=model_id, seed=seed,
            raw_response=pred,
        )
