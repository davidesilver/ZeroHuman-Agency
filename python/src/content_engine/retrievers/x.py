"""X/Twitter Retriever — searches recent tweets via X API v2.

CLI path (PrintingPress x-twitter):
    Install:  npm install -g @printingpress/x-twitter   (or per printingpress.dev docs)
    Binary:   x-twitter  (or override via PP_X_TWITTER_BIN env var)
    Command:  x-twitter search "<query>" --max-results <n>
    Output:   JSON array of tweet objects with fields:
                id, text, created_at, url,
                author.username (or username at top level)

    If the binary is not installed, falls back to direct X API v2 via urllib.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

from ..models import ResearchItemCreate, RetrieverType, SourceType
from ..utils.cli_runner import CLINotFoundError, run_cli
from .base import BaseRetriever

logger = logging.getLogger(__name__)

_X_SEARCH_URL = "https://api.twitter.com/2/tweets/search/recent"
_CLI_BINARY_ENV = "PP_X_TWITTER_BIN"
_CLI_BINARY_DEFAULT = "x-twitter"


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

        query = _build_query(topics, x_accounts)
        if not query:
            logger.warning("XRetriever: no topics or accounts configured — skipping")
            return []

        binary = os.environ.get(_CLI_BINARY_ENV, _CLI_BINARY_DEFAULT)
        try:
            raw = await run_cli(
                binary,
                ["search", query, "--max-results", str(min(100, max_items))],
                env_extra={"X_BEARER_TOKEN": bearer_token},
            )
            return _parse_cli_output(raw, self.brand_id, self.run_id, self.retriever_type, max_items)
        except CLINotFoundError:
            logger.debug("XRetriever: CLI '%s' not found — using direct API", binary)
        except Exception as exc:
            logger.warning("XRetriever: CLI failed (%s) — using direct API", exc)

        return await _fetch_direct(bearer_token, query, max_items, self.brand_id, self.run_id, self.retriever_type)


# ---------------------------------------------------------------------------
# CLI output parsing
# ---------------------------------------------------------------------------

def _parse_cli_output(
    raw: Any,
    brand_id: str,
    run_id: str,
    retriever_type: RetrieverType,
    max_items: int,
) -> list[ResearchItemCreate]:
    if not isinstance(raw, list):
        raw = raw.get("data", []) if isinstance(raw, dict) else []

    items: list[ResearchItemCreate] = []
    for tweet in raw[:max_items]:
        tweet_id = tweet.get("id", "")
        text = tweet.get("text", "")
        if not tweet_id or not text:
            continue

        # author may be nested or flat
        author_obj = tweet.get("author") or {}
        username = (
            author_obj.get("username")
            or tweet.get("username")
            or tweet.get("author_id", tweet_id)
        )

        url = tweet.get("url") or f"https://twitter.com/i/web/status/{tweet_id}"

        published_at: datetime | None = None
        raw_date = tweet.get("created_at")
        if raw_date:
            try:
                published_at = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
            except Exception:
                published_at = datetime.now(timezone.utc)

        try:
            items.append(
                ResearchItemCreate(
                    brand_id=brand_id,
                    run_id=run_id,
                    retriever=retriever_type,
                    source_type=SourceType.SCRAPE,
                    title=text[:100].replace("\n", " "),
                    url=url,
                    source_name=f"@{username}",
                    summary=text[:500],
                    published_at=published_at,
                    language="en",
                )
            )
        except Exception as exc:
            logger.debug("XRetriever: skipping tweet %s: %s", tweet_id, exc)

    return items


# ---------------------------------------------------------------------------
# Direct X API v2 fallback (original implementation)
# ---------------------------------------------------------------------------

async def _fetch_direct(
    bearer_token: str,
    query: str,
    max_items: int,
    brand_id: str,
    run_id: str,
    retriever_type: RetrieverType,
) -> list[ResearchItemCreate]:
    import json as _json
    import urllib.parse
    import urllib.request

    per_request = max(10, min(100, max_items))
    params: dict[str, Any] = {
        "query": query,
        "max_results": per_request,
        "tweet.fields": "created_at,author_id,public_metrics",
        "expansions": "author_id",
        "user.fields": "username,name",
    }

    try:
        url = f"{_X_SEARCH_URL}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {bearer_token}"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data: dict = _json.loads(resp.read())
    except Exception as exc:
        logger.warning("XRetriever: direct API request failed: %s", exc)
        return []

    tweets: list[dict] = data.get("data", [])
    if not tweets:
        return []

    user_lookup: dict[str, dict] = {
        u.get("id", ""): u
        for u in data.get("includes", {}).get("users", [])
    }

    items: list[ResearchItemCreate] = []
    for tweet in tweets[:max_items]:
        tweet_id = tweet.get("id", "")
        text = tweet.get("text", "")
        if not tweet_id or not text:
            continue

        author_id = tweet.get("author_id", "")
        username = user_lookup.get(author_id, {}).get("username", author_id)

        published_at: datetime | None = None
        raw_date = tweet.get("created_at")
        if raw_date:
            try:
                published_at = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
            except Exception:
                published_at = datetime.now(timezone.utc)

        try:
            items.append(
                ResearchItemCreate(
                    brand_id=brand_id,
                    run_id=run_id,
                    retriever=retriever_type,
                    source_type=SourceType.SCRAPE,
                    title=text[:100].replace("\n", " "),
                    url=f"https://twitter.com/i/web/status/{tweet_id}",
                    source_name=f"@{username}",
                    summary=text[:500],
                    published_at=published_at,
                    language="en",
                )
            )
        except Exception as exc:
            logger.debug("XRetriever: skipping tweet %s: %s", tweet_id, exc)

    return items


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_query(topics: list[str], accounts: list[str]) -> str:
    parts: list[str] = []
    if topics:
        topic_clause = " OR ".join(topics)
        parts.append(f"({topic_clause})" if len(topics) > 1 else topic_clause)
    if accounts:
        account_clause = " OR ".join(f"from:{h.lstrip('@')}" for h in accounts)
        parts.append(f"({account_clause})" if len(accounts) > 1 else account_clause)
    return " ".join(parts)
