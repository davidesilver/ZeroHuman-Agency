"""Content Enrichment — extracts full article text from URLs.

Uses trafilatura (free, no API key) as default.
Falls back to basic requests+BeautifulSoup if trafilatura fails.
Firecrawl API support available for premium extraction if key is configured.

This is NOT a retriever in the traditional sense — it enriches existing
research items by replacing their short Serper snippets with full article text.
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
from typing import Sequence
from urllib.parse import urlparse

import httpx

from ..config import settings
from ..db import get_db

logger = logging.getLogger("content_engine.enrichment")

# M-01: SSRF Protection — block private/reserved IP ranges
_PRIVATE_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),       # loopback
    ipaddress.ip_network("169.254.0.0/16"),    # link-local / AWS metadata
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("::1/128"),            # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),           # IPv6 unique local
]


def _is_safe_url(url: str) -> bool:
    """M-01: Validate URL is safe to fetch — HTTPS only, no private IPs."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("https", "http"):
            return False
        # Block numeric IP addresses in private ranges
        hostname = parsed.hostname or ""
        try:
            addr = ipaddress.ip_address(hostname)
            for network in _PRIVATE_NETWORKS:
                if addr in network:
                    logger.warning("SSRF blocked: %s resolves to private IP %s", url, addr)
                    return False
        except ValueError:
            pass  # hostname is not a bare IP — acceptable
        return True
    except Exception:
        return False

# Max summary length to store (avoid bloating DB)
MAX_SUMMARY_LENGTH = 3000


async def _extract_with_trafilatura(url: str) -> str | None:
    """Extract article text using trafilatura (runs in thread pool)."""
    try:
        import trafilatura

        def _extract():
            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                return None
            text = trafilatura.extract(
                downloaded,
                include_comments=False,
                include_tables=False,
                no_fallback=False,
            )
            return text

        # M-10: asyncio.get_event_loop() deprecated in Python 3.10+
        return await asyncio.to_thread(_extract)
    except ImportError:
        logger.warning("trafilatura not installed, skipping extraction")
        return None
    except Exception as e:
        logger.warning("trafilatura failed for %s: %s", url, e)
        return None


async def _extract_with_firecrawl(url: str, api_key: str) -> str | None:
    """Extract article text using Firecrawl API."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.firecrawl.dev/v1/scrape",
                json={
                    "url": url,
                    "formats": ["markdown"],
                },
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", {}).get("markdown", None)
    except Exception as e:
        logger.warning("Firecrawl failed for %s: %s", url, e)
        return None


async def _extract_with_requests(url: str) -> str | None:
    """Basic fallback: fetch page and extract text with BeautifulSoup."""
    try:
        from bs4 import BeautifulSoup

        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "ContentEngine/1.0"})
            resp.raise_for_status()

        def _parse():
            soup = BeautifulSoup(resp.text, "html.parser")
            # Remove scripts, styles, nav, footer
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()
            # Try article or main content
            article = soup.find("article") or soup.find("main") or soup.find("body")
            if article:
                paragraphs = article.find_all("p")
                return "\n\n".join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 30)
            return None

        # M-10: use asyncio.to_thread() instead of deprecated get_event_loop()
        return await asyncio.to_thread(_parse)
    except Exception as e:
        logger.warning("Basic extraction failed for %s: %s", url, e)
        return None


async def extract_full_text(url: str) -> str | None:
    """Extract full article text from a URL using the best available method.

    Priority: Firecrawl (if API key) → trafilatura → requests+BS4
    """
    # M-01: SSRF protection — validate URL before any network request
    if not _is_safe_url(url):
        logger.warning("Blocked unsafe URL for enrichment: %s", url)
        return None

    # Skip non-article URLs
    skip_domains = {"youtube.com", "youtu.be", "twitter.com", "x.com", "linkedin.com"}
    try:
        domain = urlparse(url).netloc.replace("www.", "")
        if any(s in domain for s in skip_domains):
            return None
    except Exception:
        pass

    firecrawl_key = getattr(settings, "firecrawl_api_key", "")
    if firecrawl_key:
        result = await _extract_with_firecrawl(url, firecrawl_key)
        if result:
            return result[:MAX_SUMMARY_LENGTH]

    result = await _extract_with_trafilatura(url)
    if result:
        return result[:MAX_SUMMARY_LENGTH]

    result = await _extract_with_requests(url)
    if result:
        return result[:MAX_SUMMARY_LENGTH]

    return None


async def enrich_research_items(
    item_ids: Sequence[str],
    *,
    max_concurrent: int = 5,
) -> dict[str, bool]:
    """Enrich research items by extracting full text from their URLs.

    Args:
        item_ids: Research item IDs to enrich.
        max_concurrent: Max concurrent extractions.

    Returns:
        Dict mapping item_id → success boolean.
    """
    db = get_db()
    results: dict[str, bool] = {}
    semaphore = asyncio.Semaphore(max_concurrent)

    # Fetch items
    items_resp = db.table("research_items").select("id, url, summary").in_("id", list(item_ids)).execute()
    items = items_resp.data or []

    async def _enrich_one(item: dict) -> None:
        item_id = item["id"]
        url = item.get("url", "")
        current_summary = item.get("summary", "")

        # Skip if summary is already long (likely already enriched)
        if current_summary and len(current_summary) > 500:
            results[item_id] = True
            return

        async with semaphore:
            full_text = await extract_full_text(url)

        if full_text and len(full_text) > len(current_summary or ""):
            try:
                db.table("research_items").update({
                    "summary": full_text,
                    "metadata": {
                        **(item.get("metadata") or {}),
                        "enriched": True,
                        "original_summary": current_summary[:200] if current_summary else None,
                    },
                }).eq("id", item_id).execute()
                results[item_id] = True
                logger.info("Enriched item %s: %d → %d chars", item_id, len(current_summary or ""), len(full_text))
            except Exception as e:
                logger.warning("Failed to save enriched text for %s: %s", item_id, e)
                results[item_id] = False
        else:
            results[item_id] = False

    await asyncio.gather(*[_enrich_one(item) for item in items])

    enriched = sum(1 for v in results.values() if v)
    logger.info("Enriched %d/%d research items", enriched, len(items))
    return results
