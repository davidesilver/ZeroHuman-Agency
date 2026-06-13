"""Whisper-backed subtitle generation for automated shorts."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import httpx

from ..config import settings

logger = logging.getLogger("content_engine.services.subtitle_generator")


def _clean_word(word: str) -> str:
    return " ".join(word.strip().split())


def _normalize_word_payload(words: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for raw in words:
        text = _clean_word(str(raw.get("word") or raw.get("text") or ""))
        if not text:
            continue
        try:
            start = float(raw.get("start", 0.0))
            end = float(raw.get("end", start))
        except (TypeError, ValueError):
            start = 0.0
            end = 0.0
        normalized.append({"text": text, "start": start, "end": max(end, start)})
    return normalized


def _group_words(
    words: list[dict[str, Any]],
    *,
    min_words: int = 2,
    max_words: int = 4,
    gap_seconds: float = 0.45,
) -> list[dict[str, Any]]:
    if not words:
        return []

    blocks: list[dict[str, Any]] = []
    current: list[dict[str, Any]] = []

    for index, word in enumerate(words):
        current.append(word)
        next_word = words[index + 1] if index + 1 < len(words) else None
        gap = (float(next_word["start"]) - float(word["end"])) if next_word else 0.0
        should_flush = len(current) >= max_words or (
            len(current) >= min_words and gap > gap_seconds
        )
        if should_flush:
            blocks.append(
                {
                    "start": float(current[0]["start"]),
                    "end": float(current[-1]["end"]),
                    "text": " ".join(item["text"] for item in current).strip(),
                    "words": current.copy(),
                }
            )
            current = []

    if current:
        blocks.append(
            {
                "start": float(current[0]["start"]),
                "end": float(current[-1]["end"]),
                "text": " ".join(item["text"] for item in current).strip(),
                "words": current.copy(),
            }
        )

    def _rebuild(block: dict[str, Any]) -> None:
        block["start"] = float(block["words"][0]["start"])
        block["end"] = float(block["words"][-1]["end"])
        block["text"] = " ".join(item["text"] for item in block["words"]).strip()

    if len(blocks) >= 2 and len(blocks[-1]["words"]) == 1:
        last_word = blocks[-1]["words"][0]
        prev_words = blocks[-2]["words"]
        if len(prev_words) == 2:
            prev_words.append(last_word)
            _rebuild(blocks[-2])
            blocks.pop()
        elif len(prev_words) >= 3:
            moved = prev_words.pop()
            blocks[-1]["words"] = [moved, last_word]
            _rebuild(blocks[-2])
            _rebuild(blocks[-1])

    return blocks


def _estimate_words_from_text(
    text: str,
    duration_seconds: float | None,
) -> list[dict[str, Any]]:
    tokens = [_clean_word(token) for token in text.split()]
    tokens = [token for token in tokens if token]
    if not tokens:
        return []

    total_duration = duration_seconds or max(4.0, len(tokens) * 0.35)
    total_weight = sum(max(len(token), 1) for token in tokens)
    current = 0.0
    words: list[dict[str, Any]] = []
    for token in tokens:
        share = max(len(token), 1) / total_weight
        span = max(0.18, total_duration * share)
        words.append({"text": token, "start": round(current, 2), "end": round(current + span, 2)})
        current += span
    return words


async def _transcribe_with_sidecar(audio_path: str) -> list[dict[str, Any]]:
    file_path = Path(audio_path)
    if not file_path.exists():
        raise FileNotFoundError(audio_path)

    async with httpx.AsyncClient(timeout=300) as client:
        with file_path.open("rb") as handle:
            response = await client.post(
                f"{settings.whisper_service_url.rstrip('/')}/transcribe",
                files={"file": (file_path.name, handle, "audio/mpeg")},
            )
        response.raise_for_status()

    data = response.json()
    if isinstance(data, dict):
        payload = data.get("words") or data.get("data") or []
    else:
        payload = data

    if not isinstance(payload, list):
        return []

    return _normalize_word_payload(payload)


async def generate_subtitle_blocks(
    audio_path: str,
    *,
    fallback_text: str | None = None,
    fallback_duration_seconds: float | None = None,
) -> list[dict[str, Any]]:
    """Turn Whisper word timestamps into 2-4 word caption blocks.

    If the Whisper sidecar is unavailable, falls back to deterministic
    synthetic timings derived from the narration text so the pipeline can
    still complete in development or degraded environments.
    """
    words: list[dict[str, Any]] = []
    try:
        words = await _transcribe_with_sidecar(audio_path)
    except Exception as exc:
        logger.warning("Whisper sidecar failed, falling back to estimated subtitles: %s", exc)

    if not words and fallback_text:
        words = _estimate_words_from_text(fallback_text, fallback_duration_seconds)

    return _group_words(words)
