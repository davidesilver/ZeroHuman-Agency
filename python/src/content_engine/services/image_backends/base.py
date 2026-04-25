"""Image backend interface. Each concrete backend implements generate()."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, Optional


@dataclass
class GeneratedImage:
    """Raw bytes + metadata returned by a backend. Caller uploads to Storage."""
    image_bytes: bytes
    mime_type: str            # e.g. "image/png"
    width_px: int
    height_px: int
    cost_usd: float
    model_id: str
    seed: Optional[int] = None
    raw_response: Optional[dict] = None


class ImageBackend(Protocol):
    name: str  # "replicate", "openai", "pillo", "mock"

    async def generate(
        self,
        *,
        prompt: str,
        negative_prompt: Optional[str],
        model_id: str,
        width: int,
        height: int,
        seed: Optional[int],
    ) -> GeneratedImage: ...
