"""
Centralized LLM Model Configuration

Provides a single source of truth for LLM model configuration,
routing rules, and capabilities. This eliminates DRY violations and
ensures consistent model selection across the system.

Critical for maintainability: all model routing logic in one place.

Author: AI Engineering Team
Created: 2026-04-17
"""

import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ModelCapability(Enum):
    """LLM model capabilities.

    Each capability represents a type of task that models can perform.
    Models are associated with the capabilities they excel at.
    """

    GENERAL = "general"           # General-purpose tasks
    RESEARCH = "research"           # Research and analysis
    SCORING = "scoring"           # Content scoring and evaluation
    FACT_CHECK = "fact_check"     # Fact verification
    CREATIVE = "creative"         # Creative writing and ideation
    EDITING = "editing"           # Content editing and refinement
    REASONING = "reasoning"       # Complex reasoning and logic


@dataclass
class ModelConfig:
    """
    Configuration for an LLM model.

    Attributes:
        model_id: Unique model identifier (e.g., "claude-sonnet-4-20250514")
        capabilities: List of capabilities this model supports
        max_tokens: Maximum tokens for model output
        temperature: Default temperature for this model
        timeout_seconds: Default timeout for API calls
        priority: Lower priority = preferred for this capability
        provider: API provider (anthropic, openai, openrouter)
        cost_tier: Cost tier (free, low, medium, high)
    """

    model_id: str
    capabilities: list[ModelCapability]
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout_seconds: int = 30
    priority: int = 0
    provider: str = "unknown"
    cost_tier: str = "medium"


# Model configurations for all supported models
# This is the single source of truth for model selection

