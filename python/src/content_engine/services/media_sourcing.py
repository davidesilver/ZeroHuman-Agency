"""B-roll media sourcing cascade for automated shorts."""

from __future__ import annotations

import asyncio
import logging
import os
import threading
import time
from collections.abc import Iterable

import httpx

from ..config import settings
from ..db import get_db

logger = logging.getLogger("content_engine.services.media_sourcing")

REPLICATE_VIDEO_MODEL = os.environ.get("REPLICATE_VIDEO_MODEL", "minimax/video-01-live")
_CACHE_TTL_SECONDS = 15 * 60
_CACHE_LOCK = threading.Lock()
_CACHE: dict[tuple[str, str], tuple[float, list[str]]] = {}


def _normalize_keywords(keywords: str | Iterable[str]) -> str:
    if isinstance(keywords, str):
        tokens = [part.strip() for part in keywords.replace(",", " ").split()]
    else:
        tokens = [str(part).strip() for part in keywords]
    clean = [token for token in tokens if token]
    return " ".join(clean).strip()


def _cache_key(brand_id: str, keywords: str) -> tuple[str, str]:
    return brand_id, keywords.lower()


def _get_cached(brand_id: str, keywords: str) -> list[str] | None:
    key = _cache_key(brand_id, keywords)
    with _CACHE_LOCK:
        entry = _CACHE.get(key)
        if not entry:
            return None
        saved_at, values = entry
        if time.time() - saved_at > _CACHE_TTL_SECONDS:
            _CACHE.pop(key, None)
            return None
        return list(values)


def _set_cached(brand_id: str, keywords: str, values: list[str]) -> None:
    key = _cache_key(brand_id, keywords)
    with _CACHE_LOCK:
        _CACHE[key] = (time.time(), list(values))


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        clean = value.strip()
        if not clean or clean in seen:
            continue
        seen.add(clean)
        ordered.append(clean)
    return ordered


def _brand_asset_bucket_url(storage_path: str) -> str:
    db = get_db()
    signed = db.storage.from_("brand-assets").create_signed_url(storage_path, 900)
    return signed.get("signedURL") or signed.get("signedUrl") or signed.get("signed_url") or ""


async def _brand_asset_videos(brand_id: str, limit: int) -> list[str]:
    db = get_db()
    result = (
        db.table("brand_assets")
        .select("storage_path")
        .eq("brand_id", brand_id)
        .in_("kind", ["example_post", "example_carousel", "other"])
        .like("mime_type", "video/%")
        .order("created_at", desc=True)
        .limit(max(limit * 2, 5))
        .execute()
    )
    rows = result.data or []
    urls = []
    for row in rows:
        storage_path = row.get("storage_path")
        if not storage_path:
            continue
        try:
            url = _brand_asset_bucket_url(storage_path)
        except Exception as exc:
            logger.debug("Failed to sign brand asset %s: %s", storage_path, exc)
            continue
        if url:
            urls.append(url)
        if len(urls) >= limit:
            break
    return urls


async def _replicate_videos(query: str, limit: int) -> list[str]:
    if not settings.replicate_api_token or limit <= 0:
        return []

    headers = {
        "Authorization": f"Token {settings.replicate_api_token}",
        "Content-Type": "application/json",
    }
    payload = {"input": {"prompt": query}}

    async with httpx.AsyncClient(timeout=180) as client:
        response = await client.post(
            f"https://api.replicate.com/v1/models/{REPLICATE_VIDEO_MODEL}/predictions",
            json=payload,
            headers=headers,
        )
        response.raise_for_status()
        prediction = response.json()

        started = time.time()
        while prediction.get("status") not in ("succeeded", "failed", "canceled"):
            if time.time() - started > 180:
                raise TimeoutError("Replicate video generation timed out after 180s")
            await asyncio.sleep(2)
            poll = await client.get(prediction["urls"]["get"], headers=headers)
            poll.raise_for_status()
            prediction = poll.json()

        if prediction.get("status") != "succeeded":
            raise RuntimeError(f"Replicate prediction {prediction.get('status')}: {prediction.get('error')}")

        output = prediction.get("output")
        if isinstance(output, list):
            return [str(item) for item in output if item]
        if isinstance(output, str) and output:
            return [output]
    return []


async def _pexels_videos(query: str, limit: int) -> list[str]:
    if not settings.pexels_api_key or limit <= 0:
        return []

    params = {"query": query, "per_page": max(limit, 3), "orientation": "portrait"}
    headers = {"Authorization": settings.pexels_api_key}

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.get(
            "https://api.pexels.com/videos/search",
            params=params,
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()

    urls: list[str] = []
    for video in data.get("videos", []):
        files = video.get("video_files") or []
        if not files:
            continue
        best = max(
            files,
            key=lambda item: (
                int(item.get("width") or 0) * int(item.get("height") or 0),
                int(item.get("file_size") or 0),
            ),
        )
        link = best.get("link")
        if link:
            urls.append(link)
        if len(urls) >= limit:
            break
    return urls


async def search_b_roll_videos(
    keywords: str | Iterable[str],
    brand_id: str,
    limit: int = 5,
) -> list[str]:
    """Return a cascade of B-roll URLs for a short."""
    normalized = _normalize_keywords(keywords)
    if not normalized:
        normalized = "abstract motion background"

    cached = _get_cached(brand_id, normalized)
    if cached is not None:
        return cached[:limit]

    urls: list[str] = []
    try:
        urls.extend(await _brand_asset_videos(brand_id, limit))
    except Exception as exc:
        logger.warning("Brand asset B-roll lookup failed for %s: %s", brand_id, exc)

    if len(urls) < limit:
        try:
            urls.extend(await _replicate_videos(normalized, limit - len(urls)))
        except Exception as exc:
            logger.warning("Replicate B-roll generation failed for %s: %s", brand_id, exc)

    if len(urls) < limit:
        try:
            urls.extend(await _pexels_videos(normalized, limit - len(urls)))
        except Exception as exc:
            logger.warning("Pexels B-roll lookup failed for %s: %s", brand_id, exc)

    unique = _unique(urls)
    _set_cached(brand_id, normalized, unique)
    return unique[:limit]
