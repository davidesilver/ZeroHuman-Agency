"""Serper-based retrievers: Semantic, Keyword, Practitioner.

CLI path (PrintingPress serper):
    Install:  npm install -g @printingpress/serper  (or per printingpress.dev docs)
    Binary:   serper  (or override via PP_SERPER_BIN env var)
    Command:  serper search "<query>" --num 10 --type news --time w --lang en
    Output:   JSON array of result objects with fields: title, link/url, snippet/description, source
    Cache:    SQLite local — identical queries within the cache window skip network round-trip.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from ..config import settings
from ..models import ResearchItemCreate, RetrieverType, SourceType
from ..utils.cli_runner import CLINotFoundError, run_cli
from .base import BaseRetriever

logger = logging.getLogger(__name__)

SERPER_URL = "https://google.serper.dev/search"

_CLI_BINARY_ENV = "PP_SERPER_BIN"
_CLI_BINARY_DEFAULT = "serper"


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

    binary = os.environ.get(_CLI_BINARY_ENV, _CLI_BINARY_DEFAULT)
    args = ["search", query, "--num", str(num), "--time", time_period, "--lang", language]
    if search_type == "news":
        args += ["--type", "news"]

    try:
        raw = await run_cli(binary, args, env_extra={"SERPER_API_KEY": settings.serper_api_key})
        return _normalize_serper_results(raw)
    except CLINotFoundError:
        logger.debug("Serper CLI not found — using API directly")
    except Exception as exc:
        logger.warning("Serper CLI failed (%s) — using API", exc)

    # Fallback: direct Serper API
    payload: dict[str, Any] = {
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
    return data.get("organic", []) or data.get("news", [])


def _normalize_serper_results(raw: Any) -> list[dict]:
    """Normalize CLI output to the same shape as the Serper API response."""
    if isinstance(raw, dict):
        raw = raw.get("organic", []) or raw.get("news", []) or raw.get("results", [])
    if not isinstance(raw, list):
        return []
    normalized: list[dict] = []
    for r in raw:
        if not isinstance(r, dict):
            continue
        # CLI may use different field names — normalize to API shape
        normalized.append({
            "title": r.get("title", ""),
            "link": r.get("link") or r.get("url", ""),
            "snippet": r.get("snippet") or r.get("description", ""),
            "source": r.get("source") or r.get("domain", ""),
        })
    return normalized


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
                        source_type=SourceType.SEARCH,
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
                        source_type=SourceType.SEARCH,
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
                        source_type=SourceType.SEARCH,
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