MODEL_CONFIGS: dict[str, ModelConfig] = {
    # Anthropic Claude models
    "claude-sonnet-4-20250514": ModelConfig(
        model_id="claude-sonnet-4-20250514",
        capabilities=[
            ModelCapability.GENERAL,
            ModelCapability.RESEARCH,
            ModelCapability.SCORING,
            ModelCapability.FACT_CHECK,
            ModelCapability.EDITING,
            ModelCapability.REASONING,
        ],
        max_tokens=8192,
        temperature=0.7,
        timeout_seconds=30,
        priority=0,  # Highest priority for most capabilities
        provider="anthropic",
        cost_tier="medium",
    ),
    "claude-opus-4-20250514": ModelConfig(
        model_id="claude-opus-4-20250514",
        capabilities=[
            ModelCapability.GENERAL,
            ModelCapability.RESEARCH,
            ModelCapability.CREATIVE,
            ModelCapability.REASONING,
        ],
        max_tokens=4096,
        temperature=0.9,  # Higher temperature for creative tasks
        timeout_seconds=45,
        priority=1,
        provider="anthropic",
        cost_tier="high",
    ),
    "claude-haiku-4-20250514": ModelConfig(
        model_id="claude-haiku-4-20250514",
        capabilities=[
            ModelCapability.GENERAL,
            ModelCapability.EDITING,
        ],
        max_tokens=4096,
        temperature=0.7,
        timeout_seconds=20,
        priority=2,
        provider="anthropic",
        cost_tier="low",
    ),

    # OpenAI GPT models
    "gpt-4o": ModelConfig(
        model_id="gpt-4o",
        capabilities=[
            ModelCapability.GENERAL,
            ModelCapability.RESEARCH,
            ModelCapability.EDITING,
            ModelCapability.REASONING,
        ],
        max_tokens=4096,
        temperature=0.7,
        timeout_seconds=30,
        priority=1,
        provider="openai",
        cost_tier="medium",
    ),
    "gpt-4-turbo": ModelConfig(
        model_id="gpt-4-turbo",
        capabilities=[
            ModelCapability.GENERAL,
            ModelCapability.RESEARCH,
            ModelCapability.CREATIVE,
        ],
        max_tokens=4096,
        temperature=0.8,
        timeout_seconds=45,
        priority=2,
        provider="openai",
        cost_tier="high",
    ),
    "gpt-4o-mini": ModelConfig(
        model_id="gpt-4o-mini",
        capabilities=[
            ModelCapability.GENERAL,
            ModelCapability.EDITING,
        ],
        max_tokens=16384,
        temperature=0.7,
        timeout_seconds=20,
        priority=2,
        provider="openai",
        cost_tier="low",
    ),

    # OpenRouter free tier models (for fallback)
    "gemma-4-150b:free": ModelConfig(
        model_id="gemma-4-150b:free",
        capabilities=[
            ModelCapability.GENERAL,
            ModelCapability.EDITING,
        ],
        max_tokens=4096,
        temperature=0.7,
        timeout_seconds=30,
        priority=10,  # Low priority, only for fallback
        provider="openrouter",
        cost_tier="free",
    ),
    "xiaomi/mimo:free": ModelConfig(
        model_id="xiaomi/mimo:free",
        capabilities=[
            ModelCapability.GENERAL,
            ModelCapability.EDITING,
        ],
        max_tokens=4096,
        temperature=0.7,
        timeout_seconds=30,
        priority=10,
        provider="openrouter",
        cost_tier="free",
    ),
    "meta-llama/llama-3-8b-instruct:free": ModelConfig(
        model_id="meta-llama/llama-3-8b-instruct:free",
        capabilities=[
            ModelCapability.GENERAL,
            ModelCapability.EDITING,
        ],
        max_tokens=4096,
        temperature=0.7,
        timeout_seconds=30,
        priority=10,
        provider="openrouter",
        cost_tier="free",
    ),

    # ── Google Gemini ──────────────────────────────────────────────────────────
    "gemini-2.5-pro": ModelConfig(
        model_id="gemini-2.5-pro",
        capabilities=[ModelCapability.GENERAL, ModelCapability.RESEARCH, ModelCapability.REASONING, ModelCapability.CREATIVE],
        max_tokens=8192, temperature=0.7, timeout_seconds=30, priority=1, provider="google", cost_tier="medium",
    ),
    "gemini-2.5-flash": ModelConfig(
        model_id="gemini-2.5-flash",
        capabilities=[ModelCapability.GENERAL, ModelCapability.EDITING],
        max_tokens=8192, temperature=0.7, timeout_seconds=20, priority=2, provider="google", cost_tier="low",
    ),

    # ── Groq ──────────────────────────────────────────────────────────────────
    "llama-3.3-70b-versatile": ModelConfig(
        model_id="llama-3.3-70b-versatile",
        capabilities=[ModelCapability.GENERAL, ModelCapability.EDITING, ModelCapability.CREATIVE],
        max_tokens=8192, temperature=0.7, timeout_seconds=15, priority=3, provider="groq", cost_tier="free",
    ),
    "llama-3.1-8b-instant": ModelConfig(
        model_id="llama-3.1-8b-instant",
        capabilities=[ModelCapability.GENERAL, ModelCapability.EDITING],
        max_tokens=8192, temperature=0.7, timeout_seconds=10, priority=5, provider="groq", cost_tier="free",
    ),

    # ── DeepSeek ──────────────────────────────────────────────────────────────
    "deepseek-chat": ModelConfig(
        model_id="deepseek-chat",
        capabilities=[ModelCapability.GENERAL, ModelCapability.RESEARCH, ModelCapability.EDITING],
        max_tokens=8192, temperature=0.7, timeout_seconds=30, priority=2, provider="deepseek", cost_tier="low",
    ),
    "deepseek-reasoner": ModelConfig(
        model_id="deepseek-reasoner",
        capabilities=[ModelCapability.REASONING, ModelCapability.FACT_CHECK],
        max_tokens=8192, temperature=0.6, timeout_seconds=60, priority=2, provider="deepseek", cost_tier="low",
    ),

    # ── Mistral AI ─────────────────────────────────────────────────────────────
    "mistral-large-latest": ModelConfig(
        model_id="mistral-large-latest",
        capabilities=[ModelCapability.GENERAL, ModelCapability.CREATIVE, ModelCapability.RESEARCH],
        max_tokens=8192, temperature=0.7, timeout_seconds=30, priority=2, provider="mistral", cost_tier="medium",
    ),
    "mistral-small-latest": ModelConfig(
        model_id="mistral-small-latest",
        capabilities=[ModelCapability.GENERAL, ModelCapability.EDITING],
        max_tokens=8192, temperature=0.7, timeout_seconds=20, priority=3, provider="mistral", cost_tier="low",
    ),

    # ── xAI ───────────────────────────────────────────────────────────────────
    "grok-3": ModelConfig(
        model_id="grok-3",
        capabilities=[ModelCapability.GENERAL, ModelCapability.RESEARCH, ModelCapability.CREATIVE],
        max_tokens=8192, temperature=0.7, timeout_seconds=30, priority=2, provider="xai", cost_tier="medium",
    ),
    "grok-3-mini": ModelConfig(
        model_id="grok-3-mini",
        capabilities=[ModelCapability.GENERAL, ModelCapability.EDITING],
        max_tokens=8192, temperature=0.7, timeout_seconds=20, priority=3, provider="xai", cost_tier="low",
    ),

    # ── Together AI ───────────────────────────────────────────────────────────
    "meta-llama/Llama-3.3-70B-Instruct-Turbo": ModelConfig(
        model_id="meta-llama/Llama-3.3-70B-Instruct-Turbo",
        capabilities=[ModelCapability.GENERAL, ModelCapability.CREATIVE, ModelCapability.EDITING],
        max_tokens=8192, temperature=0.7, timeout_seconds=30, priority=3, provider="together", cost_tier="low",
    ),

    # ── Perplexity (search-augmented) ──────────────────────────────────────────
    "sonar-pro": ModelConfig(
        model_id="sonar-pro",
        capabilities=[ModelCapability.RESEARCH, ModelCapability.FACT_CHECK],
        max_tokens=8192, temperature=0.5, timeout_seconds=30, priority=2, provider="perplexity", cost_tier="medium",
    ),

    # ── Moonshot / Kimi ────────────────────────────────────────────────────────
    "moonshot-v1-128k": ModelConfig(
        model_id="moonshot-v1-128k",
        capabilities=[ModelCapability.GENERAL, ModelCapability.RESEARCH],
        max_tokens=4096, temperature=0.7, timeout_seconds=30, priority=3, provider="moonshot", cost_tier="low",
    ),

    # ── Cerebras (ultra-fast free) ─────────────────────────────────────────────
    "llama3.1-70b": ModelConfig(
        model_id="llama3.1-70b",
        capabilities=[ModelCapability.GENERAL, ModelCapability.EDITING],
        max_tokens=8192, temperature=0.7, timeout_seconds=10, priority=4, provider="cerebras", cost_tier="free",
    ),

    # ── Qwen ──────────────────────────────────────────────────────────────────
    "qwen-max": ModelConfig(
        model_id="qwen-max",
        capabilities=[ModelCapability.GENERAL, ModelCapability.CREATIVE, ModelCapability.RESEARCH],
        max_tokens=8192, temperature=0.7, timeout_seconds=30, priority=3, provider="qwen", cost_tier="medium",
    ),
    "qwq-32b": ModelConfig(
        model_id="qwq-32b",
        capabilities=[ModelCapability.REASONING],
        max_tokens=8192, temperature=0.6, timeout_seconds=60, priority=3, provider="qwen", cost_tier="low",
    ),
}

