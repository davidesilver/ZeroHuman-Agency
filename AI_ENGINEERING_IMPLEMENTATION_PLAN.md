# 🚀 AI Engineering Implementation Plan

**Author:** AI Engineer Agent
**Date:** 2026-04-16
**Status:** 📋 Ready for Implementation
**Priority:** Production Readiness

---

## 🎯 Executive Summary

Based on comprehensive audit analysis, this implementation plan addresses **REAL production risks** while fixing genuine technical issues. The plan prioritizes operational concerns over code cosmetics, focusing on system reliability, observability, and cost management.

**Critical Insight:** The original audit identified 60% real issues and 40% over-prioritized concerns. This plan re-prioritizes based on **actual production impact**.

---

## 📊 Priority Matrix

| Priority | Issues | Production Impact | Implementation Time |
|----------|--------|-------------------|---------------------|
| 🔴 CRITICAL | JSON parsing, Rate limiting, Cost tracking | System crashes, cost overruns | 2-3 days |
| 🟠 HIGH | Graceful degradation, Fallback metrics | Poor user experience, blind spots | 1-2 days |
| 🟡 MEDIUM | Parallel retry strategy, DRY cleanup | Improved reliability, maintenance | 2-3 days |
| 🟢 LOW | Database optimization, Thread safety | Marginal performance gains | 1-2 days |

---

## 🔴 PHASE 1: CRITICAL PRODUCTION FIXES (Week 1)

### 1.1 Fix JSON Parsing Vulnerability

**Problem:** Current parser fails on nested code blocks inside JSON strings.

**Impact:** System crashes when LLM generates valid JSON with code blocks in string fields.

**Implementation:**

```python
# File: python/src/content_engine/utils/json_parser.py (NEW)

import re
import json
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class RobustJSONParser:
    """Robust JSON parser that handles nested code blocks and LLM artifacts."""

    MAX_RETRIES = 3
    TIMEOUT_SECONDS = 30

    @staticmethod
    def parse_llm_response(
        text: str,
        context: str = "unknown",
        allow_partial: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Parse JSON from LLM response with multiple fallback strategies.

        Args:
            text: Raw LLM response text
            context: Context for error logging
            allow_partial: If True, attempt to extract partial JSON on failure

        Returns:
            Parsed JSON dict or None if all strategies fail
        """
        strategies = [
            RobustJSONParser._try_direct_parse,
            RobustJSONParser._try_strip_outer_fences,
            RobustJSONParser._try_extract_first_json,
            RobustJSONParser._try_regex_extraction,
        ]

        for i, strategy in enumerate(strategies):
            try:
                result = strategy(text)
                if result:
                    logger.info(f"JSON parse success using strategy {i+1} for context: {context}")
                    return result
            except Exception as e:
                logger.warning(f"Strategy {i+1} failed for context {context}: {str(e)}")
                continue

        # All strategies failed
        logger.error(f"All JSON parsing strategies failed for context: {context}")
        if allow_partial:
            return RobustJSONParser._try_partial_extraction(text)
        return None

    @staticmethod
    def _try_direct_parse(text: str) -> Optional[Dict[str, Any]]:
        """Strategy 1: Direct JSON parse (fastest path)."""
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _try_strip_outer_fences(text: str) -> Optional[Dict[str, Any]]:
        """
        Strategy 2: Strip outer markdown fences only.

        Unlike the original rsplit, this only removes the outermost fences.
        """
        text = text.strip()

        # Remove ```json or ```python opening
        if text.startswith('```'):
            # Find first newline after opening fence
            first_newline = text.find('\n')
            if first_newline != -1:
                text = text[first_newline + 1:]

        # Remove closing ``` (only the last one)
        if text.endswith('```'):
            last_fence = text.rfind('```')
            if last_fence != -1:
                text = text[:last_fence]

        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _try_extract_first_json(text: str) -> Optional[Dict[str, Any]]:
        """
        Strategy 3: Extract first complete JSON object using brace counting.

        This handles cases where JSON is embedded in conversational text.
        """
        text = text.strip()

        brace_depth = 0
        start_idx = -1
        in_string = False
        escape_next = False

        for i, char in enumerate(text):
            if escape_next:
                escape_next = False
                continue

            if char == '\\':
                escape_next = True
                continue

            if char == '"' and not escape_next:
                in_string = not in_string
                continue

            if in_string:
                continue

            if char == '{' and brace_depth == 0:
                start_idx = i

            if char == '{':
                brace_depth += 1
            elif char == '}':
                brace_depth -= 1
                if brace_depth == 0 and start_idx != -1:
                    # Found complete JSON object
                    json_text = text[start_idx:i+1]
                    try:
                        return json.loads(json_text)
                    except json.JSONDecodeError:
                        continue

        return None

    @staticmethod
    def _try_regex_extraction(text: str) -> Optional[Dict[str, Any]]:
        """
        Strategy 4: Regex-based extraction of JSON patterns.

        More permissive but can capture malformed JSON.
        """
        # Pattern to match JSON objects (with some flexibility)
        json_pattern = r'\{(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\}))*\}))*\}'

        matches = re.findall(json_pattern, text, re.DOTALL)

        # Try each match, longest first
        matches.sort(key=len, reverse=True)

        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue

        return None

    @staticmethod
    def _try_partial_extraction(text: str) -> Optional[Dict[str, Any]]:
        """
        Fallback: Extract whatever key-value pairs we can.

        Not ideal, but better than complete failure.
        """
        result = {}

        # Simple pattern for key: value pairs
        pattern = r'"([^"]+)"\s*:\s*("([^"\\]|\\.)*"|[\d.]+|true|false|null|\{[^}]*\})'

        matches = re.findall(pattern, text)

        for key, value, _ in matches:
            try:
                # Try to parse the value
                parsed_value = json.loads(value)
                result[key] = parsed_value
            except:
                # Keep as string if parsing fails
                result[key] = value.strip('"')

        return result if result else None


