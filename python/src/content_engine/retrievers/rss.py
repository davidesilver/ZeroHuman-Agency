"""Trusted Source Retriever — RSS feed parser. No LLM needed."""

from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser

from ..models import ResearchItemCreate, RetrieverType, SourceType
from .base import BaseRetriever


class RSSRetriever(BaseRetriever):
    retriever_type = RetrieverType.TRUSTED_SOURCE

    async def fetch(self, config: dict) -> list[ResearchItemCreate]:
        feeds: list[dict] = config.get("feeds", [])
        max_age_hours: int = config.get("max_age_hours", 48)
        max_items: int = config.get("max_items", 100)
        cutoff = datetime.now(timezone.utc).timestamp() - (max_age_hours * 3600)

        items: list[ResearchItemCreate] = []
        for feed_cfg in feeds:
            url = feed_cfg.get("url", "")
            source_name = feed_cfg.get("name", url)
            language = feed_cfg.get("language", "en")
            if not url:
                continue
            try:
                parsed = feedparser.parse(url)
                for entry in parsed.entries:
                    pub_dt = self._parse_date(entry)
                    if pub_dt and pub_dt.timestamp() < cutoff:
                        continue
                    link = entry.get("link", "")
                    title = entry.get("title", "")
                    if not link or not title:
                        continue
                    summary = entry.get("summary", entry.get("description", ""))[:500]
                    items.append(
                        ResearchItemCreate(
                            brand_id=self.brand_id,
                            run_id=self.run_id,
                            retriever=self.retriever_type,
                            source_type=SourceType.ARTICLE,
                            title=title.strip(),
                            url=link.strip(),
                            source_name=source_name,
                            author=entry.get("author"),
                            summary=summary,
                            published_at=pub_dt,
                            language=language,
                        )
                    )
            except Exception:
                continue
            if len(items) >= max_items:
                break
        return items[:max_items]

    @staticmethod
    def _parse_date(entry: dict) -> datetime | None:
        for field in ("published", "updated"):
            raw = entry.get(field)
            if raw:
                try:
                    return parsedate_to_datetime(raw)
                except Exception:
                    pass
            parsed = entry.get(f"{field}_parsed")
            if parsed:
                try:
                    from time import mktime
                    return datetime.fromtimestamp(mktime(parsed), tz=timezone.utc)
                except Exception:
                    pass
        return None