# Model routing: map capabilities to models
# Models are sorted by priority (lower = preferred)
MODEL_ROUTING: dict[ModelCapability, list[ModelConfig]] = {
    ModelCapability.GENERAL: [
        MODEL_CONFIGS["claude-sonnet-4-20250514"],
        MODEL_CONFIGS["gpt-4o"],
        MODEL_CONFIGS["gemini-2.5-pro"],
        MODEL_CONFIGS["claude-haiku-4-20250514"],
        MODEL_CONFIGS["gpt-4o-mini"],
        MODEL_CONFIGS["gemini-2.5-flash"],
        MODEL_CONFIGS["llama-3.3-70b-versatile"],  # Groq free
        MODEL_CONFIGS["deepseek-chat"],
        MODEL_CONFIGS["llama3.1-70b"],  # Cerebras free
    ],
    ModelCapability.RESEARCH: [
        MODEL_CONFIGS["claude-sonnet-4-20250514"],
        MODEL_CONFIGS["sonar-pro"],  # Perplexity search-augmented
        MODEL_CONFIGS["gpt-4o"],
        MODEL_CONFIGS["gemini-2.5-pro"],
        MODEL_CONFIGS["claude-opus-4-20250514"],
        MODEL_CONFIGS["deepseek-chat"],
        MODEL_CONFIGS["moonshot-v1-128k"],
        MODEL_CONFIGS["gpt-4-turbo"],
    ],
    ModelCapability.SCORING: [
        MODEL_CONFIGS["claude-sonnet-4-20250514"],
        MODEL_CONFIGS["gpt-4o"],
        MODEL_CONFIGS["claude-haiku-4-20250514"],
        MODEL_CONFIGS["gpt-4o-mini"],
        MODEL_CONFIGS["gemini-2.5-flash"],
        MODEL_CONFIGS["llama-3.1-8b-instant"],  # Groq fast
    ],
    ModelCapability.FACT_CHECK: [
        MODEL_CONFIGS["claude-sonnet-4-20250514"],
        MODEL_CONFIGS["sonar-pro"],  # Perplexity with web search
        MODEL_CONFIGS["gpt-4o"],
        MODEL_CONFIGS["deepseek-reasoner"],
    ],
    ModelCapability.CREATIVE: [
        MODEL_CONFIGS["claude-opus-4-20250514"],
        MODEL_CONFIGS["gpt-4-turbo"],
        MODEL_CONFIGS["claude-sonnet-4-20250514"],
        MODEL_CONFIGS["mistral-large-latest"],
        MODEL_CONFIGS["gpt-4o"],
        MODEL_CONFIGS["grok-3"],
        MODEL_CONFIGS["qwen-max"],
        MODEL_CONFIGS["meta-llama/Llama-3.3-70B-Instruct-Turbo"],
    ],
    ModelCapability.EDITING: [
        MODEL_CONFIGS["claude-sonnet-4-20250514"],
        MODEL_CONFIGS["gpt-4o"],
        MODEL_CONFIGS["claude-haiku-4-20250514"],
        MODEL_CONFIGS["gpt-4o-mini"],
        MODEL_CONFIGS["mistral-small-latest"],
        MODEL_CONFIGS["llama-3.3-70b-versatile"],  # Groq free
        MODEL_CONFIGS["deepseek-chat"],
        MODEL_CONFIGS["gemini-2.5-flash"],
    ],
    ModelCapability.REASONING: [
        MODEL_CONFIGS["claude-sonnet-4-20250514"],
        MODEL_CONFIGS["claude-opus-4-20250514"],
        MODEL_CONFIGS["deepseek-reasoner"],
        MODEL_CONFIGS["gpt-4o"],
        MODEL_CONFIGS["gemini-2.5-pro"],
        MODEL_CONFIGS["qwq-32b"],
        MODEL_CONFIGS["grok-3"],
    ],
}