# Convenience function
def parse_llm_json(text: str, context: str = "unknown") -> Optional[Dict[str, Any]]:
    """Convenience wrapper for RobustJSONParser."""
    return RobustJSONParser.parse_llm_response(text, context)
```

**Integration with god_system.py:**

```python
# File: python/src/content_engine/agents/god_system.py (MODIFIED)

from src.content_engine.utils.json_parser import RobustJSONParser

class GodSystemAgent:
    # ... existing code ...

    async def _parse_json(self, text: str, context: str) -> Dict[str, Any]:
        """Parse JSON with robust error handling and retries."""

        for attempt in range(self.MAX_RETRIES):
            result = RobustJSONParser.parse_llm_response(
                text,
                context=context,
                allow_partial=(attempt == self.MAX_RETRIES - 1)  # Allow partial on last attempt
            )

            if result:
                return result

            # Log failure
            logger.warning(f"JSON parse attempt {attempt + 1}/{self.MAX_RETRIES} failed for {context}")

            # If not last attempt, we could try to get LLM to retry
            # (This would require additional implementation)

        # All retries failed
        logger.error(f"JSON parsing completely failed for {context}")
        raise ValueError(f"Failed to parse JSON response after {self.MAX_RETRIES} attempts")
```

**Testing:**

```python
# File: python/tests/test_json_parser.py (NEW)

import pytest
from src.content_engine.utils.json_parser import RobustJSONParser

def test_nested_code_blocks():
    """Test that parser handles code blocks inside JSON strings."""
    text = '''```json
    {
        "title": "Python Tutorial",
        "body": "Here's an example: \\`\\`\\`python x=1 \\`\\`\\`"
    }
    ```'''
    result = RobustJSONParser.parse_llm_response(text, "test_nested")
    assert result is not None
    assert result["body"] == "Here's an example: ```python x=1 ```"

def test_embedded_in_conversation():
    """Test extraction from conversational text."""
    text = "Here's the analysis:\n{\"score\": 8.5, \"reasoning\": \"Good\"}\nDoes this help?"
    result = RobustJSONParser.parse_llm_response(text, "test_conversation")
    assert result is not None
    assert result["score"] == 8.5

def test_multiple_json_objects():
    """Test that we extract the first valid JSON object."""
    text = '{"invalid": missing} {"valid": true} {"also": false}'
    result = RobustJSONParser.parse_llm_response(text, "test_multiple")
    assert result is not None
    assert result["valid"] is True
```

**Estimated Time:** 4-6 hours

---

### 1.2 Implement Rate Limiting

**Problem:** No rate limiting on LLM API calls. System will break under load.

**Impact:** API quota exhaustion, service degradation, cost overruns.

**Implementation:**

```python
# File: python/src/content_engine/utils/rate_limiter.py (NEW)

import time
import asyncio
from typing import Dict, Optional
from collections import defaultdict
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class RateLimitStrategy(Enum):
    """Rate limiting strategies."""
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"

@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    max_requests: int
    window_seconds: int
    strategy: RateLimitStrategy = RateLimitStrategy.TOKEN_BUCKET

