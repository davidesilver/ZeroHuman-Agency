"""Security and resilience utilities.

H-07: Prompt sanitization to prevent indirect prompt injection.
H-08: Timeout guard / circuit-break helper for external HTTP calls.
"""

from __future__ import annotations

import logging
import re
import time
from collections import defaultdict

import httpx

_logger = logging.getLogger("content_engine.security")

# ── H-07: Prompt Injection Sanitization ─────────────────────────────────────

# Patterns that suggest a prompt injection attempt in user-controlled input
_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions?", re.IGNORECASE),
    re.compile(r"ignore\s+(all\s+)?prior\s+instructions?", re.IGNORECASE),
    re.compile(r"forget\s+(everything|all)\s+(you\s+)?know", re.IGNORECASE),
    re.compile(r"new\s+system\s+prompt", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+a", re.IGNORECASE),
    re.compile(r"act\s+as\s+(a|an)\s+\w+(?:\s+without\s+restrictions?)?", re.IGNORECASE),
    re.compile(r"disregard\s+(your\s+)?(previous|prior|all)\s+", re.IGNORECASE),
    re.compile(r"override\s+(your\s+)?instructions?", re.IGNORECASE),
    re.compile(r"<\s*/?system\s*>", re.IGNORECASE),         # XML-style system tags
    re.compile(r"\[\s*INST\s*\]|\[\/INST\]", re.IGNORECASE),  # Llama instruction tokens
]

# Max length for any single user-controlled field inserted into a prompt
MAX_FIELD_LENGTH = 4000


def sanitize_for_prompt(text: str, *, context: str = "") -> str:
    """H-07: Sanitize a user-controlled or web-scraped string before LLM injection.

    Strategy:
    1. Truncate to MAX_FIELD_LENGTH to bound prompt size
    2. Detect and redact known injection patterns
    3. Escape angle brackets to prevent XML-tag injections

    Args:
        text: The string to sanitize.
        context: Description of where this text comes from (for logging).

    Returns:
        Sanitized string safe to embed in an LLM prompt.
    """
    if not text:
        return ""

    # 1. Truncate
    if len(text) > MAX_FIELD_LENGTH:
        _logger.debug(
            "Truncating field from %d to %d chars%s",
            len(text), MAX_FIELD_LENGTH, f" ({context})" if context else "",
        )
        text = text[:MAX_FIELD_LENGTH] + "…"

    # 2. Detect injection patterns
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            _logger.warning(
                "Potential prompt injection detected%s — pattern: %r",
                f" in {context}" if context else "",
                pattern.pattern,
            )
            # Redact the matched portion rather than dropping the entire text
            text = pattern.sub("[REDACTED]", text)

    # 3. Escape XML-ish angle brackets (prevent </system> attacks)
    text = text.replace("<", "\u003c").replace(">", "\u003e")

    return text


# ── H-08: External API Circuit Breaker ───────────────────────────────────────

class CircuitOpenError(Exception):
    """Raised when a circuit breaker is open (service considered down)."""


class CircuitBreaker:
    """Simple in-memory circuit breaker for external HTTP APIs.

    State machine:
        CLOSED  → normal operation
        OPEN    → service is down, fast-fail for `reset_timeout` seconds
        HALF    → after reset_timeout, allow one probe request through

    Args:
        name:           Identifier for this breaker (used in logs).
        failure_threshold:  Consecutive failures before opening.
        reset_timeout:  Seconds to wait before probing again.
    """

    _instances: dict[str, "CircuitBreaker"] = {}

    def __init__(self, name: str, *, failure_threshold: int = 5, reset_timeout: float = 60.0):
        self.name = name
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self._failures = 0
        self._opened_at: float | None = None
        self._state = "CLOSED"

    @classmethod
    def for_service(cls, name: str, **kwargs) -> "CircuitBreaker":
        """Get or create a singleton breaker for a named service."""
        if name not in cls._instances:
            cls._instances[name] = cls(name, **kwargs)
        return cls._instances[name]

    @property
    def state(self) -> str:
        if self._state == "OPEN" and self._opened_at is not None:
            if time.monotonic() - self._opened_at >= self.reset_timeout:
                self._state = "HALF"
        return self._state

    def record_success(self) -> None:
        self._failures = 0
        self._state = "CLOSED"
        self._opened_at = None

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self.failure_threshold:
            if self._state != "OPEN":
                _logger.warning(
                    "Circuit breaker OPEN for %s after %d failures",
                    self.name, self._failures,
                )
            self._state = "OPEN"
            self._opened_at = time.monotonic()

    async def call(self, coro) -> object:
        """Execute `coro` if circuit is not open; record success/failure."""
        if self.state == "OPEN":
            raise CircuitOpenError(
                f"Circuit breaker OPEN for {self.name} — "
                f"try again in {self.reset_timeout:.0f}s"
            )
        try:
            result = await coro
            self.record_success()
            return result
        except (httpx.TimeoutException, httpx.ConnectError) as exc:
            self.record_failure()
            _logger.warning("External call failed for %s: %s", self.name, exc)
            raise
        except Exception:
            # Non-network errors don't count against the circuit
            raise


# Pre-instantiated breakers for known external services
serper_breaker = CircuitBreaker.for_service("serper", failure_threshold=5, reset_timeout=120.0)
openrouter_breaker = CircuitBreaker.for_service("openrouter", failure_threshold=3, reset_timeout=60.0)
youtube_breaker = CircuitBreaker.for_service("youtube", failure_threshold=5, reset_timeout=120.0)
resend_breaker = CircuitBreaker.for_service("resend", failure_threshold=3, reset_timeout=300.0)
