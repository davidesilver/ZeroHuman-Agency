"""Image backend interface. Each concrete backend implements generate()."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class GeneratedImage:
    """Raw bytes + metadata returned by a backend. Caller uploads to Storage."""
    image_bytes: bytes
    mime_type: str            # e.g. "image/png"
    width_px: int
    height_px: int
    cost_usd: float
    model_id: str
    seed: int | None = None
    raw_response: dict | None = None


class ImageBackend(Protocol):
    name: str  # "replicate", "openai", "pillo", "mock"

    async def generate(
        self,
        *,
        prompt: str,
        negative_prompt: str | None,
        model_id: str,
        width: int,
        height: int,
        seed: int | None,
    ) -> GeneratedImage: ...