class RateLimiter:
    """
    Thread-safe and async-safe rate limiter using token bucket algorithm.

    Supports multiple independent rate limits (e.g., per-model, per-endpoint).
    """

    def __init__(self):
        self._limits: Dict[str, RateLimitConfig] = {}
        self._buckets: Dict[str, TokenBucket] = {}
        self._lock = asyncio.Lock()

    def configure_limit(self, key: str, config: RateLimitConfig):
        """Configure a rate limit for a specific key."""
        self._limits[key] = config
        if config.strategy == RateLimitStrategy.TOKEN_BUCKET:
            self._buckets[key] = TokenBucket(
                capacity=config.max_requests,
                refill_rate=config.max_requests / config.window_seconds
            )

    async def acquire(self, key: str, tokens: int = 1) -> bool:
        """
        Attempt to acquire tokens from the rate limiter.

        Returns:
            True if tokens acquired, False if rate limited
        """
        if key not in self._limits:
            logger.warning(f"No rate limit configured for key: {key}, allowing request")
            return True

        config = self._limits[key]

        async with self._lock:
            if config.strategy == RateLimitStrategy.TOKEN_BUCKET:
                bucket = self._buckets.get(key)
                if not bucket:
                    logger.error(f"Token bucket not found for key: {key}")
                    return False

                return bucket.consume(tokens)

        return False

    async def wait_until_available(self, key: str, tokens: int = 1, timeout: Optional[float] = None):
        """
        Wait until tokens are available.

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
            await asyncio.sleep(0.1)

    def get_wait_time(self, key: str, tokens: int = 1) -> float:
        """Get estimated wait time until tokens are available."""
        if key not in self._limits:
            return 0.0

        bucket = self._buckets.get(key)
        if not bucket:
            return 0.0

        return bucket.wait_time(tokens)

class TokenBucket:
    """Token bucket algorithm for rate limiting."""

    def __init__(self, capacity: float, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate  # tokens per second
        self.tokens = capacity
        self.last_refill = time.time()
        self._lock = asyncio.Lock()

    async def consume(self, tokens: float) -> bool:
        """Consume tokens if available."""
        async with self._lock:
            self._refill()

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

    def wait_time(self, tokens: float) -> float:
        """Calculate wait time until tokens are available."""
        self._refill()
        if self.tokens >= tokens:
            return 0.0

        deficit = tokens - self.tokens
        return deficit / self.refill_rate


# Global rate limiter instance
rate_limiter = RateLimiter()

# Configure default limits (adjust based on API quotas)
rate_limiter.configure_limit(
    "anthropic",
    RateLimitConfig(
        max_requests=50,  # 50 requests per minute
        window_seconds=60,
        strategy=RateLimitStrategy.TOKEN_BUCKET
    )
)

rate_limiter.configure_limit(
    "openrouter",
    RateLimitConfig(
        max_requests=100,  # 100 requests per minute (free tier)
        window_seconds=60,
        strategy=RateLimitStrategy.TOKEN_BUCKET
    )
)
```

**Integration with llm_client.py:**

```python
# File: python/src/content_engine/utils/llm_client.py (MODIFIED)

from src.content_engine.utils.rate_limiter import rate_limiter, RateLimitStrategy

class LLMClient:
    # ... existing code ...

    async def call_llm(
        self,
        prompt: str,
        task_type: str = "general",
        max_retries: int = 2,
        # ... other parameters
    ) -> LLMResponse:
        """Call LLM with rate limiting."""

        # Determine rate limit key based on model/engine
        rate_limit_key = self._get_rate_limit_key(model)

        # Acquire rate limit
        if not await rate_limiter.acquire(rate_limit_key):
            wait_time = rate_limiter.get_wait_time(rate_limit_key)
            logger.warning(f"Rate limited for {rate_limit_key}, waiting {wait_time:.2f}s")

            # Option 1: Wait (can timeout)
            # await rate_limiter.wait_until_available(rate_limit_key, timeout=30.0)

            # Option 2: Fall back immediately
            return await self._emergency_openrouter_fallback(prompt, task_type, model)

        # Proceed with LLM call
        # ... existing logic ...

    def _get_rate_limit_key(self, model: str) -> str:
        """Map model to rate limit key."""
        if "claude" in model.lower() or "anthropic" in model.lower():
            return "anthropic"
        else:
            return "openrouter"
```

**Monitoring:**

```python
# File: python/src/content_engine/utils/metrics.py (MODIFIED)

class RateLimitMetrics:
    """Track rate limiting statistics."""

    def __init__(self):
        self.requests_total = defaultdict(int)
        self.requests_limited = defaultdict(int)
        self.wait_times = defaultdict(list)

    def record_request(self, key: str, was_limited: bool, wait_time: float = 0.0):
        """Record a rate limit event."""
        self.requests_total[key] += 1
        if was_limited:
            self.requests_limited[key] += 1
            self.wait_times[key].append(wait_time)

    def get_metrics(self, key: str) -> Dict[str, Any]:
        """Get metrics for a key."""
        total = self.requests_total[key]
        limited = self.requests_limited[key]
        wait_times = self.wait_times[key]

        return {
            "total_requests": total,
            "limited_requests": limited,
            "limit_rate": limited / total if total > 0 else 0.0,
            "avg_wait_time": sum(wait_times) / len(wait_times) if wait_times else 0.0,
            "max_wait_time": max(wait_times) if wait_times else 0.0,
        }
```

**Estimated Time:** 3-4 hours

---

### 1.3 Implement Cost Tracking

**Problem:** No visibility into LLM spending. Can't monitor costs or set budgets.

**Impact:** Unexpected costs, inability to optimize spending, no budget alerts.

**Implementation:**

```python
# File: python/src/content_engine/utils/cost_tracker.py (NEW)

import asyncio
from typing import Dict, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import logging
import json

logger = logging.getLogger(__name__)

# Pricing per 1M tokens (adjust based on actual API pricing)
PRICING = {
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
    "claude-opus-4-20250514": {"input": 15.0, "output": 75.0},
    "claude-haiku-4-20250514": {"input": 0.25, "output": 1.25},
    "gpt-4-turbo": {"input": 10.0, "output": 30.0},
    "gpt-4o": {"input": 5.0, "output": 15.0},
    # Add more models as needed
}

@dataclass
class LLMAPIUsage:
    """Track LLM API usage and costs."""
    timestamp: str
    model: str
    tokens_input: int
    tokens_output: int
    cost_input_usd: float
    cost_output_usd: float
    cost_total_usd: float
    latency_ms: int
    task_type: str
    brand_id: str
    agent_name: str

class CostTracker:
    """Track and manage LLM API costs."""

    def __init__(self, storage_path: str = "llm_cost_tracking.json"):
        self.storage_path = storage_path
        self.usage_history: list[LLMAPIUsage] = []
        self._lock = asyncio.Lock()
        self._load_history()

    async def record_usage(
        self,
        model: str,
        tokens_input: int,
        tokens_output: int,
        latency_ms: int,
        task_type: str,
        brand_id: str,
        agent_name: str,
    ) -> LLMAPIUsage:
        """Record LLM API usage and calculate costs."""

        pricing = PRICING.get(model, {"input": 0.0, "output": 0.0})

        cost_input = (tokens_input / 1_000_000) * pricing["input"]
        cost_output = (tokens_output / 1_000_000) * pricing["output"]
        cost_total = cost_input + cost_output

        usage = LLMAPIUsage(
            timestamp=datetime.now(timezone.utc).isoformat(),
            model=model,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            cost_input_usd=cost_input,
            cost_output_usd=cost_output,
            cost_total_usd=cost_total,
            latency_ms=latency_ms,
            task_type=task_type,
            brand_id=brand_id,
            agent_name=agent_name,
        )

        async with self._lock:
            self.usage_history.append(usage)
            await self._save_history()

        # Log expensive calls
        if cost_total > 0.10:  # Log calls costing more than $0.10
            logger.info(
                f"Expensive LLM call: ${cost_total:.4f} for {model} "
                f"({tokens_input} input + {tokens_output} output tokens)"
            )

        return usage

    def get_total_cost(self, hours: int = 24) -> Dict[str, float]:
        """Get total costs for the last N hours."""
        cutoff_time = datetime.now(timezone.utc).timestamp() - (hours * 3600)

        recent_usage = [
            u for u in self.usage_history
            if datetime.fromisoformat(u.timestamp).timestamp() > cutoff_time
        ]

        costs_by_model: Dict[str, float] = {}
        total_cost = 0.0

        for usage in recent_usage:
            costs_by_model[usage.model] = costs_by_model.get(usage.model, 0.0) + usage.cost_total_usd
            total_cost += usage.cost_total_usd

        return {
            "total_cost_usd": total_cost,
            "costs_by_model": costs_by_model,
            "request_count": len(recent_usage),
            "time_period_hours": hours,
        }

    def get_cost_by_brand(self, hours: int = 24) -> Dict[str, Dict[str, float]]:
        """Get costs broken down by brand."""
        cutoff_time = datetime.now(timezone.utc).timestamp() - (hours * 3600)

        recent_usage = [
            u for u in self.usage_history
            if datetime.fromisoformat(u.timestamp).timestamp() > cutoff_time
        ]

        brand_costs: Dict[str, Dict[str, float]] = {}

        for usage in recent_usage:
            if usage.brand_id not in brand_costs:
                brand_costs[usage.brand_id] = {
                    "total_cost_usd": 0.0,
                    "request_count": 0,
                    "tokens_total": 0,
                }

            brand_costs[usage.brand_id]["total_cost_usd"] += usage.cost_total_usd
            brand_costs[usage.brand_id]["request_count"] += 1
            brand_costs[usage.brand_id]["tokens_total"] += usage.tokens_input + usage.tokens_output

        return brand_costs

    async def _save_history(self):
        """Save usage history to file."""
        try:
            data = [asdict(u) for u in self.usage_history[-1000:]]  # Keep last 1000 records
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save cost tracking: {e}")

    def _load_history(self):
        """Load usage history from file."""
        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
                self.usage_history = [
                    LLMAPIUsage(**item) for item in data
                ]
        except FileNotFoundError:
            logger.info("No existing cost tracking file found, starting fresh")
        except Exception as e:
            logger.error(f"Failed to load cost tracking: {e}, starting fresh")


# Global cost tracker instance
cost_tracker = CostTracker()
```

**Integration with llm_client.py:**

```python
# File: python/src/content_engine/utils/llm_client.py (MODIFIED)

from src.content_engine.utils.cost_tracker import cost_tracker

class LLMClient:
    # ... existing code ...

    async def call_llm(
        self,
        prompt: str,
        task_type: str = "general",
        brand_id: str = "default",
        agent_name: str = "unknown",
        # ... other parameters
    ) -> LLMResponse:
        """Call LLM with cost tracking."""

        start_time = time.time()

        # ... existing LLM call logic ...

        latency_ms = int((time.time() - start_time) * 1000)

        # Track costs
        await cost_tracker.record_usage(
            model=response.model_used,
            tokens_input=response.tokens_prompt,
            tokens_output=response.tokens_completion,
            latency_ms=latency_ms,
            task_type=task_type,
            brand_id=brand_id,
            agent_name=agent_name,
        )

        return response
```

**Monitoring Dashboard:**

```python
# File: python/src/content_engine/utils/cost_monitor.py (NEW)

from src.content_engine.utils.cost_tracker import cost_tracker

class CostMonitor:
    """Monitor and alert on LLM costs."""

    BUDGET_ALERT_THRESHOLD_USD = 10.0  # Alert if hourly cost exceeds $10
    DAILY_BUDGET_USD = 50.0  # Alert if daily cost exceeds $50

    @staticmethod
    def check_budget_alerts() -> Dict[str, Any]:
        """Check if cost budgets are being exceeded."""
        hourly_cost = cost_tracker.get_total_cost(hours=1)
        daily_cost = cost_tracker.get_total_cost(hours=24)

        alerts = []

        if hourly_cost["total_cost_usd"] > CostMonitor.BUDGET_ALERT_THRESHOLD_USD:
            alerts.append({
                "severity": "WARNING",
                "message": f"Hourly cost ${hourly_cost['total_cost_usd']:.2f} exceeds threshold ${CostMonitor.BUDGET_ALERT_THRESHOLD_USD:.2f}",
                "cost_usd": hourly_cost["total_cost_usd"],
                "threshold_usd": CostMonitor.BUDGET_ALERT_THRESHOLD_USD,
            })

        if daily_cost["total_cost_usd"] > CostMonitor.DAILY_BUDGET_USD:
            alerts.append({
                "severity": "CRITICAL",
                "message": f"Daily cost ${daily_cost['total_cost_usd']:.2f} exceeds budget ${CostMonitor.DAILY_BUDGET_USD:.2f}",
                "cost_usd": daily_cost["total_cost_usd"],
                "budget_usd": CostMonitor.DAILY_BUDGET_USD,
            })

        return {
            "alerts": alerts,
            "hourly_cost": hourly_cost,
            "daily_cost": daily_cost,
        }
```

**Estimated Time:** 3-4 hours

---

## 🟠 PHASE 2: HIGH PRIORITY IMPROVEMENTS (Week 2)

### 2.1 Implement Graceful Degradation

**Problem:** System crashes when all LLM models fail. No fallback strategy.

**Impact:** Complete service outage, poor user experience.

**Implementation:**

```python
# File: python/src/content_engine/utils/degradation.py (NEW)

import logging
from typing import Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)

class DegradationLevel(Enum):
    """System degradation levels."""
    NORMAL = "normal"           # All services operational
    DEGRADED = "degraded"       # Some services degraded, reduced functionality
    MINIMAL = "minimal"         # Minimal functionality available
    UNAVAILABLE = "unavailable" # Service unavailable

@dataclass
class DegradationResponse:
    """Response when system is degraded."""
    level: DegradationLevel
    message: str
    data: Optional[Dict[str, Any]] = None
    can_retry: bool = True
    retry_after_seconds: int = 60

class GracefulDegradationManager:
    """Manage graceful degradation when services fail."""

    def __init__(self):
        self.failure_counts: Dict[str, int] = {}
        self.current_level = DegradationLevel.NORMAL
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}

    def record_failure(self, service: str, error: Exception):
        """Record a service failure."""
        self.failure_counts[service] = self.failure_counts.get(service, 0) + 1

        logger.warning(f"Service failure recorded: {service} (count: {self.failure_counts[service]})")

        # Check if we need to degrade
        if self.failure_counts[service] >= 5:  # 5 consecutive failures
            self._degrade_service(service)

    def record_success(self, service: str):
        """Record a service success."""
        self.failure_counts[service] = 0

        # Check if we can recover
        if self.current_level != DegradationLevel.NORMAL:
            self._attempt_recovery(service)

    def get_degraded_response(
        self,
        task_type: str,
        context: str = "unknown"
    ) -> DegradationResponse:
        """Get a response appropriate for current degradation level."""

        if self.current_level == DegradationLevel.NORMAL:
            return DegradationResponse(
                level=DegradationLevel.NORMAL,
                message="System operating normally",
                can_retry=False,
            )

        elif self.current_level == DegradationLevel.DEGRADED:
            return DegradationResponse(
                level=DegradationLevel.DEGRADED,
                message="Some AI services are temporarily unavailable. Using reduced functionality.",
                data={
                    "fallback_used": True,
                    "quality": "reduced",
                },
                can_retry=True,
                retry_after_seconds=30,
            )

        elif self.current_level == DegradationLevel.MINIMAL:
            return DegradationResponse(
                level=DegradationLevel.MINIMAL,
                message="AI services are currently unavailable. Please try again later.",
                data={
                    "fallback_used": True,
                    "quality": "minimal",
                },
                can_retry=True,
                retry_after_seconds=120,
            )

        else:  # UNAVAILABLE
            return DegradationResponse(
                level=DegradationLevel.UNAVAILABLE,
                message="Service temporarily unavailable. We're working to restore full functionality.",
                can_retry=True,
                retry_after_seconds=300,
            )

    def _degrade_service(self, service: str):
        """Degrade service due to failures."""
        if self.current_level == DegradationLevel.NORMAL:
            self.current_level = DegradationLevel.DEGRADED
            logger.warning(f"System degraded to DEGRADED level due to {service} failures")

        elif self.current_level == DegradationLevel.DEGRADED:
            self.current_level = DegradationLevel.MINIMAL
            logger.error(f"System degraded to MINIMAL level due to {service} failures")

        elif self.current_level == DegradationLevel.MINIMAL:
            self.current_level = DegradationLevel.UNAVAILABLE
            logger.critical(f"System degraded to UNAVAILABLE level due to {service} failures")

    def _attempt_recovery(self, service: str):
        """Attempt to recover from degraded state."""
        if self.current_level == DegradationLevel.MINIMAL:
            self.current_level = DegradationLevel.DEGRADED
            logger.info(f"System recovered to DEGRADED level")

        elif self.current_level == DegradationLevel.DEGRADED:
            self.current_level = DegradationLevel.NORMAL
            logger.info(f"System recovered to NORMAL level")


class CircuitBreaker:
    """Circuit breaker pattern for failing services."""

    def __init__(self, failure_threshold: int = 5, timeout_seconds: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.failure_count = 0
        self.last_failure_time = None
        self.is_open = False

    def record_failure(self):
        """Record a failure."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.is_open = True
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")

    def record_success(self):
        """Record a success."""
        self.failure_count = 0
        self.is_open = False

    def can_attempt(self) -> bool:
        """Check if we can attempt the operation."""
        if not self.is_open:
            return True

        # Check if timeout has passed
        if time.time() - self.last_failure_time > self.timeout_seconds:
            self.is_open = False
            self.failure_count = 0
            logger.info("Circuit breaker closed after timeout")
            return True

        return False


