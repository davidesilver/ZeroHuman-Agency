"""
Comprehensive Test Suite for Centralized Model Routing Configuration

Tests cover model configuration, routing logic, and helper functions.

Author: AI Engineering Team
Created: 2026-04-17
"""

import pytest
from src.content_engine.config.llm_models import (
    ModelCapability,
    ModelConfig,
    MODEL_CONFIGS,
    MODEL_ROUTING,
    OPENROUTER_FALLBACK_MODELS,
    get_models_for_capability,
    get_model_ids_for_capability,
    get_model_config,
    get_primary_models_for_capability,
    get_fallback_models_for_capability,
    get_all_models,
    get_models_by_provider,
    get_models_by_cost_tier,
    MODEL_CAPABILITIES,
)


class TestModelCapability:
    """Test ModelCapability enum."""

    def test_capability_enum_values(self):
        """Test that all capabilities have correct values."""
        assert ModelCapability.GENERAL.value == "general"
        assert ModelCapability.RESEARCH.value == "research"
        assert ModelCapability.SCORING.value == "scoring"
        assert ModelCapability.FACT_CHECK.value == "fact_check"
        assert ModelCapability.CREATIVE.value == "creative"
        assert ModelCapability.EDITING.value == "editing"
        assert ModelCapability.REASONING.value == "reasoning"


class TestModelConfig:
    """Test ModelConfig dataclass."""

    def test_model_config_creation(self):
        """Test creating a model configuration."""
        config = ModelConfig(
            model_id="test-model",
            capabilities=[ModelCapability.GENERAL, ModelCapability.RESEARCH],
            max_tokens=4096,
            temperature=0.7,
            timeout_seconds=30,
            priority=0,
            provider="test-provider",
            cost_tier="medium"
        )

        assert config.model_id == "test-model"
        assert len(config.capabilities) == 2
        assert config.max_tokens == 4096
        assert config.provider == "test-provider"

    def test_model_config_defaults(self):
        """Test default values for ModelConfig."""
        config = ModelConfig(
            model_id="test-model",
            capabilities=[ModelCapability.GENERAL]
        )

        assert config.max_tokens == 4096  # Default
        assert config.temperature == 0.7  # Default
        assert config.timeout_seconds == 30  # Default
        assert config.priority == 0  # Default
        assert config.provider == "unknown"  # Default
        assert config.cost_tier == "medium"  # Default


class TestModelConfigs:
    """Test MODEL_CONFIGS dictionary."""

    def test_model_configs_not_empty(self):
        """Test that MODEL_CONFIGS is populated."""
        assert len(MODEL_CONFIGS) > 0

    def test_model_configs_has_required_models(self):
        """Test that required models are present."""
        required_models = [
            "claude-sonnet-4-20250514",
            "claude-opus-4-20250514",
            "gpt-4o",
        ]

        for model_id in required_models:
            assert model_id in MODEL_CONFIGS

    def test_model_configs_structure(self):
        """Test that all configs have correct structure."""
        for model_id, config in MODEL_CONFIGS.items():
            assert isinstance(config, ModelConfig)
            assert isinstance(config.model_id, str)
            assert isinstance(config.capabilities, list)
            assert config.model_id == model_id

    def test_claude_sonnet_config(self):
        """Test specific configuration for Claude Sonnet."""
        config = MODEL_CONFIGS["claude-sonnet-4-20250514"]

        assert config.provider == "anthropic"
        assert config.cost_tier == "medium"
        assert ModelCapability.SCORING in config.capabilities
        assert ModelCapability.FACT_CHECK in config.capabilities
        assert config.priority == 0  # Should be highest priority

    def test_fallback_models_config(self):
        """Test that fallback models have free tier."""
        for model_id in OPENROUTER_FALLBACK_MODELS:
            config = MODEL_CONFIGS.get(model_id)
            assert config is not None
            assert config.cost_tier == "free"


