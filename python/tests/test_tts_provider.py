from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_synthesize_tts_prefers_elevenlabs_when_secret_exists():
    from content_engine.services import tts_provider
    from content_engine.services.tts_provider import TTSResult

    direct_result = TTSResult(
        audio_path="/tmp/direct.mp3",
        provider_used="elevenlabs",
        mime_type="audio/mpeg",
        duration_seconds=12.3,
        voice_id="voice-1",
    )

    with patch.object(tts_provider, "get_brand_secret", return_value="secret"), \
         patch.object(tts_provider, "_synthesize_with_elevenlabs", new=AsyncMock(return_value=direct_result)) as mock_direct, \
         patch.object(tts_provider, "_synthesize_with_sidecar", new=AsyncMock()) as mock_sidecar:

        result = await tts_provider.synthesize_tts("hello world", "brand-1", provider="auto", voice_id="voice-1")

    assert result.audio_path == "/tmp/direct.mp3"
    assert result.provider_used == "elevenlabs"
    mock_direct.assert_awaited_once()
    mock_sidecar.assert_not_called()


@pytest.mark.asyncio
async def test_synthesize_tts_falls_back_to_sidecar_without_secret():
    from content_engine.services import tts_provider
    from content_engine.services.tts_provider import TTSResult

    sidecar_result = TTSResult(
        audio_path="/tmp/sidecar.mp3",
        provider_used="edge-tts",
        mime_type="audio/mpeg",
        duration_seconds=9.1,
        voice_id="en-US-JennyNeural",
    )

    with patch.object(tts_provider, "get_brand_secret", return_value=None), \
         patch.object(tts_provider, "_synthesize_with_sidecar", new=AsyncMock(return_value=sidecar_result)) as mock_sidecar:

        result = await tts_provider.synthesize_tts("hello world", "brand-1", provider="auto")

    assert result.audio_path == "/tmp/sidecar.mp3"
    assert result.provider_used == "edge-tts"
    mock_sidecar.assert_awaited_once()