# Global degradation manager
degradation_manager = GracefulDegradationManager()
```

**Integration with llm_client.py:**

```python
# File: python/src/content_engine/utils/llm_client.py (MODIFIED)

from src.content_engine.utils.degradation import degradation_manager, DegradationLevel

class LLMClient:
    # ... existing code ...

    async def call_llm(
        self,
        prompt: str,
        task_type: str = "general",
        # ... other parameters
    ) -> LLMResponse:
        """Call LLM with graceful degradation."""

        try:
            # ... existing LLM call logic ...

            # Record success
            degradation_manager.record_success(model)

            return response

        except Exception as e:
            # Record failure
            degradation_manager.record_failure(model, e)

            # Get degraded response
            degraded = degradation_manager.get_degraded_response(task_type)

            if degraded.level == DegradationLevel.UNAVAILABLE:
                # Cannot proceed
                raise Exception(f"Service unavailable: {degraded.message}")

            # Try fallback strategies
            logger.warning(f"Primary LLM failed, attempting fallback: {e}")

            try:
                return await self._emergency_openrouter_fallback(prompt, task_type, model)
            except Exception as fallback_error:
                # All fallbacks failed
                logger.error(f"All LLM strategies failed: {fallback_error}")

                # Return degraded response
                return LLMResponse(
                    content=degraded.message,
                    model_used="fallback",
                    tokens_prompt=0,
                    tokens_completion=0,
                    engine="fallback",
                    latency_ms=0,
                    fallback_to=None,
                )
