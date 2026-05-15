"""Provider registrar — thread-safe registry of LLMProvider instances.

Usage:
    from content_engine.services.llm.registrar import get_registrar, list_providers

    # Get the default provider for a brand
    provider = get_registrar().get_for_brand(brand_id)
    result = provider.complete(request)
"""

from __future__ import annotations

import threading
from typing import Optional

from .openrouter import OpenRouterProvider
from .provider import LLMProvider

_lock = threading.Lock()
_registry: dict[str, LLMProvider] = {}
_initialized = False


def _ensure_defaults() -> None:
    global _initialized
    if _initialized:
        return
    with _lock:
        if not _initialized:
            _registry["openrouter"] = OpenRouterProvider()
            _initialized = True


def register_provider(provider: LLMProvider) -> None:
    """Register or replace a provider by name."""
    with _lock:
        _registry[provider.name] = provider


def get_provider(name: str) -> Optional[LLMProvider]:
    """Return a provider by name, or None if not registered."""
    _ensure_defaults()
    return _registry.get(name)


def list_providers() -> list[dict]:
    """Return a list of registered providers with availability info."""
    _ensure_defaults()
    return [
        {
            "name": p.name,
            "type": type(p).__name__,
        }
        for p in _registry.values()
    ]


class ProviderRegistrar:
    """High-level registrar with per-brand routing."""

    def get_for_brand(self, brand_id: str, preferred: Optional[str] = None) -> LLMProvider:
        """Return the best available provider for a brand.

        Selection order:
          1. preferred (if specified and available)
          2. 'openrouter' (always available as fallback)
        """
        _ensure_defaults()
        if preferred:
            p = _registry.get(preferred)
            if p and p.is_available(brand_id):
                return p
        return _registry["openrouter"]


_registrar = ProviderRegistrar()


def get_registrar() -> ProviderRegistrar:
    """Return the global provider registrar."""
    _ensure_defaults()
    return _registrar