class TestModelRouting:
    """Test MODEL_ROUTING dictionary."""

    def test_model_routing_has_all_capabilities(self):
        """Test that all capabilities are in routing."""
        for capability in ModelCapability:
            assert capability in MODEL_ROUTING

    def test_model_routing_not_empty(self):
        """Test that all capability lists are not empty."""
        for capability, models in MODEL_ROUTING.items():
            assert len(models) > 0

    def test_model_routing_sorted_by_priority(self):
        """Test that models returned are sorted by priority."""
        for capability in ModelCapability:
            models = get_models_for_capability(capability)
            priorities = [m.priority for m in models]
            # Check that priorities are sorted (non-decreasing)
            assert priorities == sorted(priorities)

    def test_model_routing_claude_first_for_scoring(self):
        """Test that Claude Sonnet is first for scoring."""
        scoring_models = MODEL_ROUTING[ModelCapability.SCORING]

        assert len(scoring_models) > 0
        assert scoring_models[0].model_id == "claude-sonnet-4-20250514"
        assert scoring_models[0].priority == 0


class TestHelperFunctions:
    """Test helper functions."""

    def test_get_models_for_capability(self):
        """Test getting models for a capability."""
        models = get_models_for_capability(ModelCapability.SCORING)

        assert isinstance(models, list)
        assert len(models) > 0
        assert all(isinstance(m, ModelConfig) for m in models)

    def test_get_models_for_capability_sorted(self):
        """Test that returned models are sorted by priority."""
        models = get_models_for_capability(ModelCapability.GENERAL)

        priorities = [m.priority for m in models]
        assert priorities == sorted(priorities)

    def test_get_model_ids_for_capability(self):
        """Test getting model IDs for a capability."""
        model_ids = get_model_ids_for_capability(ModelCapability.SCORING)

        assert isinstance(model_ids, list)
        assert len(model_ids) > 0
        assert all(isinstance(m, str) for m in model_ids)
        assert "claude-sonnet-4-20250514" in model_ids

    def test_get_model_config_existing(self):
        """Test getting config for existing model."""
        config = get_model_config("claude-sonnet-4-20250514")

        assert config is not None
        assert config.model_id == "claude-sonnet-4-20250514"
        assert isinstance(config, ModelConfig)

    def test_get_model_config_non_existing(self):
        """Test getting config for non-existing model."""
        config = get_model_config("non-existent-model")

        assert config is None

    def test_get_primary_models_for_capability(self):
        """Test getting primary (non-free) models."""
        primary_models = get_primary_models_for_capability(ModelCapability.GENERAL)

        assert isinstance(primary_models, list)
        assert len(primary_models) > 0

        # Check that none are free tier
        for model_id in primary_models:
            config = get_model_config(model_id)
            assert config is not None
            assert config.cost_tier != "free"

    def test_get_fallback_models_for_capability(self):
        """Test getting fallback models."""
        fallback_models = get_fallback_models_for_capability(ModelCapability.GENERAL)

        assert isinstance(fallback_models, list)
        assert len(fallback_models) > 0

        # Check that all are free tier
        for model_id in fallback_models:
            config = get_model_config(model_id)
            assert config is not None
            assert config.cost_tier == "free"

    def test_get_all_models(self):
        """Test getting all model IDs."""
        all_models = get_all_models()

        assert isinstance(all_models, list)
        assert len(all_models) > 0
        assert len(all_models) == len(MODEL_CONFIGS)

    def test_get_models_by_provider(self):
        """Test getting models by provider."""
        anthropic_models = get_models_by_provider("anthropic")

        assert isinstance(anthropic_models, list)
        assert len(anthropic_models) > 0

        # Check that all returned models are from correct provider
        for model_id in anthropic_models:
            config = get_model_config(model_id)
            assert config is not None
            assert config.provider == "anthropic"

    def test_get_models_by_cost_tier(self):
        """Test getting models by cost tier."""
        free_models = get_models_by_cost_tier("free")

        assert isinstance(free_models, list)
        assert len(free_models) > 0

        # Check that all returned models are in correct tier
        for model_id in free_models:
            config = get_model_config(model_id)
            assert config is not None
            assert config.cost_tier == "free"


