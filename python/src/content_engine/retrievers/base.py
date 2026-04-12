from __future__ import annotations

import time
from abc import ABC, abstractmethod

from ..models import ResearchItemCreate, RetrieverResult, RetrieverType


class BaseRetriever(ABC):
    retriever_type: RetrieverType

    def __init__(self, brand_id: str, run_id: str):
        self.brand_id = brand_id
        self.run_id = run_id

    async def execute(self, config: dict) -> RetrieverResult:
        start = time.monotonic()
        errors: list[str] = []
        items: list[ResearchItemCreate] = []
        try:
            items = await self.fetch(config)
        except Exception as e:
            errors.append(f"{self.retriever_type}: {e}")
        elapsed = int((time.monotonic() - start) * 1000)
        return RetrieverResult(
            retriever=self.retriever_type,
            items=items,
            duration_ms=elapsed,
            errors=errors,
        )

    @abstractmethod
    async def fetch(self, config: dict) -> list[ResearchItemCreate]:
        ...
