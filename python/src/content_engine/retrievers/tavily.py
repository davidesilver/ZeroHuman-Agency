"""Tavily retriever — enhanced search with free tier (1000 req/month).

CLI path (PrintingPress tavily):
    Install:  npm install -g @printingpress/tavily  (or per printingpress.dev docs)
    Binary:   tavily  (or override via PP_TAVILY_BIN env var)
    Command:  tavily search "<query>" --max-results 10 --exclude-domains "..."
    Output:   JSON array of result objects with fields: url, title, content/snippet, score
    Cache:    SQLite local — identical queries within the cache window skip network round-trip.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any
from urllib.parse import urlparse

from ..config import settings
from ..models import ResearchItemCreate, RetrieverType, SourceType
from ..utils.cli_runner import CLINotFoundError, run_cli
from .base import BaseRetriever
from .duckduckgo import _build_queries

logger = logging.getLogger("content_engine.retrievers.tavily")

_CLI_BINARY_ENV = "PP_TAVILY_BIN"
_CLI_BINARY_DEFAULT = "tavily"


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

        for query in queries:
            if len(items) >= max_items:
                break
            results = await _tavily_search(
                query,
                max_results=min(10, max_items - len(items)),
                exclude_domains=exclude_domains,
                api_key=settings.tavily_api_key,
            )
            for r in results:
                url = r.get("url", "")
                title = r.get("title", "")
                if not url or not title or url in seen_urls:
                    continue
                seen_urls.add(url)
                items.append(
                    ResearchItemCreate(
                        brand_id=self.brand_id,
                        run_id=self.run_id,
                        retriever=RetrieverType.TAVILY,
                        source_type=SourceType.SEARCH,
                        title=title,
                        url=url,
                        source_name=_domain(url),
                        summary=(r.get("content") or r.get("snippet", ""))[:500],
                        language=language,
                    )
                )

        return items

    @staticmethod
    def _domain(url: str) -> str:
        return _domain(url)


async def _tavily_search(
    query: str,
    *,
    max_results: int = 10,
    exclude_domains: list[str] | None = None,
    api_key: str,
) -> list[dict]:
    binary = os.environ.get(_CLI_BINARY_ENV, _CLI_BINARY_DEFAULT)
    args = ["search", query, "--max-results", str(max_results)]
    if exclude_domains:
        args += ["--exclude-domains", ",".join(exclude_domains)]

    try:
        raw = await run_cli(binary, args, env_extra={"TAVILY_API_KEY": api_key})
        return _normalize_tavily_results(raw)
    except CLINotFoundError:
        logger.debug("Tavily CLI not found — using SDK directly")
    except Exception as exc:
        logger.warning("Tavily CLI failed (%s) — using SDK", exc)

    # Fallback: Tavily Python SDK
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=api_key)
        response = await asyncio.to_thread(
            client.search,
            query,
            max_results=max_results,
            exclude_domains=exclude_domains or None,
        )
        return response.get("results", [])
    except ImportError:
        logger.warning("tavily-python not installed — TavilyRetriever disabled")
    except Exception as exc:
        logger.warning("Tavily SDK failed for query '%s': %s", query, exc)
    return []


def _normalize_tavily_results(raw: Any) -> list[dict]:
    if isinstance(raw, dict):
        raw = raw.get("results", [])
    if not isinstance(raw, list):
        return []
    normalized: list[dict] = []
    for r in raw:
        if not isinstance(r, dict):
            continue
        normalized.append({
            "url": r.get("url", ""),
            "title": r.get("title", ""),
            "content": r.get("content") or r.get("snippet", ""),
        })
    return normalized


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.removeprefix("www.")
    except Exception:
        return ""