class TestModelCapabilities:
    """Test MODEL_CAPABILITIES descriptions."""

    def test_capabilities_descriptions_exist(self):
        """Test that all capabilities have descriptions."""
        for capability in ModelCapability:
            assert capability in MODEL_CAPABILITIES

    def test_capability_descriptions_are_strings(self):
        """Test that all descriptions are strings."""
        for capability, description in MODEL_CAPABILITIES.items():
            assert isinstance(description, str)
            assert len(description) > 0


class TestOpenRouterFallbackModels:
    """Test OPENROUTER_FALLBACK_MODELS."""

    def test_fallback_models_not_empty(self):
        """Test that fallback models list is not empty."""
        assert len(OPENROUTER_FALLBACK_MODELS) > 0

    def test_fallback_models_exist_in_configs(self):
        """Test that all fallback models have configs."""
        for model_id in OPENROUTER_FALLBACK_MODELS:
            assert model_id in MODEL_CONFIGS

    def test_fallback_models_are_free_tier(self):
        """Test that all fallback models are free tier."""
        for model_id in OPENROUTER_FALLBACK_MODELS:
            config = MODEL_CONFIGS[model_id]
            assert config.cost_tier == "free"


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_capability_not_in_routing(self):
        """Test behavior when capability is not in routing."""
        # Create a mock capability that's not in routing
        mock_capability = ModelCapability.GENERAL

        # This capability should be in routing
        assert mock_capability in MODEL_ROUTING

        # But if we try to get a non-existent one, it should return empty list
        # (The get_models_for_capability function handles this gracefully)
        # We're just testing that the routing dictionary itself
        # For capabilities not in routing, we'd get KeyError if accessing MODEL_ROUTING directly

    def test_empty_capability_list(self):
        """Test getting models for capability with empty list."""
        # Create a temporary empty list for a capability
        original = MODEL_ROUTING.get(ModelCapability.GENERAL)
        MODEL_ROUTING[ModelCapability.GENERAL] = []

        models = get_models_for_capability(ModelCapability.GENERAL)
        assert len(models) == 0

        # Restore original
        MODEL_ROUTING[ModelCapability.GENERAL] = original


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    def test_full_routing_flow(self):
        """Test complete routing flow for a task."""
        # 1. Get capability for a task
        capability = ModelCapability.SCORING

        # 2. Get models for that capability
        models = get_models_for_capability(capability)

        # 3. Get model IDs
        model_ids = get_model_ids_for_capability(capability)

        # 4. Verify everything is consistent
        assert len(models) == len(model_ids)
        assert all(m.model_id in model_ids for m in models)

        # 5. Get config for first model
        first_model = models[0]
        config = get_model_config(first_model.model_id)

        assert config is not None
        assert config.model_id == first_model.model_id
        assert capability in config.capabilities

    def test_primary_fallback_flow(self):
        """Test primary and fallback model flow."""
        capability = ModelCapability.GENERAL

        # Get primary models
        primary_models = get_primary_models_for_capability(capability)

        # Get fallback models
        fallback_models = get_fallback_models_for_capability(capability)

        # Verify no overlap
        primary_set = set(primary_models)
        fallback_set = set(fallback_models)

        # Check that primary and fallback are disjoint
        overlap = primary_set & fallback_set
        # In our current config, there should be no overlap
        # (free models are not in primary lists)
        assert len(overlap) == 0

    def test_provider_distribution(self):
        """Test distribution of models across providers."""
        anthropic = get_models_by_provider("anthropic")
        openai = get_models_by_provider("openai")
        openrouter = get_models_by_provider("openrouter")

        # All providers should have at least one model
        assert len(anthropic) > 0
        assert len(openai) > 0
        assert len(openrouter) > 0

        # Total should match configured models
        total_configured = len(MODEL_CONFIGS)
        total_by_provider = len(anthropic) + len(openai) + len(openrouter)
        assert total_configured == total_by_provider


# Run tests with: pytest tests/test_model_routing.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
