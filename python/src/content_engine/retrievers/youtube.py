"""YouTube Retriever — searches YouTube Data API for relevant videos."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx

from ..config import settings
from ..models import ResearchItemCreate, RetrieverType, SourceType
from .base import BaseRetriever

YT_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"


class YouTubeRetriever(BaseRetriever):
    retriever_type = RetrieverType.TREND

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

        async with httpx.AsyncClient(timeout=30) as client:
            # Search by topics
            for topic in topics[:5]:
                params = {
                    "part": "snippet",
                    "q": topic,
                    "type": "video",
                    "order": "relevance",
                    "publishedAfter": published_after,
                    "maxResults": 5,
                    "key": settings.youtube_api_key,
                }
                resp = await client.get(YT_SEARCH_URL, params=params)
                if resp.status_code != 200:
                    continue
                data = resp.json()
                for item in data.get("items", []):
                    video_id = item["id"].get("videoId", "")
                    if not video_id:
                        continue
                    url = f"https://www.youtube.com/watch?v={video_id}"
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)
                    snippet = item.get("snippet", {})
                    pub_str = snippet.get("publishedAt", "")
                    pub_dt = datetime.fromisoformat(pub_str.replace("Z", "+00:00")) if pub_str else None
                    items.append(
                        ResearchItemCreate(
                            brand_id=self.brand_id,
                            run_id=self.run_id,
                            retriever=self.retriever_type,
                            source_type=SourceType.VIDEO,
                            title=snippet.get("title", ""),
                            url=url,
                            source_name=snippet.get("channelTitle", "YouTube"),
                            author=snippet.get("channelTitle"),
                            summary=snippet.get("description", "")[:500],
                            published_at=pub_dt,
                            language="en",
                        )
                    )
                if len(items) >= max_items:
                    break

            # Search by channel IDs
            for channel_id in channels[:10]:
                params = {
                    "part": "snippet",
                    "channelId": channel_id,
                    "type": "video",
                    "order": "date",
                    "publishedAfter": published_after,
                    "maxResults": 3,
                    "key": settings.youtube_api_key,
                }
                resp = await client.get(YT_SEARCH_URL, params=params)
                if resp.status_code != 200:
                    continue
                data = resp.json()
                for item in data.get("items", []):
                    video_id = item["id"].get("videoId", "")
                    if not video_id:
                        continue
                    url = f"https://www.youtube.com/watch?v={video_id}"
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)
                    snippet = item.get("snippet", {})
                    pub_str = snippet.get("publishedAt", "")
                    pub_dt = datetime.fromisoformat(pub_str.replace("Z", "+00:00")) if pub_str else None
                    items.append(
                        ResearchItemCreate(
                            brand_id=self.brand_id,
                            run_id=self.run_id,
                            retriever=self.retriever_type,
                            source_type=SourceType.VIDEO,
                            title=snippet.get("title", ""),
                            url=url,
                            source_name=snippet.get("channelTitle", "YouTube"),
                            author=snippet.get("channelTitle"),
                            summary=snippet.get("description", "")[:500],
                            published_at=pub_dt,
                            language="en",
                        )
                    )
                if len(items) >= max_items:
                    break

        return items[:max_items]