```

**Estimated Time:** 3-4 hours

---

### 2.2 Implement Fallback Rate Metrics

**Problem:** No visibility into how often we're falling back to alternative models.

**Impact:** Can't monitor service quality, can't optimize model selection.

**Implementation:**

```python
# File: python/src/content_engine/utils/fallback_metrics.py (NEW)

import time
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict
from datetime import datetime, timezone
import json
import logging

logger = logging.getLogger(__name__)

@dataclass
class FallbackEvent:
    """Record a fallback event."""
    timestamp: str
    primary_model: str
    fallback_model: str
    reason: str
    task_type: str
    latency_ms_primary: int
    latency_ms_fallback: int
    success: bool

class FallbackMetrics:
    """Track and analyze fallback patterns."""

    def __init__(self, storage_path: str = "fallback_metrics.json"):
        self.storage_path = storage_path
        self.events: List[FallbackEvent] = []
        self._by_model: Dict[str, Dict[str, int]] = defaultdict(lambda: {"count": 0, "success": 0})
        self._by_reason: Dict[str, int] = defaultdict(int)
        self._by_task: Dict[str, int] = defaultdict(int)

    def record_fallback(
        self,
        primary_model: str,
        fallback_model: str,
        reason: str,
        task_type: str,
        latency_ms_primary: int,
        latency_ms_fallback: int,
        success: bool,
    ):
        """Record a fallback event."""

        event = FallbackEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            primary_model=primary_model,
            fallback_model=fallback_model,
            reason=reason,
            task_type=task_type,
            latency_ms_primary=latency_ms_primary,
            latency_ms_fallback=latency_ms_fallback,
            success=success,
        )

        self.events.append(event)
        self._by_model[primary_model]["count"] += 1
        if success:
            self._by_model[primary_model]["success"] += 1
        self._by_reason[reason] += 1
        self._by_task[task_type] += 1

        logger.info(
            f"Fallback recorded: {primary_model} -> {fallback_model} "
            f"(reason: {reason}, success: {success})"
        )

        # Save periodically
        if len(self.events) % 10 == 0:
            self._save_events()

    def get_fallback_rate(self, hours: int = 24) -> Dict[str, float]:
        """Get fallback rates for the last N hours."""
        cutoff_time = datetime.now(timezone.utc).timestamp() - (hours * 3600)

        recent_events = [
            e for e in self.events
            if datetime.fromisoformat(e.timestamp).timestamp() > cutoff_time
        ]

        total_requests = sum(
            stats["count"] for stats in self._by_model.values()
        )

        fallback_by_model = {
            model: {
                "count": stats["count"],
                "success_rate": stats["success"] / stats["count"] if stats["count"] > 0 else 0.0,
                "fallback_rate": stats["count"] / total_requests if total_requests > 0 else 0.0,
            }
            for model, stats in self._by_model.items()
        }

        return {
            "total_fallbacks": len(recent_events),
            "total_requests": total_requests,
            "overall_fallback_rate": len(recent_events) / total_requests if total_requests > 0 else 0.0,
            "by_model": fallback_by_model,
            "by_reason": dict(self._by_reason),
            "by_task": dict(self._by_task),
        }

    def get_problematic_models(self, threshold: float = 0.10) -> List[str]:
        """Get models with fallback rates above threshold."""
        metrics = self.get_fallback_rate()

        problematic = []

        for model, stats in metrics["by_model"].items():
            if stats["fallback_rate"] > threshold:
                problematic.append(model)

        return sorted(problematic, key=lambda m: metrics["by_model"][m]["fallback_rate"], reverse=True)

    def _save_events(self):
        """Save events to file."""
        try:
            data = [asdict(e) for e in self.events[-500:]]  # Keep last 500 events
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save fallback metrics: {e}")


