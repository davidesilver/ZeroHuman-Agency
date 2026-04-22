"""X/Twitter Retriever — searches recent tweets via X API v2."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

from ..models import ResearchItemCreate, RetrieverType, SourceType
from .base import BaseRetriever

logger = logging.getLogger(__name__)

_X_SEARCH_URL = "https://api.twitter.com/2/tweets/search/recent"


class XRetriever(BaseRetriever):
    retriever_type = RetrieverType.X

    async def fetch(self, config: dict) -> list[ResearchItemCreate]:
        bearer_token = os.environ.get("X_BEARER_TOKEN", "").strip()

        if not bearer_token:
            logger.warning("X_BEARER_TOKEN not configured — XRetriever skipped")
            return []

        x_accounts: list[str] = config.get("x_accounts", [])
        topics: list[str] = config.get("topics", [])
        max_items: int = int(config.get("max_items", 30))
        days_back: int = int(config.get("days_back", 3))  # noqa: F841 — kept for future start_time filtering

        # Build query string
        query = _build_query(topics, x_accounts)
        if not query:
            logger.warning("XRetriever: no topics or accounts configured — skipping")
            return []

        # Clamp per-request max_results to API limits (10–100)
        per_request = max(10, min(100, max_items))

        params: dict[str, Any] = {
            "query": query,
            "max_results": per_request,
            "tweet.fields": "created_at,author_id,public_metrics",
            "expansions": "author_id",
            "user.fields": "username,name",
        }

        try:
            import urllib.request
            import urllib.parse
            import json as _json

            headers = {"Authorization": f"Bearer {bearer_token}"}
            url = f"{_X_SEARCH_URL}?{urllib.parse.urlencode(params)}"

            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read()
            data: dict = _json.loads(raw)
        except Exception as exc:
            logger.warning("XRetriever: HTTP request failed: %s", exc)
            return []

        tweets: list[dict] = data.get("data", [])
        if not tweets:
            return []

        # Build user lookup: author_id -> {username, name}
        user_lookup: dict[str, dict] = {}
        for user in data.get("includes", {}).get("users", []):
            user_lookup[user.get("id", "")] = user

        items: list[ResearchItemCreate] = []
        for tweet in tweets[:max_items]:
            tweet_id: str = tweet.get("id", "")
            text: str = tweet.get("text", "")
            created_at_raw: str | None = tweet.get("created_at")
            author_id: str = tweet.get("author_id", "")

            if not tweet_id or not text:
                continue

            published_at: datetime | None = None
            if created_at_raw:
                try:
                    published_at = datetime.fromisoformat(created_at_raw.replace("Z", "+00:00"))
                except Exception:
                    published_at = datetime.now(timezone.utc)

            user_info = user_lookup.get(author_id, {})
            username: str = user_info.get("username", author_id)
            source_name = f"@{username}"

            tweet_url = f"https://twitter.com/i/web/status/{tweet_id}"
            title = text[:100].replace("\n", " ")
            summary = text[:500]

            try:
                items.append(
                    ResearchItemCreate(
                        brand_id=self.brand_id,
                        run_id=self.run_id,
                        retriever=self.retriever_type,
                        source_type=SourceType.SCRAPE,
                        title=title,
                        url=tweet_url,
                        source_name=source_name,
                        summary=summary,
                        published_at=published_at,
                        language="en",
                    )
                )
            except Exception as exc:
                logger.debug("XRetriever: failed to create ResearchItemCreate for tweet %s: %s", tweet_id, exc)
                continue

        return items


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_query(topics: list[str], accounts: list[str]) -> str:
    """Assemble an X API v2 query string from topics and account handles."""
    parts: list[str] = []

    if topics:
        topic_clause = " OR ".join(topics)
        parts.append(f"({topic_clause})" if len(topics) > 1 else topic_clause)

    if accounts:
        account_clause = " OR ".join(f"from:{handle.lstrip('@')}" for handle in accounts)
        parts.append(f"({account_clause})" if len(accounts) > 1 else account_clause)

    return " ".join(parts)
