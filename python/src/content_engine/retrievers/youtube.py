"""YouTube Retriever — searches YouTube Data API for relevant videos.

CLI path (PrintingPress youtube):
    Install:  npm install -g @printingpress/youtube  (or per printingpress.dev docs)
    Binary:   youtube  (or override via PP_YOUTUBE_BIN env var)
    Command:  youtube search "<query>" --max-results 5 --published-after <ISO8601>
              youtube channel <channelId> --max-results 3 --published-after <ISO8601>
    Output:   JSON array of video objects with fields:
                videoId/id, title, channelTitle, description, publishedAt, url
    Cache:    SQLite local — identical queries within the cache window skip network round-trip.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from ..config import settings
from ..models import ResearchItemCreate, RetrieverType, SourceType
from ..utils.cli_runner import CLINotFoundError, run_cli
from .base import BaseRetriever

logger = logging.getLogger(__name__)

YT_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
_CLI_BINARY_ENV = "PP_YOUTUBE_BIN"
_CLI_BINARY_DEFAULT = "youtube"


class YouTubeRetriever(BaseRetriever):
    retriever_type = RetrieverType.YOUTUBE

    async def fetch(self, config: dict) -> list[ResearchItemCreate]:
        if not settings.youtube_api_key:
            return []

        topics: list[str] = config.get("topics", [])
        channels: list[str] = config.get("youtube_channels", [])
        max_items: int = config.get("max_items", 30)
        days_back: int = config.get("days_back", 7)

        published_after = (datetime.now(timezone.utc) - timedelta(days=days_back)).isoformat()
        items: list[ResearchItemCreate] = []
        seen_urls: set[str] = set()

        binary = os.environ.get(_CLI_BINARY_ENV, _CLI_BINARY_DEFAULT)

        # Topics search
        for topic in topics[:5]:
            if len(items) >= max_items:
                break
            results = await _youtube_search(
                binary,
                ["search", topic, "--max-results", "5", "--published-after", published_after],
                api_key=settings.youtube_api_key,
                fallback_params={
                    "part": "snippet",
                    "q": topic,
                    "type": "video",
                    "order": "relevance",
                    "publishedAfter": published_after,
                    "maxResults": 5,
                    "key": settings.youtube_api_key,
                },
            )
            for video in results:
                item = _video_to_item(video, self.brand_id, self.run_id, self.retriever_type)
                if item and item.url not in seen_urls:
                    seen_urls.add(item.url)
                    items.append(item)

        # Channel search
        for channel_id in channels[:10]:
            if len(items) >= max_items:
                break
            results = await _youtube_search(
                binary,
                ["channel", channel_id, "--max-results", "3", "--published-after", published_after],
                api_key=settings.youtube_api_key,
                fallback_params={
                    "part": "snippet",
                    "channelId": channel_id,
                    "type": "video",
                    "order": "date",
                    "publishedAfter": published_after,
                    "maxResults": 3,
                    "key": settings.youtube_api_key,
                },
            )
            for video in results:
                item = _video_to_item(video, self.brand_id, self.run_id, self.retriever_type)
                if item and item.url not in seen_urls:
                    seen_urls.add(item.url)
                    items.append(item)

        return items[:max_items]


async def _youtube_search(
    binary: str,
    args: list[str],
    *,
    api_key: str,
    fallback_params: dict,
) -> list[dict]:
    try:
        raw = await run_cli(binary, args, env_extra={"YOUTUBE_API_KEY": api_key})
        return _normalize_youtube_results(raw)
    except CLINotFoundError:
        logger.debug("YouTube CLI not found — using API directly")
    except Exception as exc:
        logger.warning("YouTube CLI failed (%s) — using API", exc)

    # Fallback: direct YouTube Data API
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(YT_SEARCH_URL, params=fallback_params)
            if resp.status_code != 200:
                return []
            data = resp.json()
        results: list[dict] = []
        for item in data.get("items", []):
            video_id = item.get("id", {}).get("videoId", "")
            if not video_id:
                continue
            snippet = item.get("snippet", {})
            results.append({
                "id": video_id,
                "title": snippet.get("title", ""),
                "channelTitle": snippet.get("channelTitle", "YouTube"),
                "description": snippet.get("description", ""),
                "publishedAt": snippet.get("publishedAt", ""),
                "url": f"https://www.youtube.com/watch?v={video_id}",
            })
        return results
    except Exception as exc:
        logger.warning("YouTube API request failed: %s", exc)
        return []


def _normalize_youtube_results(raw: Any) -> list[dict]:
    if isinstance(raw, dict):
        raw = raw.get("items", []) or raw.get("videos", []) or raw.get("results", [])
    if not isinstance(raw, list):
        return []
    normalized: list[dict] = []
    for v in raw:
        if not isinstance(v, dict):
            continue
        video_id = v.get("id") or v.get("videoId", "")
        url = v.get("url") or (f"https://www.youtube.com/watch?v={video_id}" if video_id else "")
        if not url:
            continue
        normalized.append({
            "id": video_id,
            "title": v.get("title", ""),
            "channelTitle": v.get("channelTitle") or v.get("channel", "YouTube"),
            "description": v.get("description") or v.get("snippet", ""),
            "publishedAt": v.get("publishedAt") or v.get("published_at", ""),
            "url": url,
        })
    return normalized


def _video_to_item(
    video: dict,
    brand_id: str,
    run_id: str,
    retriever_type: RetrieverType,
) -> ResearchItemCreate | None:
    url = video.get("url", "")
    title = video.get("title", "")
    if not url or not title:
        return None

    pub_dt: datetime | None = None
    pub_str = video.get("publishedAt", "")
    if pub_str:
        try:
            pub_dt = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
        except Exception:
            pass

    try:
        return ResearchItemCreate(
            brand_id=brand_id,
            run_id=run_id,
            retriever=retriever_type,
            source_type=SourceType.YOUTUBE,
            title=title,
            url=url,
            source_name=video.get("channelTitle", "YouTube"),
            author=video.get("channelTitle"),
            summary=video.get("description", "")[:500],
            published_at=pub_dt,
            language="en",
        )
    except Exception as exc:
        logger.debug("YouTubeRetriever: skipping video %s: %s", url, exc)
        return None
