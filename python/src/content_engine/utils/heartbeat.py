"""Pragmatic Heartbeat System - resilience-first approach.

This module provides:
1. Logging-first heartbeat (DB writes optional, can be disabled)
2. Uses existing context/action parameters (no agent_key pollution)
3. Bounded cache to prevent memory leaks
4. Rate limiting per brand to prevent abuse
5. Graceful degradation (never fails the main pipeline)

Design Principles:
- Do no harm: heartbeat failures never impact main pipeline
- Measure first: start with logging, add DB writes only if needed
- Simplify: reuse existing context/action instead of new parameters
- Resilience: bounded resources, rate limiting, graceful degradation
"""

from __future__ import annotations

import logging
import time
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from threading import Lock

logger = logging.getLogger("content_engine.heartbeat")


class HeartbeatCache:
    """Bounded LRU cache for heartbeat data to prevent memory leaks.

    Uses OrderedDict for O(1) access and automatic eviction of oldest entries.
    """

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 60):
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._lock = Lock()

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get heartbeat from cache if exists and not expired."""
        with self._lock:
            entry = self._cache.get(key)
            if not entry:
                return None

            # Check TTL
            if time.time() - entry.get("timestamp", 0) > self._ttl:
                del self._cache[key]
                return None

            # Move to end (mark as recently used)
            self._cache.move_to_end(key)
            return entry

    def set(self, key: str, value: Dict[str, Any]) -> None:
        """Set heartbeat in cache with automatic eviction if full."""
        with self._lock:
            # Remove if exists
            if key in self._cache:
                del self._cache[key]

            # Add to end
            self._cache[key] = value

            # Evict oldest if over capacity
            while len(self._cache) > self._max_size:
                self._cache.popitem(last=False)


class RateLimiter:
    """Simple rate limiter per brand to prevent abuse.

    Allows max_requests per time_window_seconds.
    """

    def __init__(self, max_requests: int = 100, time_window_seconds: int = 60):
        self._max_requests = max_requests
        self._time_window = time_window_seconds
        self._requests: Dict[str, list] = {}
        self._lock = Lock()

    def is_allowed(self, brand_id: str) -> bool:
        """Check if request is allowed for this brand."""
        with self._lock:
            now = time.time()
            brand_requests = self._requests.get(brand_id, [])

            # Remove expired requests
            brand_requests = [t for t in brand_requests if now - t < self._time_window]
            self._requests[brand_id] = brand_requests

            # Check limit
            if len(brand_requests) >= self._max_requests:
                logger.warning(
                    "Rate limit exceeded for brand %s: %d requests in %d seconds",
                    brand_id, len(brand_requests), self._time_window
                )
                return False

            # Record request
            brand_requests.append(now)
            return True


# Global instances
_heartbeat_cache = HeartbeatCache(max_size=1000, ttl_seconds=60)
_rate_limiter = RateLimiter(max_requests=100, time_window_seconds=60)
_rate_limiting_enabled = False  # DISABLED by default per user request


async def record_agent_heartbeat(
    brand_id: str,
    llm_meta: Optional[Dict[str, Any]] = None,
    context: str = "general",
    action: str = "call_llm",
    status: str = "healthy",
) -> None:
    """Record agent heartbeat with resilience-first approach.

    This function:
    1. Always succeeds (never raises exceptions)
    2. Uses rate limiting to prevent abuse
    3. Logs to structured logger (primary)
    4. Writes to cache (for dashboard real-time)
    5. Optionally writes to DB (can be disabled via config)

    Args:
        brand_id: Brand ID for rate limiting and tracking
        llm_meta: Dict with LLM metadata {model, engine, latency_ms, tokens}
        context: Context label (e.g., "god_advocate", "writer_initial")
        action: Action label (e.g., "advocate", "generate_content")
        status: "healthy", "degraded", "down"

    Note:
        This function is fire-and-forget. It should always be called with
        asyncio.create_task() to avoid blocking the main pipeline.
    """
    try:
        # Rate limiting check (only if enabled)
        if _rate_limiting_enabled and not _rate_limiter.is_allowed(brand_id):
            logger.debug("Heartbeat rate limited for brand %s", brand_id)
            return

        # Build heartbeat data
        heartbeat_data = {
            "brand_id": brand_id,
            "context": context,
            "action": action,
            "status": status,
            "timestamp": time.time(),
            "llm_meta": llm_meta or {},
        }

        # Extract agent identifier from context/action (no new agent_key needed)
        agent_identifier = _extract_agent_identifier(context, action)

        # 1. Log to structured logger (PRIMARY, always works)
        logger.info(
            "Heartbeat: brand=%s agent=%s context=%s action=%s status=%s model=%s engine=%s latency_ms=%s",
            brand_id,
            agent_identifier,
            context,
            action,
            status,
            llm_meta.get("model_used", "unknown") if llm_meta else "unknown",
            llm_meta.get("engine", "unknown") if llm_meta else "unknown",
            llm_meta.get("latency_ms") if llm_meta else None,
        )

        # 2. Store in bounded cache (for dashboard real-time)
        cache_key = f"{brand_id}:{agent_identifier}"
        _heartbeat_cache.set(cache_key, heartbeat_data)

        # 3. Optional DB write (can be disabled, try-catch for resilience)
        if _should_write_to_db():
            await _write_to_db(heartbeat_data, agent_identifier)

    except Exception as e:
        # NEVER fail the main pipeline
        logger.error("Heartbeat recording failed (non-critical): %s", e)


def _extract_agent_identifier(context: str, action: str) -> str:
    """Extract agent identifier from existing context/action parameters.

    This avoids adding a new agent_key parameter to call_llm.

    Examples:
        context="god_advocate", action="advocate" -> "god_advocate"
        context="writer_initial", action="generate_content" -> "writer"
        context="humanizer_pass1", action="humanize" -> "humanizer"

    Args:
        context: Context label from call_llm
        action: Action label from call_llm

    Returns:
        Agent identifier string
    """
    # Try to extract from context first (more specific)
    if "_" in context:
        # Take the first part before underscore (e.g., "god_advocate" -> "god_advocate")
        # But for god_system, keep the full context to distinguish sub-agents
        if context.startswith("god_"):
            return context  # "god_advocate", "god_factcheck", etc.
        else:
            # For others, take first part (e.g., "writer_initial" -> "writer")
            return context.split("_")[0]

    # Fallback to action
    return action


def _should_write_to_db() -> bool:
    """Check if DB writes are enabled for heartbeat.

    This allows disabling DB writes if they cause performance issues.
    Can be controlled via environment variable or config.
    """
    try:
        from ..config import settings
        # Default to True, can be disabled via HEARTBEAT_DB_WRITE=false
        return getattr(settings, 'heartbeat_db_write', True)
    except Exception:
        # If config fails, default to True (safer)
        return True


async def _write_to_db(heartbeat_data: Dict[str, Any], agent_identifier: str) -> None:
    """Write heartbeat to database with error handling.

    This is optional and should never fail the main pipeline.

    Args:
        heartbeat_data: Heartbeat data dictionary
        agent_identifier: Extracted agent identifier
    """
    try:
        from ..db import get_db
        from ..config import settings

        db = get_db()

        # Prepare data for pipeline_health table
        now = datetime.utcnow().isoformat()
        llm_meta = heartbeat_data.get("llm_meta", {})

        upsert_data = {
            "brand_id": heartbeat_data["brand_id"],
            "agent_name": agent_identifier,
            "status": heartbeat_data["status"],
            "last_seen": now,
            "current_model": llm_meta.get("model_used", "unknown"),
            "fallback_model": llm_meta.get("fallback_to"),
            "engine": llm_meta.get("engine", "unknown"),
            "last_latency_ms": llm_meta.get("latency_ms"),
        }

        # Upsert to pipeline_health
        existing = db.table("pipeline_health").select("*").eq(
            "brand_id", heartbeat_data["brand_id"]
        ).eq(
            "agent_name", agent_identifier
        ).maybe_single().execute()

        if existing.data:
            db.table("pipeline_health").update(upsert_data).eq(
                "id", existing.data["id"]
            ).execute()
        else:
            upsert_data["uptime_pct"] = 100.0
            upsert_data["errors_today"] = 0
            upsert_data["queue_size"] = 0
            db.table("pipeline_health").insert(upsert_data).execute()

    except Exception as e:
        # Log but don't fail
        logger.debug("DB write failed for heartbeat (non-critical): %s", e)


def get_cached_heartbeat(brand_id: str, agent_identifier: str) -> Optional[Dict[str, Any]]:
    """Get cached heartbeat data for dashboard real-time updates.

    Args:
        brand_id: Brand ID
        agent_identifier: Agent identifier (e.g., "god_advocate", "writer")

    Returns:
        Cached heartbeat data or None if not found/expired
    """
    cache_key = f"{brand_id}:{agent_identifier}"
    return _heartbeat_cache.get(cache_key)


def get_all_cached_heartbeats(brand_id: str) -> Dict[str, Dict[str, Any]]:
    """Get all cached heartbeats for a brand.

    Args:
        brand_id: Brand ID

    Returns:
        Dict mapping agent_identifier -> heartbeat_data
    """
    result = {}
    with _heartbeat_cache._lock:
        for key, value in _heartbeat_cache._cache.items():
            if key.startswith(f"{brand_id}:"):
                agent_id = key.split(":", 1)[1]
                result[agent_id] = value
    return result


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics for monitoring.

    Returns:
        Dict with cache metrics
    """
    with _heartbeat_cache._lock:
        return {
            "cache_size": len(_heartbeat_cache._cache),
            "max_size": _heartbeat_cache._max_size,
            "ttl_seconds": _heartbeat_cache._ttl,
            "rate_limit_max": _rate_limiter._max_requests,
            "rate_limit_window": _rate_limiter._time_window,
            "rate_limiting_enabled": _rate_limiting_enabled,
        }


def set_rate_limiting(enabled: bool) -> None:
    """Enable or disable rate limiting for heartbeat recording.

    Args:
        enabled: True to enable rate limiting, False to disable
    """
    global _rate_limiting_enabled
    _rate_limiting_enabled = enabled
    logger.info("Rate limiting %s", "enabled" if enabled else "disabled")
