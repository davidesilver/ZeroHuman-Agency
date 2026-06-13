from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


def test_group_words_chunks_2_to_4_words():
    from content_engine.services.subtitle_generator import _group_words

    words = [
        {"text": "One", "start": 0.0, "end": 0.2},
        {"text": "two", "start": 0.22, "end": 0.4},
        {"text": "three", "start": 0.42, "end": 0.7},
        {"text": "four", "start": 0.72, "end": 0.95},
        {"text": "five", "start": 1.55, "end": 1.8},
    ]

    blocks = _group_words(words)

    assert [len(block["words"]) for block in blocks] == [3, 2]
    assert blocks[0]["text"] == "One two three"
    assert blocks[1]["text"] == "four five"


@pytest.mark.asyncio
async def test_generate_subtitle_blocks_falls_back_to_text_when_sidecar_fails():
    from content_engine.services import subtitle_generator

    with patch.object(subtitle_generator, "_transcribe_with_sidecar", new=AsyncMock(side_effect=RuntimeError("down"))):
        blocks = await subtitle_generator.generate_subtitle_blocks(
            "/tmp/audio.mp3",
            fallback_text="A short fallback narration",
            fallback_duration_seconds=4.0,
        )

    assert blocks
    assert blocks[0]["text"].startswith("A short")
