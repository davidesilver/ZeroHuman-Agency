"""Mock backend — emits a 1024×1024 PNG with the prompt rendered on a
neutral background. Used in tests + when DEFAULT_IMAGE_BACKEND=mock.
No network calls, no API keys."""
from __future__ import annotations

import io

from PIL import Image, ImageDraw, ImageFont

from .base import GeneratedImage


class MockBackend:
    name = "mock"

    async def generate(self, *, prompt: str, negative_prompt: str | None,
                       model_id: str, width: int, height: int,
                       seed: int | None) -> GeneratedImage:
        img = Image.new("RGB", (width, height), color=(245, 245, 245))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", 18)
        except OSError:
            font = ImageFont.load_default()
        # naive wrap
        words, line, y = prompt.split(), "", 24
        for w in words:
            test = (line + " " + w).strip()
            if draw.textlength(test, font=font) > width - 48:
                draw.text((24, y), line, fill=(20, 20, 20), font=font)
                y += 26
                line = w
            else:
                line = test
        if line:
            draw.text((24, y), line, fill=(20, 20, 20), font=font)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return GeneratedImage(
            image_bytes=buf.getvalue(), mime_type="image/png",
            width_px=width, height_px=height, cost_usd=0.0,
            model_id=model_id, seed=seed, raw_response={"mock": True},
        )
