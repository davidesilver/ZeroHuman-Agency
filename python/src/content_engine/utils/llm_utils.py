"""Shared LLM utilities — single authoritative implementation.

M-02/M-03: Previously _call_llm and _parse_json were duplicated across
4 different agent files with diverging implementations (different timeouts,
error handling, and JSON parsing strategies). This module is the single
source of truth used by all agents.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from ..config import settings

_logger = logging.getLogger("content_engine.llm")

# Default LLM model — overridable per call
DEFAULT_MODEL = "anthropic/claude-sonnet-4-20250514"

# Default timeout for LLM calls — enough for long completions
DEFAULT_TIMEOUT = 60.0


async def call_llm(
    prompt: str,
    *,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 2048,
    temperature: float = 0.7,
    timeout: float = DEFAULT_TIMEOUT,
    system: str | None = None,
) -> str:
    """Call the LLM via OpenRouter and return the raw text response.

    Raises:
        RuntimeError: on HTTP error or empty response
        httpx.TimeoutException: if the call exceeds `timeout` seconds
    """
    api_key = settings.openrouter_api_key or settings.anthropic_api_key
    if not api_key:
        raise RuntimeError("No LLM API key configured (OPENROUTER_API_KEY or ANTHROPIC_API_KEY)")

    # Build message list
    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://content-engine.vest",
        "X-Title": "Content Engine",
    }

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
        )

    if resp.status_code != 200:
        _logger.error("LLM HTTP %s: %s", resp.status_code, resp.text[:500])
        raise RuntimeError(f"LLM API error {resp.status_code}")

    data = resp.json()
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not content:
        raise RuntimeError("Empty LLM response")

    return content


def parse_json_response(text: str, context: str = "") -> Any:
    """Parse JSON from an LLM response, handling markdown code fences.

    M-02: Canonical implementation replacing 4 diverging versions across agents.

    Strategy:
        1. Try direct json.loads (handles clean JSON)
        2. Strip markdown code fences (```json ... ```)
        3. Find first {...} or [...] block
        4. Raise ValueError with context for debugging

    Args:
        text: Raw LLM output text.
        context: Optional description of what we were parsing (for error messages).

    Raises:
        ValueError: If no valid JSON could be parsed.
    """
    if not text or not text.strip():
        raise ValueError(f"Empty LLM response{f' in {context}' if context else ''}")

    # 1. Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Strip markdown code fences
    stripped = re.sub(r"```(?:json)?\s*", "", text).replace("```", "").strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    # 3. Extract first JSON object or array
    obj_match = re.search(r"\{[\s\S]*\}", stripped)
    arr_match = re.search(r"\[[\s\S]*\]", stripped)

    # Prefer whichever appears first
    match = None
    if obj_match and arr_match:
        match = obj_match if obj_match.start() < arr_match.start() else arr_match
    elif obj_match:
        match = obj_match
    elif arr_match:
        match = arr_match

    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Found JSON-like content but could not parse it"
                f"{f' in {context}' if context else ''}: {e}"
            ) from e

    raise ValueError(
        f"No JSON found in LLM response{f' in {context}' if context else ''}. "
        f"First 200 chars: {text[:200]!r}"
    )
