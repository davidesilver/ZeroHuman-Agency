"""Tavily retriever — enhanced search with free tier (1000 req/month)."""

from __future__ import annotations

import logging

from ..config import settings
from ..models import ResearchItemCreate, RetrieverType, SourceType
from .base import BaseRetriever
from .duckduckgo import _build_queries

logger = logging.getLogger("content_engine.retrievers.tavily")


class TavilyRetriever(BaseRetriever):
    """Web search via Tavily Search API.

    Free tier: 1000 searches/month. Quality significantly higher than DDG.
    Activated automatically when TAVILY_API_KEY is configured.
    Falls back to DuckDuckGoRetriever if key is missing.
    """

    retriever_type = RetrieverType.TAVILY

    async def fetch(self, config: dict) -> list[ResearchItemCreate]:
        if not settings.tavily_api_key:
            logger.warning("TavilyRetriever called without TAVILY_API_KEY — returning empty")
            return []

        topics: list[str] = config.get("topics", [])
        principles: list[str] = config.get("founder_principles", [])
        max_items: int = config.get("max_items", 50)
        exclude_domains: list[str] = config.get("exclude_domains", [])
        language: str = config.get("language", "en")

        queries = _build_queries(topics, principles)
        items: list[ResearchItemCreate] = []
        seen_urls: set[str] = set()

        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=settings.tavily_api_key)
        except ImportError:
            logger.warning("tavily-python not installed — TavilyRetriever disabled")
            return []

        for query in queries:
            if len(items) >= max_items:
                break
            try:
                import asyncio
                response = await asyncio.to_thread(
                    client.search,
                    query,
                    max_results=min(10, max_items - len(items)),
                    exclude_domains=exclude_domains or None,
                )
                for r in response.get("results", []):
                    url = r.get("url", "")
                    title = r.get("title", "")
                    content = r.get("content", "")
                    if not url or not title or url in seen_urls:
                        continue
                    seen_urls.add(url)
                    items.append(ResearchItemCreate(
                        brand_id=self.brand_id,
                        run_id=self.run_id,
                        retriever=RetrieverType.TAVILY,
                        source_type=SourceType.SEARCH,
                        title=title,
                        url=url,
                        source_name=self._domain(url),
                        summary=content[:500] if content else "",
                        language=language,
                    ))
            except Exception as e:
                logger.warning("Tavily search failed for query '%s': %s", query, e)
                continue

        return items

    @staticmethod
    def _domain(url: str) -> str:
        try:
            from urllib.parse import urlparse
            return urlparse(url).netloc.removeprefix("www.")
        except Exception:
            return ""
