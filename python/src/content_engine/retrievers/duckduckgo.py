"""DuckDuckGo retriever — free web search fallback, no API key required."""

from __future__ import annotations

import asyncio
import logging

from ..models import ResearchItemCreate, RetrieverType, SourceType
from .base import BaseRetriever

logger = logging.getLogger("content_engine.retrievers.duckduckgo")

# Conservative rate limit to avoid temporary DDG blocks (~20 req/min)
_DDG_DELAY_SECONDS = 3.0
_DDG_LOCK = asyncio.Lock()


def _build_queries(topics: list[str], principles: list[str]) -> list[str]:
    """Build search queries from brand topics and principles (same logic as SerperRetrievers)."""
    queries: list[str] = []
    for topic in topics[:4]:
        queries.append(topic)
    for principle in principles[:2]:
        if len(principle) < 80:
            queries.append(principle)
    return queries or ["content marketing strategy"]


class DuckDuckGoRetriever(BaseRetriever):
    """Free web search via DuckDuckGo. No API key required.

    Used as automatic fallback when no premium search API (Serper/Tavily) is configured.
    Rate-limited conservatively to avoid temporary DDG soft-blocks.
    """

    retriever_type = RetrieverType.DUCKDUCKGO

    async def fetch(self, config: dict) -> list[ResearchItemCreate]:
        topics: list[str] = config.get("topics", [])
        principles: list[str] = config.get("founder_principles", [])
        max_items: int = config.get("max_items", 30)
        language: str = config.get("language", "en")
        exclude_domains: list[str] = config.get("exclude_domains", [])

        queries = _build_queries(topics, principles)
        items: list[ResearchItemCreate] = []
        seen_urls: set[str] = set()

        try:
            from duckduckgo_search import DDGS  # noqa: F401
        except ImportError:
            logger.warning("duckduckgo-search not installed — DuckDuckGoRetriever disabled")
            return []

        for query in queries:
            if len(items) >= max_items:
                break
            try:
                async with _DDG_LOCK:
                    await asyncio.sleep(_DDG_DELAY_SECONDS)
                    results = await asyncio.to_thread(
                        self._search_sync, query, language, max_items - len(items)
                    )

                for r in results:
                    url = r.get("href", "") or r.get("url", "")
                    title = r.get("title", "")
                    body = r.get("body", "")
                    source = r.get("source", "") or self._domain(url)

                    if not url or not title:
                        continue
                    if url in seen_urls:
                        continue
                    if any(ex in url for ex in exclude_domains):
                        continue

                    seen_urls.add(url)
                    items.append(ResearchItemCreate(
                        brand_id=self.brand_id,
                        run_id=self.run_id,
                        retriever=RetrieverType.DUCKDUCKGO,
                        source_type=SourceType.SEARCH,
                        title=title,
                        url=url,
                        source_name=source,
                        summary=body[:500] if body else "",
                        language=language,
                    ))

            except Exception as e:
                logger.warning("DDG search failed for query '%s': %s", query, e)
                continue

        return items

    def _search_sync(self, query: str, language: str, max_results: int) -> list[dict]:
        from duckduckgo_search import DDGS
        region = "it-it" if language == "it" else "wt-wt"
        with DDGS() as ddgs:
            return list(ddgs.text(query, region=region, max_results=min(max_results, 10)))

    @staticmethod
    def _domain(url: str) -> str:
        try:
            from urllib.parse import urlparse
            return urlparse(url).netloc.removeprefix("www.")
        except Exception:
            return ""