# Global fallback metrics instance
fallback_metrics = FallbackMetrics()
```

**Integration with llm_client.py:**

```python
# File: python/src/content_engine/utils/llm_client.py (MODIFIED)

from src.content_engine.utils.fallback_metrics import fallback_metrics

class LLMClient:
    # ... existing code ...

    async def call_llm(
        self,
        prompt: str,
        task_type: str = "general",
        # ... other parameters
    ) -> LLMResponse:
        """Call LLM with fallback metrics."""

        primary_model = self._get_primary_model(task_type)
        start_time = time.time()

        try:
            response = await self._make_llm_call(prompt, primary_model, task_type)
            return response

        except Exception as e:
            latency_primary = int((time.time() - start_time) * 1000)

            # Record fallback attempt
            fallback_start = time.time()

            try:
                fallback_response = await self._emergency_openrouter_fallback(prompt, task_type, primary_model)

                latency_fallback = int((time.time() - fallback_start) * 1000)

                # Record successful fallback
                fallback_metrics.record_fallback(
                    primary_model=primary_model,
                    fallback_model=fallback_response.model_used,
                    reason=str(e)[:100],  # Limit reason length
                    task_type=task_type,
                    latency_ms_primary=latency_primary,
                    latency_ms_fallback=latency_fallback,
                    success=True,
                )

                return fallback_response

            except Exception as fallback_error:
                # Record failed fallback
                fallback_metrics.record_fallback(
                    primary_model=primary_model,
                    fallback_model="unknown",
                    reason=f"{str(e)} | {str(fallback_error)}"[:100],
                    task_type=task_type,
                    latency_ms_primary=latency_primary,
                    latency_ms_fallback=0,
                    success=False,
                )

                raise
```

**Estimated Time:** 2-3 hours

---

## 🟡 PHASE 3: MEDIUM PRIORITY IMPROVEMENTS (Week 3-4)

### 3.1 Implement Parallel Retry Strategy

**Problem:** Sequential fallback with 120s timeout is too slow.

**Implementation:**

```python
# File: python/src/content_engine/utils/parallel_llm.py (NEW)

