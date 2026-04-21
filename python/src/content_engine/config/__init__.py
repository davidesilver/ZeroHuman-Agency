"""
Content Engine Configuration Package

Centralized configuration for LLM models, routing, and system settings.

This package provides a single source of truth for model configuration,
routing rules, and system-wide settings.
"""

from .llm_models import (
    ModelCapability,
    ModelConfig,
    MODEL_ROUTING,
    OPENROUTER_FALLBACK_MODELS,
    get_models_for_capability,
    get_model_ids_for_capability,
    get_model_config,
    MODEL_CAPABILITIES,
)

# Re-export settings so `from .config import settings` works even though
# the config/ package shadows the old config.py module.
from .settings import Settings, settings

__all__ = [
    'ModelCapability',
    'ModelConfig',
    'MODEL_ROUTING',
    'OPENROUTER_FALLBACK_MODELS',
    'get_models_for_capability',
    'get_model_ids_for_capability',
    'get_model_config',
    'MODEL_CAPABILITIES',
    'Settings',
    'settings',
]
