"""Competitor monitoring spider using Scrapling.

Scrapling is an async web scraper with stealth/anti-Cloudflare support.
It complements Firecrawl: use Scrapling for Cloudflare-protected targets.

Usage:
    from content_engine.retrievers.competitor_spider import start_spider, get_snapshots

Feature gate: competitor_monitoring_enabled must be ON.
"""

from __future__ import annotations

import logging
from typing import Optional

from ..db import get_db
from ..services.feature_flags import COMPETITOR_MONITORING_ENABLED, get_feature_flag

logger = logging.getLogger("content_engine.retrievers.competitor_spider")


class SpiderError(Exception):
    """Raised when a spider job fails."""


def _check_feature(brand_id: str) -> None:
    if not get_feature_flag(brand_id, COMPETITOR_MONITORING_ENABLED):
        raise SpiderError(
            f"competitor_monitoring_enabled is OFF for brand {brand_id}. "
            "Enable it in Settings → Feature Flags."
        )


def start_spider(brand_id: str, urls: list[str]) -> list[str]:
    """Create pending snapshot records for each URL and trigger async fetch.

    Returns list of snapshot UUIDs created.

    The actual scraping is done async via _fetch_snapshot(); callers poll
    GET /api/research/competitor/snapshots for results.
    """
    _check_feature(brand_id)

    if not urls:
        raise SpiderError("urls must be non-empty")

    snapshot_ids = []

    for url in urls:
        result = get_db().from_("competitor_snapshots").insert({
            "brand_id": brand_id,
            "url": url,
            "status": "pending",
        }).execute()
        if result.data:
            snapshot_ids.append(result.data[0]["id"])

    # Trigger async fetch in background
    import threading
    for i, snap_id in enumerate(snapshot_ids):
        t = threading.Thread(
            target=_fetch_snapshot,
            args=(snap_id, urls[i]),
            daemon=True,
        )
        t.start()

    return snapshot_ids


def _fetch_snapshot(snapshot_id: str, url: str) -> None:
    """Fetch a competitor URL using Scrapling and store the result."""
    try:
        get_db().from_("competitor_snapshots").update({"status": "running"}).eq("id", snapshot_id).execute()

        content, title, metadata = _scrape(url)

        get_db().from_("competitor_snapshots").update({
            "status": "completed",
            "title": title,
            "content": content,
            "metadata": metadata,
            "captured_at": "now()",
        }).eq("id", snapshot_id).execute()
    except Exception as exc:
        logger.error("Snapshot %s failed for %s: %s", snapshot_id, url, exc)
        get_db().from_("competitor_snapshots").update({
            "status": "failed",
            "error": str(exc),
        }).eq("id", snapshot_id).execute()


def _scrape(url: str) -> tuple[str, Optional[str], dict]:
    """Scrape a URL with Scrapling. Returns (content, title, metadata)."""
    try:
        from scrapling import Fetcher
        page = Fetcher().get(url)
        title = page.find("title").text if page.find("title") else None
        # Extract main text content
        body = page.find("body")
        content = body.get_all_text(separator="\n") if body else page.get_all_text()
        metadata = {
            "status_code": getattr(page, "status", None),
            "url": url,
            "content_length": len(content),
        }
        return content[:50_000], title, metadata  # cap at 50k chars
    except ImportError:
        # Scrapling not installed yet — fall back to httpx
        import httpx
        resp = httpx.get(url, follow_redirects=True, timeout=30.0, headers={
            "User-Agent": "Mozilla/5.0 (compatible; ContentEngine/1.0)"
        })
        resp.raise_for_status()
        import re
        title_match = re.search(r"<title[^>]*>([^<]+)</title>", resp.text, re.I)
        title = title_match.group(1).strip() if title_match else None
        # Strip HTML tags for content
        content = re.sub(r"<[^>]+>", " ", resp.text)
        content = re.sub(r"\s+", " ", content).strip()[:50_000]
        return content, title, {"status_code": resp.status_code, "url": url}


def get_snapshots(brand_id: str, url: Optional[str] = None, limit: int = 20) -> list[dict]:
    """Return snapshots for a brand, optionally filtered by URL."""
    _check_feature(brand_id)
    query = (
        get_db()
        .from_("competitor_snapshots")
        .select("id, url, title, status, captured_at, created_at, error")
        .eq("brand_id", brand_id)
        .order("created_at", desc=True)
        .limit(limit)
    )
    if url:
        query = query.eq("url", url)
    result = query.execute()
    return result.data or []