# OpenRouter fallback models (free tier)
# Used when all primary models fail
OPENROUTER_FALLBACK_MODELS: list[str] = [
    "gemma-4-150b:free",
    "xiaomi/mimo:free",
    "meta-llama/llama-3-8b-instruct:free",
]

# Model capability descriptions for UI/Logging
MODEL_CAPABILITIES: dict[ModelCapability, str] = {
    ModelCapability.GENERAL: "General purpose tasks",
    ModelCapability.RESEARCH: "Research and analysis",
    ModelCapability.SCORING: "Content scoring and evaluation",
    ModelCapability.FACT_CHECK: "Fact verification",
    ModelCapability.CREATIVE: "Creative writing and ideation",
    ModelCapability.EDITING: "Content editing and refinement",
    ModelCapability.REASONING: "Complex reasoning and logic",
}


def get_models_for_capability(capability: ModelCapability) -> list[ModelConfig]:
    """
    Get models sorted by priority for a given capability.

    Args:
        capability: The capability to get models for

    Returns:
        List of ModelConfig objects sorted by priority (lowest first)
    """
    models = MODEL_ROUTING.get(capability, [])
    return sorted(models, key=lambda m: m.priority)


def get_model_ids_for_capability(capability: ModelCapability) -> list[str]:
    """
    Get model IDs for a given capability.

    Args:
        capability: The capability to get model IDs for

    Returns:
        List of model IDs sorted by priority
    """
    models = get_models_for_capability(capability)
    return [m.model_id for m in models]


