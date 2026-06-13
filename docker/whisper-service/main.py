from __future__ import annotations

import os
import tempfile
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile

app = FastAPI(title="ZeroHuman Whisper Sidecar", version="0.1.0")


@lru_cache(maxsize=1)
def _model():
    from faster_whisper import WhisperModel

    size = os.environ.get("WHISPER_MODEL_SIZE", "base")
    device = os.environ.get("WHISPER_DEVICE", "cpu")
    compute_type = os.environ.get("WHISPER_COMPUTE_TYPE", "int8")
    return WhisperModel(size, device=device, compute_type=compute_type)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    suffix = Path(file.filename or "audio").suffix or ".mp3"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
        temp_path = Path(handle.name)
        handle.write(await file.read())

    try:
        model = _model()
        segments, _info = model.transcribe(str(temp_path), word_timestamps=True, vad_filter=True)
        words: list[dict[str, float | str]] = []
        for segment in segments:
            segment_words = getattr(segment, "words", None) or []
            for word in segment_words:
                text = str(getattr(word, "word", "")).strip()
                if not text:
                    continue
                words.append({
                    "word": text,
                    "start": float(getattr(word, "start", 0.0) or 0.0),
                    "end": float(getattr(word, "end", 0.0) or 0.0),
                })
        return words
    except Exception as exc:
        raise HTTPException(500, f"Transcription failed: {exc}") from exc
    finally:
        temp_path.unlink(missing_ok=True)
