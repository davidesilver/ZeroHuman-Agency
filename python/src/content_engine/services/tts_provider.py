"""TTS helper for the automated shorts pipeline."""

from __future__ import annotations

import base64
import logging
import tempfile
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import httpx

from ..config import settings
from .brand_secrets import get_brand_secret

logger = logging.getLogger("content_engine.services.tts_provider")


@dataclass(slots=True)
class TTSResult:
    audio_path: str
    provider_used: str
    mime_type: str = "audio/mpeg"
    duration_seconds: float | None = None
    voice_id: str | None = None


def _temp_audio_path(suffix: str = ".mp3") -> Path:
    return Path(tempfile.gettempdir()) / f"shorts-tts-{uuid4().hex}{suffix}"


async def _save_audio_bytes(audio_bytes: bytes, suffix: str = ".mp3") -> str:
    path = _temp_audio_path(suffix)
    path.write_bytes(audio_bytes)
    return str(path)


async def _synthesize_with_elevenlabs(
    text: str,
    api_key: str,
    voice_id: str | None,
) -> TTSResult:
    if not voice_id:
        raise ValueError("voice_id is required for direct ElevenLabs synthesis")

    headers = {
        "xi-api-key": api_key,
        "accept": "audio/mpeg",
        "content-type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
    }

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        audio_bytes = response.content

    return TTSResult(
        audio_path=await _save_audio_bytes(audio_bytes),
        provider_used="elevenlabs",
        mime_type=response.headers.get("content-type", "audio/mpeg"),
        voice_id=voice_id,
    )


async def _synthesize_with_sidecar(
    text: str,
    provider: str,
    voice_id: str | None,
    api_key: str | None = None,
) -> TTSResult:
    payload = {
        "text": text,
        "provider": provider,
        "voice_id": voice_id,
        "api_key": api_key,
    }
    async with httpx.AsyncClient(timeout=180) as client:
        response = await client.post(
            f"{settings.tts_service_url.rstrip('/')}/tts",
            json=payload,
        )
        response.raise_for_status()

    if response.headers.get("content-type", "").startswith("application/json"):
        data = response.json()
        if isinstance(data, dict) and data.get("audio_base64"):
            audio_bytes = base64.b64decode(data["audio_base64"])
            return TTSResult(
                audio_path=await _save_audio_bytes(audio_bytes),
                provider_used=str(data.get("provider_used") or provider),
                mime_type=str(data.get("mime_type") or "audio/mpeg"),
                duration_seconds=data.get("duration_seconds"),
                voice_id=data.get("voice_id") or voice_id,
            )

    return TTSResult(
        audio_path=await _save_audio_bytes(response.content),
        provider_used=provider,
        mime_type=response.headers.get("content-type", "audio/mpeg"),
        voice_id=voice_id,
    )


async def synthesize_tts(
    text: str,
    brand_id: str,
    provider: str = "auto",
    voice_id: str | None = None,
) -> TTSResult:
    """Synthesize a voiceover for shorts.

    Strategy:
    - Prefer a direct ElevenLabs call when a brand key exists.
    - Otherwise delegate to the local TTS sidecar.
    - The sidecar is responsible for provider fallback (local models -> Edge-TTS).
    """
    clean_text = text.strip()
    if not clean_text:
        raise ValueError("text is required")

    api_key = get_brand_secret(brand_id, "elevenlabs", "api_key")
    if provider in ("auto", "elevenlabs") and api_key and voice_id:
        try:
            return await _synthesize_with_elevenlabs(clean_text, api_key, voice_id)
        except Exception as exc:
            logger.warning("Direct ElevenLabs synthesis failed, falling back to sidecar: %s", exc)
            if provider == "elevenlabs":
                # Caller explicitly requested ElevenLabs; if it fails, surface the error.
                raise

    sidecar_provider = provider if provider != "auto" else "edge-tts"
    try:
        return await _synthesize_with_sidecar(clean_text, sidecar_provider, voice_id, api_key)
    except Exception as exc:
        if provider in ("auto", "edge-tts"):
            logger.warning("Sidecar TTS failed, retrying with edge-tts: %s", exc)
            if sidecar_provider != "edge-tts":
                return await _synthesize_with_sidecar(clean_text, "edge-tts", voice_id, None)
        raise
