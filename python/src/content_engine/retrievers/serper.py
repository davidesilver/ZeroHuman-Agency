"""Serper-based retrievers: Semantic, Keyword, Practitioner."""

from __future__ import annotations

from datetime import datetime, timezone

import httpx

from ..config import settings
from ..models import ResearchItemCreate, RetrieverType, SourceType
from .base import BaseRetriever

SERPER_URL = "https://google.serper.dev/search"


async def _serper_search(
    query: str,
    *,
    num: int = 10,
    search_type: str = "search",
    time_period: str = "w",
    language: str = "en",
) -> list[dict]:
    if not settings.serper_api_key:
        return []
    payload = {
        "q": query,
        "num": num,
        "tbs": f"qdr:{time_period}",
        "hl": language,
    }
    if search_type == "news":
        payload["type"] = "news"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            SERPER_URL,
            json=payload,
            headers={"X-API-KEY": settings.serper_api_key, "Content-Type": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()
    results = data.get("organic", []) or data.get("news", [])
    return results


class SemanticRetriever(BaseRetriever):
    """Generates search queries from founder principles and searches via Serper."""

    retriever_type = RetrieverType.SEMANTIC

    async def fetch(self, config: dict) -> list[ResearchItemCreate]:
        topics: list[str] = config.get("topics", [])
        principles: list[str] = config.get("founder_principles", [])
        max_items: int = config.get("max_items", 100)
        language: str = config.get("language", "en")
        exclude_domains: list[str] = config.get("exclude_domains", [])

        queries = self._build_queries(topics, principles)
        items: list[ResearchItemCreate] = []
        seen_urls: set[str] = set()

        for query in queries[:15]:
            results = await _serper_search(query, num=10, language=language)
            for r in results:
                url = r.get("link", "")
                if not url or url in seen_urls:
                    continue
                if any(d in url for d in exclude_domains):
                    continue
                seen_urls.add(url)
                items.append(
                    ResearchItemCreate(
                        brand_id=self.brand_id,
                        run_id=self.run_id,
                        retriever=self.retriever_type,
                        source_type=SourceType.ARTICLE,
                        title=r.get("title", ""),
                        url=url,
                        source_name=r.get("source", ""),
                        summary=r.get("snippet", ""),
                        language=language,
                    )
                )
            if len(items) >= max_items:
                break
        return items[:max_items]

    @staticmethod
    def _build_queries(topics: list[str], principles: list[str]) -> list[str]:
        queries: list[str] = []
        for topic in topics[:5]:
            queries.append(f"{topic} latest developments 2026")
            queries.append(f"{topic} practical applications case study")
        for principle in principles[:5]:
            queries.append(f'"{principle}" AI automation')
        return queries


class KeywordRetriever(BaseRetriever):
    """Direct keyword search — no LLM involved."""

    retriever_type = RetrieverType.KEYWORD

    async def fetch(self, config: dict) -> list[ResearchItemCreate]:
        keywords: list[str] = config.get("topics", [])
        max_items: int = config.get("max_items", 50)
        language: str = config.get("language", "it")

        items: list[ResearchItemCreate] = []
        seen_urls: set[str] = set()

        for kw in keywords:
            results = await _serper_search(kw, num=10, search_type="news", language=language)
            for r in results:
                url = r.get("link", "")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                items.append(
                    ResearchItemCreate(
                        brand_id=self.brand_id,
                        run_id=self.run_id,
                        retriever=self.retriever_type,
                        source_type=SourceType.ARTICLE,
                        title=r.get("title", ""),
                        url=url,
                        source_name=r.get("source", ""),
                        summary=r.get("snippet", ""),
                        language=language,
                    )
                )
            if len(items) >= max_items:
                break
        return items[:max_items]


class PractitionerRetriever(BaseRetriever):
    """Searches for content from curated list of practitioners."""

    retriever_type = RetrieverType.PRACTITIONER

    async def fetch(self, config: dict) -> list[ResearchItemCreate]:
        authors: list[str] = config.get("trusted_authors", [])
        topics: list[str] = config.get("topics", [])
        max_items: int = config.get("max_items", 80)

        items: list[ResearchItemCreate] = []
        seen_urls: set[str] = set()

        for author in authors[:20]:
            topic_str = " OR ".join(topics[:3]) if topics else "AI"
            query = f'"{author}" {topic_str}'
            results = await _serper_search(query, num=5)
            for r in results:
                url = r.get("link", "")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                items.append(
                    ResearchItemCreate(
                        brand_id=self.brand_id,
                        run_id=self.run_id,
                        retriever=self.retriever_type,
                        source_type=SourceType.ARTICLE,
                        title=r.get("title", ""),
                        url=url,
                        source_name=r.get("source", ""),
                        author=author,
                        summary=r.get("snippet", ""),
                        language="en",
                    )
                )
            if len(items) >= max_items:
                break
        return items[:max_items]