import asyncio
from typing import List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class ParallelLLMCaller:
    """Call multiple LLM models in parallel and return first successful response."""

    def __init__(self, timeout_per_model: float = 30.0, overall_timeout: float = 60.0):
        self.timeout_per_model = timeout_per_model
        self.overall_timeout = overall_timeout

    async def call_first_success(
        self,
        models: List[str],
        prompt: str,
        task_type: str = "general",
    ) -> Tuple[Optional[dict], float]:
        """
        Call multiple models in parallel, return first successful response.

        Returns:
            Tuple of (response_dict, latency_ms)
        """
        start_time = time.time()

        # Create tasks for all models
        tasks = []
        for model in models:
            task = asyncio.create_task(
                self._call_model_with_timeout(model, prompt, task_type)
            )
            tasks.append(task)

        # Wait for first successful response or overall timeout
        try:
            done, pending = await asyncio.wait(
                tasks,
                timeout=self.overall_timeout,
                return_when=asyncio.FIRST_COMPLETED,
            )

            # Cancel pending tasks
            for task in pending:
                task.cancel()

            # Get first successful result
            for task in done:
                try:
                    result = task.result()
                    if result:  # If result is not None, it was successful
                        latency = (time.time() - start_time) * 1000
                        return result, latency
                except Exception as e:
                    logger.warning(f"Task failed: {e}")
                    continue

        except asyncio.TimeoutError:
            logger.error(f"All LLM calls timed out after {self.overall_timeout}s")

        # All models failed
        return None, (time.time() - start_time) * 1000

    async def _call_model_with_timeout(
        self,
        model: str,
        prompt: str,
        task_type: str,
    ) -> Optional[dict]:
        """Call a single model with timeout."""
        try:
            result = await asyncio.wait_for(
                self._make_llm_call(model, prompt, task_type),
                timeout=self.timeout_per_model,
            )
            return result
        except asyncio.TimeoutError:
            logger.warning(f"Model {model} timed out after {self.timeout_per_model}s")
            return None
        except Exception as e:
            logger.warning(f"Model {model} failed: {e}")
            return None

    async def _make_llm_call(self, model: str, prompt: str, task_type: str) -> dict:
        """Actual LLM call implementation (placeholder)."""
        # This would contain the actual HTTP call to the LLM API
        # For now, return a mock response
        await asyncio.sleep(0.1)  # Simulate network delay
        return {
            "content": f"Response from {model}",
            "model": model,
            "tokens_prompt": 100,
            "tokens_completion": 50,
        }
```

**Estimated Time:** 3-4 hours

---

### 3.2 Fix DRY Violation in Model Routing

**Implementation:**

```python
# File: python/src/content_engine/config/llm_models.py (NEW)

from typing import List, Dict
from dataclasses import dataclass
from enum import Enum

class ModelCapability(Enum):
    """LLM model capabilities."""
    GENERAL = "general"
    RESEARCH = "research"
    SCORING = "scoring"
    FACT_CHECK = "fact_check"
    CREATIVE = "creative"
    EDITING = "editing"

@dataclass
class ModelConfig:
    """Configuration for an LLM model."""
    model_id: str
    capabilities: List[ModelCapability]
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout_seconds: int = 30
    priority: int = 0  # Lower = higher priority

# Centralized model routing configuration
MODEL_ROUTING = {
    ModelCapability.GENERAL: [
        ModelConfig(
            model_id="claude-sonnet-4-20250514",
            capabilities=[ModelCapability.GENERAL, ModelCapability.RESEARCH, ModelCapability.EDITING],
            priority=0,
        ),
        ModelConfig(
            model_id="gpt-4o",
            capabilities=[ModelCapability.GENERAL, ModelCapability.RESEARCH, ModelCapability.EDITING],
            priority=1,
        ),
    ],
    ModelCapability.SCORING: [
        ModelConfig(
            model_id="claude-sonnet-4-20250514",
            capabilities=[ModelCapability.SCORING],
            temperature=0.3,  # Lower temperature for scoring
            priority=0,
        ),
    ],
    ModelCapability.FACT_CHECK: [
        ModelConfig(
            model_id="claude-sonnet-4-20250514",
            capabilities=[ModelCapability.FACT_CHECK],
            temperature=0.2,  # Very low temperature for fact checking
            priority=0,
        ),
    ],
    ModelCapability.CREATIVE: [
        ModelConfig(
            model_id="claude-opus-4-20250514",
            capabilities=[ModelCapability.CREATIVE],
            temperature=0.9,  # Higher temperature for creativity
            priority=0,
        ),
        ModelConfig(
            model_id="gpt-4-turbo",
            capabilities=[ModelCapability.CREATIVE],
            temperature=0.9,
            priority=1,
        ),
    ],
}

# OpenRouter fallback models (free tier)
OPENROUTER_FALLBACK_MODELS = [
    "gemma-4-150b:free",
    "xiaomi/mimo:free",
    "meta-llama/llama-3-8b-instruct:free",
]

def get_models_for_capability(capability: ModelCapability) -> List[ModelConfig]:
    """Get models sorted by priority for a given capability."""
    models = MODEL_ROUTING.get(capability, [])
    return sorted(models, key=lambda m: m.priority)

def get_model_ids_for_capability(capability: ModelCapability) -> List[str]:
    """Get model IDs for a given capability."""
    return [m.model_id for m in get_models_for_capability(capability)]
```

**Integration with llm_client.py:**

```python
# File: python/src/content_engine/utils/llm_client.py (MODIFIED)

from src.content_engine.config.llm_models import (
    get_models_for_capability,
    ModelCapability,
    OPENROUTER_FALLBACK_MODELS,
)

