from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pydantic import BaseModel, Field
from uuid import UUID, uuid4


class RetrieverType(StrEnum):
    SEMANTIC = "semantic"
    PRACTITIONER = "practitioner"
    TRUSTED_SOURCE = "trusted_source"
    KEYWORD = "keyword"
    TREND = "trend"
    MANUAL = "manual"
    RSS = "rss"
    YOUTUBE = "youtube"
    GMAIL = "gmail"
    X = "x"
    DUCKDUCKGO = "duckduckgo"
    TAVILY = "tavily"


class ItemStatus(StrEnum):
    NEW = "new"
    SCORED = "scored"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class RunStatus(StrEnum):
    RUNNING = "running"
    SCORING = "scoring"
    COMPLETED = "completed"
    FAILED = "failed"


class SourceType(StrEnum):
    RSS = "rss"
    SEARCH = "search"
    YOUTUBE = "youtube"
    SCRAPE = "scrape"


class ResearchItemCreate(BaseModel):
    brand_id: str
    run_id: str
    retriever: RetrieverType
    source_type: SourceType = SourceType.SEARCH
    title: str
    url: str
    source_name: str = ""
    author: str | None = None
    summary: str = ""
    content_snippet: str = ""
    published_at: datetime | None = None
    language: str = "en"
    metadata: dict | None = None


class ScoreResult(BaseModel):
    applicability: float = Field(ge=0, le=10)
    credibility: float = Field(ge=0, le=10)
    alignment: float = Field(ge=0, le=10)
    trend_prediction: float = Field(ge=0, le=10)
    italy_relevance: float = Field(ge=0, le=10)
    feedback_bonus: float = Field(ge=0, le=10, default=0)
    reasoning: str = ""


class RetrieverResult(BaseModel):
    retriever: RetrieverType
    items: list[ResearchItemCreate]
    duration_ms: int = 0
    errors: list[str] = []


class ResearchRunResult(BaseModel):
    run_id: str
    status: RunStatus
    total_items_found: int = 0
    items_after_dedup: int = 0
    retriever_stats: dict[str, dict] = {}
    duration_seconds: float = 0


class TriggerRequest(BaseModel):
    retrievers: list[RetrieverType] | None = None
    force: bool = False
    max_items_per_retriever: int = 100
    dedup_threshold: float = 0.85


class ScoringRequest(BaseModel):
    run_id: str | None = None
    item_ids: list[str] | None = None
