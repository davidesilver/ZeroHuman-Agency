"""LLMProvider interface.

All providers (OpenRouter, OpenClaw, Anthropic direct) must implement this ABC.
The interface is intentionally minimal — extend as Phase 14 (OpenClaw POC) requires.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class LLMRequest:
    prompt: str
    system_prompt: Optional[str] = None
    model: Optional[str] = None          # None = provider picks the default
    temperature: float = 0.7
    task_type: str = "creative"
    brand_id: str = ""
    context: str = "general"
    action: str = "call_llm"
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResult:
    content: str
    model_used: str
    provider: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: Optional[int] = None
    cost_usd: Optional[float] = None
    is_fallback: bool = False
    error: Optional[str] = None


class LLMProvider(ABC):
    """Abstract LLM provider interface."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique provider identifier (e.g. 'openrouter', 'openclaw')."""

    @abstractmethod
    def complete(self, request: LLMRequest) -> LLMResult:
        """Execute a chat completion and return a structured result."""

    def is_available(self, brand_id: str) -> bool:
        """Return True if this provider is configured for the given brand.

        Default implementation: always available (override to check brand_integrations).
        """
        return True
