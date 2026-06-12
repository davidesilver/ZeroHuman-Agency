from __future__ import annotations

import base64
import logging
import tempfile
from pathlib import Path
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("tts_service")

app = FastAPI(title="ZeroHuman TTS Sidecar", version="0.1.0")


class TTSRequest(BaseModel):
    text: str
    provider: Literal["auto", "chatterbox", "cosyvoice", "edge-tts", "elevenlabs"] = "auto"
    voice_id: str | None = None
    api_key: str | None = None


def _estimate_duration(text: str) -> float:
    words = len([token for token in text.split() if token.strip()])
    return round(max(2.0, words / 2.6), 2)


async def _edge_tts(text: str, voice_name: str | None = None) -> tuple[bytes, str]:
    import edge_tts

    voice = voice_name or "en-US-JennyNeural"
    communicate = edge_tts.Communicate(text=text, voice=voice)
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as handle:
        temp_path = Path(handle.name)
    try:
        await communicate.save(str(temp_path))
        return temp_path.read_bytes(), voice
    finally:
        temp_path.unlink(missing_ok=True)


async def _elevenlabs(text: str, api_key: str, voice_id: str) -> tuple[bytes, str]:
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
        return response.content, voice_id


async def _synthesize(req: TTSRequest) -> tuple[bytes, str, str]:
    text = req.text.strip()
    if not text:
        raise HTTPException(400, "text is required")

    if req.provider == "elevenlabs":
        if req.api_key and req.voice_id:
            try:
                audio, used_voice = await _elevenlabs(text, req.api_key, req.voice_id)
                return audio, "elevenlabs", used_voice
            except Exception as exc:
                logger.warning("ElevenLabs failed, falling back to Edge-TTS: %s", exc)
        elif req.api_key and not req.voice_id:
            raise HTTPException(400, "voice_id is required for ElevenLabs")

    voice_hint = req.voice_id
    if req.provider == "chatterbox":
        voice_hint = voice_hint or "en-US-JennyNeural"
    elif req.provider == "cosyvoice":
        voice_hint = voice_hint or "en-US-GuyNeural"
    elif req.provider == "elevenlabs":
        voice_hint = voice_hint or "en-US-JennyNeural"

    audio, used_voice = await _edge_tts(text, voice_hint)
    return audio, "edge-tts", used_voice


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/voices")
async def voices():
    return {
        "edge-tts": [
            "en-US-JennyNeural",
            "en-US-GuyNeural",
            "it-IT-ElsaNeural",
            "it-IT-DiegoNeural",
        ],
        "chatterbox": ["default"],
        "cosyvoice": ["default"],
        "elevenlabs": ["voice-id-from-brand-secret"],
    }


@app.post("/tts")
async def tts(req: TTSRequest):
    audio, provider_used, voice_id = await _synthesize(req)
    return {
        "provider_used": provider_used,
        "voice_id": voice_id,
        "mime_type": "audio/mpeg",
        "duration_seconds": _estimate_duration(req.text),
        "audio_base64": base64.b64encode(audio).decode("ascii"),
    }