def get_model_config(model_id: str) -> ModelConfig | None:
    """
    Get configuration for a specific model.

    Args:
        model_id: Model identifier

    Returns:
        ModelConfig or None if model not found
    """
    return MODEL_CONFIGS.get(model_id)


def get_primary_models_for_capability(capability: ModelCapability) -> list[str]:
    """
    Get primary (non-free) models for a capability.

    Args:
        capability: The capability to get models for

    Returns:
        List of primary model IDs
    """
    models = get_models_for_capability(capability)
    return [m.model_id for m in models if m.cost_tier != "free"]


def get_fallback_models_for_capability(capability: ModelCapability) -> list[str]:
    """
    Get fallback models for a capability.

    Returns free tier models that can be used as fallbacks.

    Args:
        capability: The capability to get fallback models for

    Returns:
        List of fallback model IDs
    """
    # For now, return all free tier models
    # In production, you might want to match capability to fallback models
    return OPENROUTER_FALLBACK_MODELS


def get_all_models() -> list[str]:
    """Get all configured model IDs."""
    return list(MODEL_CONFIGS.keys())


def get_models_by_provider(provider: str) -> list[str]:
    """
    Get all models from a specific provider.

    Args:
        provider: Provider name (anthropic, openai, openrouter)

    Returns:
        List of model IDs from that provider
    """
    return [
        model_id
        for model_id, config in MODEL_CONFIGS.items()
        if config.provider == provider
    ]


def get_models_by_cost_tier(cost_tier: str) -> list[str]:
    """
    Get all models in a specific cost tier.

    Args:
        cost_tier: Cost tier (free, low, medium, high)

    Returns:
        List of model IDs in that tier
    """
    return [
        model_id
        for model_id, config in MODEL_CONFIGS.items()
        if config.cost_tier == cost_tier
    ]


# Validation on startup
def _validate_configuration():
    """Validate the model configuration on startup."""
    # Check that all models in routing have configs
    for capability, models in MODEL_ROUTING.items():
        for model in models:
            if model.model_id not in MODEL_CONFIGS:
                logger.error(
                    f"Model {model.model_id} in routing but not in MODEL_CONFIGS"
                )

    # Check that all fallback models have configs
    for model_id in OPENROUTER_FALLBACK_MODELS:
        if model_id not in MODEL_CONFIGS:
            logger.error(
                f"Fallback model {model_id} not in MODEL_CONFIGS"
            )

    logger.info("Model configuration validated successfully")


# Run validation on import
_validate_configuration()

logger.info(
    f"Loaded {len(MODEL_CONFIGS)} model configurations "
    f"for {len(MODEL_ROUTING)} capabilities"
)