class LLMClient:
    # ... existing code ...

    async def call_llm(
        self,
        prompt: str,
        task_type: str = "general",
        # ... other parameters
    ) -> LLMResponse:
        """Call LLM using centralized routing configuration."""

        # Map task_type to capability
        capability = self._task_type_to_capability(task_type)

        # Get models for this capability
        models = get_models_for_capability(capability)

        # Try each model in priority order
        for model_config in models:
            try:
                response = await self._make_llm_call(
                    prompt,
                    model_config.model_id,
                    temperature=model_config.temperature,
                    max_tokens=model_config.max_tokens,
                    timeout=model_config.timeout_seconds,
                )
                return response
            except Exception as e:
                logger.warning(f"Model {model_config.model_id} failed: {e}")
                continue

        # All primary models failed, try OpenRouter fallback
        return await self._emergency_openrouter_fallback(prompt, task_type)

    def _task_type_to_capability(self, task_type: str) -> ModelCapability:
        """Map task type to model capability."""
        mapping = {
            "general": ModelCapability.GENERAL,
            "research": ModelCapability.RESEARCH,
            "scoring": ModelCapability.SCORING,
            "fact_check": ModelCapability.FACT_CHECK,
            "creative": ModelCapability.CREATIVE,
            "editing": ModelCapability.EDITING,
        }
        return mapping.get(task_type, ModelCapability.GENERAL)
```

**Estimated Time:** 2-3 hours

---

## 🟢 PHASE 4: LOW PRIORITY OPTIMIZATIONS (Week 5+)

### 4.1 Optimize Database Upsert (Can Defer)

**Problem:** Current heartbeat upsert uses two round-trips.

**Implementation:**

```python
# File: python/src/content_engine/utils/heartbeat.py (MODIFIED)

async def _write_to_db(self, data: Dict[str, Any]) -> bool:
    """Write heartbeat data to database using native upsert."""

    try:
        # Use Supabase's native upsert (on_conflict)
        result = self.supabase.table('pipeline_health').upsert(
            data,
            on_conflict='brand_id,agent_name',  # Unique constraint
            ignore_duplicates=False,
        ).execute()

        logger.debug(f"Heartbeat written to database: {data.get('agent_name')}")
        return True

    except Exception as e:
        logger.error(f"Failed to write heartbeat to database: {e}")
        return False
```

**Estimated Time:** 1 hour

---

### 4.2 Fix Deprecated datetime.utcnow()

**Implementation:**

```python
# File: python/src/content_engine/utils/heartbeat.py (MODIFIED)

from datetime import datetime, timezone

# Replace all instances of:
# datetime.utcnow()

# With:
# datetime.now(timezone.utc)
```

**Estimated Time:** 30 minutes

---

### 4.3 Review Thread Safety (Defer Until Issues Observed)

**Action:** Monitor for actual thread safety issues in production before making changes.

**Estimated Time:** Monitoring + potential fixes (if needed)

---

## 📋 Implementation Timeline

### Week 1: Critical Production Fixes
- **Monday:** Fix JSON parsing vulnerability (4-6 hours)
- **Tuesday:** Implement rate limiting (3-4 hours)
- **Wednesday:** Implement cost tracking (3-4 hours)
- **Thursday-Friday:** Testing and integration

### Week 2: High Priority Improvements
- **Monday-Tuesday:** Implement graceful degradation (3-4 hours)
- **Wednesday-Thursday:** Implement fallback metrics (2-3 hours)
- **Friday:** Testing and integration

### Week 3-4: Medium Priority Improvements
- **Week 3:** Implement parallel retry strategy (3-4 hours)
- **Week 4:** Fix DRY violation in model routing (2-3 hours)

### Week 5+: Low Priority Optimizations
- As needed: Database optimization, datetime fixes, thread safety review

---

## 🧪 Testing Strategy

### Unit Tests
```bash
# Test JSON parser
pytest tests/test_json_parser.py -v

# Test rate limiter
pytest tests/test_rate_limiter.py -v

# Test cost tracker
pytest tests/test_cost_tracker.py -v

# Test degradation manager
pytest tests/test_degradation.py -v
```

### Integration Tests
```bash
# Test full LLM call with fallbacks
pytest tests/test_llm_integration.py -v

# Test rate limiting under load
pytest tests/test_rate_limiting_load.py -v

# Test graceful degradation
pytest tests/test_graceful_degradation.py -v
```

### Load Tests
```bash
# Test system under high load
locust -f tests/load_test_llm.py --host=http://localhost:8000
```

---

## 📊 Success Metrics

### Phase 1 Success Criteria
- ✅ JSON parsing成功率 > 99.9%
- ✅ No rate limit violations in production
- ✅ Cost tracking accuracy > 99%
- ✅ Zero service outages due to LLM failures

### Phase 2 Success Criteria
- ✅ Graceful degradation activates correctly
- ✅ Fallback rate visibility > 95%
- ✅ System recovers from degraded state automatically

### Phase 3 Success Criteria
- ✅ Average LLM response time < 30s (down from 60s+)
- ✅ Model routing maintenance overhead < 1 hour/week

### Overall Success
- ✅ System uptime > 99.5%
- ✅ Cost predictability (+/- 10%)
- ✅ User satisfaction > 4.5/5

---

## 🚨 Rollback Plan

Each phase includes a rollback plan:

### Phase 1 Rollback
- Revert JSON parser changes
- Disable rate limiting (set to permissive mode)
- Disable cost tracking (non-blocking)

### Phase 2 Rollback
- Disable graceful degradation (fallback to original error handling)
- Disable fallback metrics (non-blocking)

### Phase 3 Rollback
- Revert parallel retry to sequential
- Revert DRY fix to original routing

---

## 📝 Documentation Updates

After each phase, update:
- API documentation
- Architecture diagrams
- Runbook for operators
- Cost monitoring dashboard
- Rate limit configuration guide

---

## 🎯 Conclusion

This implementation plan prioritizes **REAL production risks** over code cosmetics. By focusing on reliability, observability, and cost management first, we ensure the system is production-ready before optimizing for code cleanliness.

**Key Philosophy:** Make it work reliably, make it observable, make it efficient (in that order).

---

**Plan Status:** 📋 READY FOR IMPLEMENTATION
**Estimated Total Time:** 2-3 weeks for all phases
**Risk Level:** 🟢 LOW (phased approach with rollback options)
