"""
LLM API Rate Limiting System

Implements token bucket algorithm for fair and efficient rate limiting
across multiple LLM API endpoints and models. Prevents API quota exhaustion
and service degradation under load.

Critical for production reliability: ensures system remains stable
even under high request volumes to LLM providers.

This is separate from the IP-based rate limiting middleware and specifically
handles API provider rate limits (Anthropic, OpenRouter, OpenAI, etc.).

Author: AI Engineering Team
Created: 2026-04-16
"""

import time
import asyncio
from typing import Dict, Optional
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class RateLimitStrategy(Enum):
    """Rate limiting strategies."""

    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting.

    Attributes:
        max_requests: Maximum number of requests allowed in the time window
        window_seconds: Time window in seconds
        strategy: Rate limiting strategy to use
    """

    max_requests: int
    window_seconds: int
    strategy: RateLimitStrategy = RateLimitStrategy.TOKEN_BUCKET


@dataclass
class TokenBucket:
    """Token bucket implementation for rate limiting.

    The token bucket algorithm allows bursts while maintaining
    a long-term rate limit. Tokens are added at a constant rate,
    and requests consume tokens. If no tokens are available,
    requests are rate limited.

    This implementation is async-safe and suitable for ASGI applications.
    """

    capacity: float
    refill_rate: float
    tokens: float = field(default_factory=float)
    last_refill: float = field(default_factory=time.time)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def consume(self, tokens: float = 1.0) -> bool:
        """
        Consume tokens if available.

        Args:
            tokens: Number of tokens to consume (default: 1.0)

        Returns:
            True if tokens were consumed, False if rate limited
        """
        async with self._lock:
            self._refill()

            if self.tokens >= tokens:
                self.tokens -= tokens
                logger.debug(f"Consumed {tokens} tokens, {self.tokens:.2f} remaining")
                return True

            logger.debug(f"Rate limited: need {tokens} tokens, only {self.tokens:.2f} available")
            return False

    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill

        # Calculate tokens to add (rate * time)
        tokens_to_add = elapsed * self.refill_rate

        # Add tokens, but don't exceed capacity
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now

    def wait_time(self, tokens: float = 1.0) -> float:
        """
        Calculate wait time until tokens are available.

        Args:
            tokens: Number of tokens needed

        Returns:
            Wait time in seconds (0.0 if tokens available now)
        """
        self._refill()

        if self.tokens >= tokens:
            return 0.0

        # Calculate time needed to refill enough tokens
        deficit = tokens - self.tokens
        return deficit / self.refill_rate


class RateLimiter:
    """
    Thread-safe and async-safe rate limiter using token bucket algorithm.

    Supports multiple independent rate limits (e.g., per-model, per-endpoint).
    Each limit has its own token bucket and configuration.

    Example:
        >>> limiter = RateLimiter()
        >>> limiter.configure_limit("anthropic", RateLimitConfig(50, 60))
        >>> if await limiter.acquire("anthropic"):
        ...     # Make API call
        ...     pass
    """

    def __init__(self):
        self._limits: Dict[str, RateLimitConfig] = {}
        self._buckets: Dict[str, TokenBucket] = {}
        self._lock = asyncio.Lock()

    def configure_limit(self, key: str, config: RateLimitConfig):
        """
        Configure a rate limit for a specific key.

        Args:
            key: Identifier for this rate limit (e.g., "anthropic", "openrouter")
            config: Rate limit configuration
        """
        self._limits[key] = config

        if config.strategy == RateLimitStrategy.TOKEN_BUCKET:
            # Calculate refill rate: tokens per second
            refill_rate = config.max_requests / config.window_seconds

            self._buckets[key] = TokenBucket(
                capacity=config.max_requests,
                refill_rate=refill_rate,
            )

            logger.info(
                f"Configured rate limit for '{key}': "
                f"{config.max_requests} requests/{config.window_seconds}s "
                f"(token bucket: {refill_rate:.2f} tokens/sec)"
            )

    async def acquire(self, key: str, tokens: float = 1.0) -> bool:
        """
        Attempt to acquire tokens from the rate limiter.

        Args:
            key: Rate limit key to acquire from
            tokens: Number of tokens to acquire (default: 1.0)

        Returns:
            True if tokens acquired, False if rate limited
        """
        if key not in self._limits:
            logger.warning(f"No rate limit configured for key: {key}, allowing request")
            return True

        config = self._limits[key]

        if config.strategy == RateLimitStrategy.TOKEN_BUCKET:
            bucket = self._buckets.get(key)
            if not bucket:
                logger.error(f"Token bucket not found for key: {key}")
                return False

            acquired = await bucket.consume(tokens)

            if not acquired:
                wait_time = bucket.wait_time(tokens)
                logger.warning(
                    f"Rate limited for '{key}': {tokens} tokens needed, "
                    f"wait time: {wait_time:.2f}s"
                )

            return acquired

        return False

    async def wait_until_available(
        self,
        key: str,
        tokens: float = 1.0,
        timeout: Optional[float] = None
    ):
        """
        Wait until tokens are available.

        This method blocks until tokens are available or timeout is exceeded.

        Args:
            key: Rate limit key to wait for
            tokens: Number of tokens needed
            timeout: Maximum wait time in seconds (None = no timeout)

        Raises:
            TimeoutError: If timeout is exceeded
        """
        if key not in self._limits:
            return

        start_time = time.time()

        while True:
            if await self.acquire(key, tokens):
                return

            if timeout and (time.time() - start_time) > timeout:
                raise TimeoutError(f"Rate limit timeout exceeded for key: {key}")

            # Wait before retrying (exponential backoff)
            wait_time = self.get_wait_time(key, tokens)
            await asyncio.sleep(min(wait_time, 1.0))  # Cap at 1 second

    def get_wait_time(self, key: str, tokens: float = 1.0) -> float:
        """
        Get estimated wait time until tokens are available.

        Args:
            key: Rate limit key
            tokens: Number of tokens needed

        Returns:
            Wait time in seconds (0.0 if tokens available now)
        """
        if key not in self._limits:
            return 0.0

        bucket = self._buckets.get(key)
        if not bucket:
            return 0.0

        return bucket.wait_time(tokens)

    def get_status(self, key: str) -> Dict[str, any]:
        """
        Get current status of a rate limit.

        Args:
            key: Rate limit key

        Returns:
            Dictionary with current status information
        """
        if key not in self._limits:
            return {"configured": False}

        config = self._limits[key]
        bucket = self._buckets.get(key)

        if not bucket:
            return {"configured": True, "bucket": None}

        return {
            "configured": True,
            "max_requests": config.max_requests,
            "window_seconds": config.window_seconds,
            "strategy": config.strategy.value,
            "tokens_available": bucket.tokens,
            "tokens_capacity": bucket.capacity,
            "utilization_pct": (1 - bucket.tokens / bucket.capacity) * 100,
        }


# Global rate limiter instance
rate_limiter = RateLimiter()

# Configure default limits based on typical API quotas
# Adjust these based on your actual API plans

# Anthropic Claude API (typical limits)
rate_limiter.configure_limit(
    "anthropic",
    RateLimitConfig(
        max_requests=50,  # 50 requests per minute
        window_seconds=60,
        strategy=RateLimitStrategy.TOKEN_BUCKET
    )
)

# OpenRouter API (free tier limits)
rate_limiter.configure_limit(
    "openrouter",
    RateLimitConfig(
        max_requests=100,  # 100 requests per minute (free tier)
        window_seconds=60,
        strategy=RateLimitStrategy.TOKEN_BUCKET
    )
)

# OpenAI API (typical limits)
rate_limiter.configure_limit(
    "openai",
    RateLimitConfig(
        max_requests=60,  # 60 requests per minute
        window_seconds=60,
        strategy=RateLimitStrategy.TOKEN_BUCKET
    )
)

logger.info("LLM rate limiter initialized with default limits for anthropic, openrouter, and openai")


# Export key components
__all__ = [
    'RateLimiter',
    'RateLimitConfig',
    'RateLimitStrategy',
    'TokenBucket',
    'rate_limiter',
]
