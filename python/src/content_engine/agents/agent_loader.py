"""Agent Loader — TTL-cached identity and skills loader from DB.

Phase 2 preparation: loads agent identity and skills from Supabase,
with in-memory TTL cache to avoid hitting the DB on every LLM call.

Cache strategy: 5-minute TTL per (brand_id, agent_key) tuple.
Cache is invalidated on identity update via `invalidate_agent_cache()`.
No external dependency (Redis etc.) — uses a simple dict + monotonic clock.

Usage (Phase 2 — wired in after DB migration):
    from ..agents.agent_loader import get_agent_identity

    identity = await get_agent_identity(brand_id, "writer")
    prompt = identity + task_specific_section
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass

logger = logging.getLogger("content_engine.agent_loader")

# ── Default identity prompts (Phase 1 fallbacks) ────────────────────────────

# These are imported lazily to avoid circular imports when this module
# is loaded before the agent modules.  The dict is populated on first access.
_DEFAULTS_LOADED = False
_DEFAULT_IDENTITIES: dict[str, str] = {}


def _load_defaults() -> dict[str, str]:
    """Lazy-load hardcoded prompts as fallback defaults."""
    global _DEFAULTS_LOADED, _DEFAULT_IDENTITIES
    if _DEFAULTS_LOADED:
        return _DEFAULT_IDENTITIES

    from .adapter import ADAPTER_PROMPT
    from .editor import EDITOR_PROMPT
    from .god_system import (
        ADVOCATE_PROMPT,
        CREATIVE_PROMPT,
        FACTCHECK_PROMPT,
        SYNTHESIS_PROMPT,
    )
    from .writer import WRITER_PROMPT

    _DEFAULT_IDENTITIES = {
        "writer": WRITER_PROMPT,
        "editor": EDITOR_PROMPT,
        "adapter": ADAPTER_PROMPT,
        "god_advocate": ADVOCATE_PROMPT,
        "god_factcheck": FACTCHECK_PROMPT,
        "god_creative": CREATIVE_PROMPT,
        "god_synthesis": SYNTHESIS_PROMPT,
    }
    _DEFAULTS_LOADED = True
    return _DEFAULT_IDENTITIES


# ── TTL Cache ────────────────────────────────────────────────────────────────

CACHE_TTL_SECONDS = 300  # 5 minutes


@dataclass
class _CacheEntry:
    identity: str
    skills_text: str
    task_type_override: str | None
    expires_at: float


class _AgentCache:
    """Thread-safe TTL cache for agent identities + skills.

    Key: (brand_id, agent_key)
    Value: _CacheEntry with expiry timestamp

    Why not functools.lru_cache?
      - lru_cache doesn't support TTL natively
      - We need explicit invalidation on identity update
      - We want per-key expiry, not global eviction
    """

    def __init__(self, ttl: int = CACHE_TTL_SECONDS):
        self._store: dict[tuple[str, str], _CacheEntry] = {}
        self._lock = threading.Lock()
        self._ttl = ttl

    def get(self, brand_id: str, agent_key: str) -> _CacheEntry | None:
        key = (brand_id, agent_key)
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if time.monotonic() > entry.expires_at:
                del self._store[key]
                return None
            return entry

    def put(
        self,
        brand_id: str,
        agent_key: str,
        identity: str,
        skills_text: str = "",
        task_type_override: str | None = None,
    ) -> None:
        key = (brand_id, agent_key)
        entry = _CacheEntry(
            identity=identity,
            skills_text=skills_text,
            task_type_override=task_type_override,
            expires_at=time.monotonic() + self._ttl,
        )
        with self._lock:
            self._store[key] = entry

    def invalidate(self, brand_id: str, agent_key: str | None = None) -> int:
        """Invalidate cache entries.

        If agent_key is None, invalidate ALL entries for the brand.
        Returns the number of entries invalidated.
        """
        removed = 0
        with self._lock:
            keys_to_remove = [
                k for k in self._store
                if k[0] == brand_id and (agent_key is None or k[1] == agent_key)
            ]
            for k in keys_to_remove:
                del self._store[k]
                removed += 1
        if removed:
            logger.info(
                "Invalidated %d cache entries for brand=%s agent=%s",
                removed, brand_id, agent_key or "*",
            )
        return removed

    def clear(self) -> None:
        """Clear the entire cache (useful for tests)."""
        with self._lock:
            self._store.clear()

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._store)


# Module-level singleton
_cache = _AgentCache()


# ── Public API ───────────────────────────────────────────────────────────────

async def get_agent_identity(
    brand_id: str,
    agent_key: str,
) -> str:
    """Load the agent identity prompt for a brand, with caching.

    Resolution order:
    1. In-memory TTL cache (5min)
    2. DB: agent_configs table
    3. Hardcoded defaults (Phase 1 prompts)

    Returns the identity string (may contain {placeholders} for .format()).
    """
    # 1. Check cache
    cached = _cache.get(brand_id, agent_key)
    if cached is not None:
        logger.debug("Cache HIT for brand=%s agent=%s", brand_id, agent_key)
        return cached.identity + (f"\n\n{cached.skills_text}" if cached.skills_text else "")

    # 2. Try DB (Phase 2 — gracefully degrades if table doesn't exist yet)
    identity_text = ""
    skills_text = ""
    task_type_override = None

    try:
        from ..db import get_db
        db = get_db()

        # Load identity
        config = db.table("agent_configs") \
            .select("identity, task_type_override") \
            .eq("brand_id", brand_id) \
            .eq("agent_key", agent_key) \
            .eq("is_active", True) \
            .maybe_single() \
            .execute()

        if config.data and config.data.get("identity"):
            identity_text = config.data["identity"]
            task_type_override = config.data.get("task_type_override")

        # Load skills
        skills = db.table("agent_skills") \
            .select("skill_name, instructions, priority") \
            .eq("brand_id", brand_id) \
            .eq("target_agent", agent_key) \
            .eq("is_active", True) \
            .order("priority") \
            .execute()

        if skills.data:
            skill_blocks = []
            for s in skills.data:
                skill_blocks.append(f"### Skill: {s['skill_name']}\n{s['instructions']}")
            skills_text = "## Skills Attive\n" + "\n\n".join(skill_blocks)

    except Exception as e:
        # Phase 2 tables may not exist yet — this is expected during Phase 1
        logger.debug("DB agent_configs not available (expected in Phase 1): %s", e)

    # 3. Fallback to hardcoded defaults
    if not identity_text:
        defaults = _load_defaults()
        identity_text = defaults.get(agent_key, "")

    # Cache the result
    if identity_text:
        _cache.put(brand_id, agent_key, identity_text, skills_text, task_type_override)

    return identity_text + (f"\n\n{skills_text}" if skills_text else "")


async def get_task_type_override(brand_id: str, agent_key: str) -> str | None:
    """Get task_type override for this brand+agent, if any.

    Returns None if no override is set (use the agent's default task_type).
    """
    cached = _cache.get(brand_id, agent_key)
    if cached is not None:
        return cached.task_type_override
    # If not cached, trigger a full load which will populate the cache
    await get_agent_identity(brand_id, agent_key)
    cached = _cache.get(brand_id, agent_key)
    return cached.task_type_override if cached else None


def invalidate_agent_cache(brand_id: str, agent_key: str | None = None) -> int:
    """Invalidate cached agent config (call after DB update).

    Args:
        brand_id: The brand to invalidate
        agent_key: Specific agent to invalidate, or None for all agents

    Returns:
        Number of cache entries invalidated
    """
    return _cache.invalidate(brand_id, agent_key)


def clear_agent_cache() -> None:
    """Clear the entire agent cache (useful for tests)."""
    _cache.clear()
