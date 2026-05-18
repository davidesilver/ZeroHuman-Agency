"""Provider registrar — thread-safe registry with 7-level routing cascade.

Cascade order for get_for_brand(brand_id):
  1. caller-specified preferred provider (if available for brand)
  2. brand_llm_config.preferred_provider (if set and key available)
  3. BYOK direct — catalog P0 providers in priority order
  4. BYOK direct — catalog P1/P2 providers
  5. OpenClaw A/B routing (if configured and random roll hits)
  6. system env — Anthropic (ANTHROPIC_API_KEY)
  7. system env — OpenRouter (OPENROUTER_API_KEY)  ← last resort
"""

from __future__ import annotations

import logging
import threading

from .provider import LLMProvider

_lock = threading.Lock()
_registry: dict[str, LLMProvider] = {}
_initialized = False

logger = logging.getLogger("content_engine.llm.registrar")


def _ensure_defaults() -> None:
    global _initialized
    if _initialized:
        return
    with _lock:
        if not _initialized:
            from .openrouter import OpenRouterProvider
            from .openclaw import OpenClawProvider
            _registry["openrouter"] = OpenRouterProvider()
            _registry["openclaw"] = OpenClawProvider()
            _initialized = True


def register_provider(provider: LLMProvider) -> None:
    with _lock:
        _registry[provider.name] = provider


def get_provider(name: str) -> LLMProvider | None:
    """Return a provider by name, or None if not registered."""
    _ensure_defaults()
    return _registry.get(name)


def list_providers() -> list[dict]:
    _ensure_defaults()
    return [{"name": p.name, "type": type(p).__name__} for p in _registry.values()]


# ── Per-brand preference lookup ────────────────────────────────────────────────

_pref_cache: dict[str, str | None] = {}
_pref_lock = threading.Lock()


def _get_brand_preferred_provider(brand_id: str) -> str | None:
    with _pref_lock:
        if brand_id in _pref_cache:
            return _pref_cache[brand_id]
    try:
        from ..db import get_db
        result = (
            get_db()
            .from_("brand_llm_config")
            .select("preferred_provider")
            .eq("brand_id", brand_id)
            .maybe_single()
            .execute()
        )
        pref = result.data["preferred_provider"] if result.data else None
    except Exception:
        pref = None
    with _pref_lock:
        _pref_cache[brand_id] = pref
    return pref


def invalidate_brand_preference_cache(brand_id: str) -> None:
    with _pref_lock:
        _pref_cache.pop(brand_id, None)


# ── Build a provider instance from a catalog entry + brand secrets ─────────────

def _build_byok_provider(provider_id: str, brand_id: str) -> Optional[LLMProvider]:
    from .provider_catalog import PROVIDER_CATALOG
    defn = PROVIDER_CATALOG.get(provider_id)
    if not defn:
        return None

    if defn.api_type == "anthropic_native":
        from .anthropic_direct import AnthropicDirectProvider
        from ..brand_secrets import get_brand_secret
        api_key = get_brand_secret(brand_id, provider_id, "api_key")
        if not api_key:
            return None
        default_model = get_brand_secret(brand_id, provider_id, "default_model")
        from .anthropic_direct import _DEFAULT_MODEL
        return AnthropicDirectProvider(api_key, default_model or _DEFAULT_MODEL)

    if defn.api_type == "openai_compatible":
        from .generic_openai import GenericOpenAIProvider
        return GenericOpenAIProvider.from_brand_config(provider_id, brand_id)

    return None


# ── Routing cascade ────────────────────────────────────────────────────────────

class ProviderRegistrar:
    """High-level registrar with per-brand routing."""

    def get_for_brand(self, brand_id: str, preferred: str | None = None) -> LLMProvider:
        """Return the best available provider for a brand using the 7-level cascade."""
        _ensure_defaults()
        from .provider_catalog import PROVIDER_CATALOG
        from ..config import settings

        # ── Level 1: caller-specified preferred ─────────────────────────────
        if preferred:
            p = _build_byok_provider(preferred, brand_id)
            if p:
                return p
            # Also check static registry (e.g. openrouter passed directly)
            p = _registry.get(preferred)
            if p and p.is_available(brand_id):
                return p

        # ── Level 2: brand DB preference ────────────────────────────────────
        brand_pref = _get_brand_preferred_provider(brand_id)
        if brand_pref:
            p = _build_byok_provider(brand_pref, brand_id)
            if p:
                return p

        # ── Levels 3–4: BYOK scan (P0 then P1/P2) ───────────────────────────
        catalog_ordered = sorted(
            PROVIDER_CATALOG.values(),
            key=lambda d: (d.priority, d.display_name),
        )
        for defn in catalog_ordered:
            if defn.auth_type not in ("api_key", "optional_key"):
                continue
            if defn.category not in ("direct", "meta_router"):
                continue
            p = _build_byok_provider(defn.id, brand_id)
            if p:
                return p

        # ── Level 5: OpenClaw A/B ────────────────────────────────────────────
        openclaw = _registry.get("openclaw")
        if openclaw and openclaw.is_available(brand_id):
            try:
                if openclaw.should_route(brand_id):  # type: ignore[attr-defined]
                    return openclaw
            except AttributeError:
                pass

        # ── Level 6: system Anthropic env var ───────────────────────────────
        if settings.anthropic_api_key:
            from .anthropic_direct import AnthropicDirectProvider, _DEFAULT_MODEL
            return AnthropicDirectProvider(settings.anthropic_api_key, _DEFAULT_MODEL)

        # ── Level 7: system OpenRouter env var (always-on fallback) ─────────
        return _registry["openrouter"]


_registrar = ProviderRegistrar()


def get_registrar() -> ProviderRegistrar:
    _ensure_defaults()
    return _registrar
