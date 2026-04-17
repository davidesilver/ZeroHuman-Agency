"""
Comprehensive Test Suite for Parallel LLM Calling System

Tests cover parallel model calling, timeout handling, fallback strategies,
and performance metrics.

Author: AI Engineering Team
Created: 2026-04-17
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from src.content_engine.utils.parallel_llm import (
    ParallelLLMCaller,
    ParallelCallMetrics,
    parallel_llm_caller,
    parallel_call_metrics,
)


class TestParallelLLMCaller:
    """Test ParallelLLMCaller implementation."""

    @pytest.mark.asyncio
    async def test_caller_initialization(self):
        """Test caller initialization with default timeouts."""
        caller = ParallelLLMCaller()

        assert caller.timeout_per_model == 30.0
        assert caller.overall_timeout == 60.0
        assert caller._llm_caller is None

    @pytest.mark.asyncio
    async def test_caller_custom_timeouts(self):
        """Test caller initialization with custom timeouts."""
        caller = ParallelLLMCaller(timeout_per_model=15.0, overall_timeout=45.0)

        assert caller.timeout_per_model == 15.0
        assert caller.overall_timeout == 45.0

    @pytest.mark.asyncio
    async def test_set_llm_caller(self):
        """Test setting LLM caller function."""
        caller = ParallelLLMCaller()
        mock_caller = AsyncMock()

        caller.set_llm_caller(mock_caller)

        assert caller._llm_caller is mock_caller

    @pytest.mark.asyncio
    async def test_call_first_success_with_no_models(self):
        """Test calling with no models returns None."""
        caller = ParallelLLMCaller()
        mock_caller = AsyncMock()
        caller.set_llm_caller(mock_caller)

        result, latency = await caller.call_first_success([], "prompt")

        assert result is None
        assert latency == 0.0

    @pytest.mark.asyncio
    async def test_call_first_success_no_caller_set(self):
        """Test calling without setting LLM caller returns None."""
        caller = ParallelLLMCaller()

        result, latency = await caller.call_first_success(
            ["model1"],
            "prompt"
        )

        assert result is None
        assert latency == 0.0

    @pytest.mark.asyncio
    async def test_call_first_success_successful(self):
        """Test successful parallel call."""
        caller = ParallelLLMCaller()
        mock_caller = AsyncMock()

        # Mock successful response
        mock_response = {
            "model": "claude-sonnet-4-20250514",
            "content": "Test response",
            "tokens": 100,
        }
        mock_caller.return_value = mock_response

        caller.set_llm_caller(mock_caller)

        result, latency = await caller.call_first_success(
            ["claude-sonnet-4-20250514"],
            "test prompt",
            "scoring"
        )

        assert result is not None
        assert result["model"] == "claude-sonnet-4-20250514"
        assert latency > 0
        mock_caller.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_first_success_first_wins(self):
        """Test that first successful response is returned."""
        caller = ParallelLLMCaller()

        # Create mock that returns different responses based on model
        async def mock_llm_call(model, prompt, task_type, context, brand_id, agent_name):
            await asyncio.sleep(0.1)  # Simulate network delay
            return {
                "model": model,
                "content": f"Response from {model}",
                "tokens": 100,
            }

        caller.set_llm_caller(mock_llm_call)

        result, latency = await caller.call_first_success(
            ["model1", "model2", "model3"],
            "prompt"
        )

        assert result is not None
        # Should return first model that completes
        assert result["model"] in ["model1", "model2", "model3"]

    @pytest.mark.asyncio
    async def test_call_first_success_all_fail(self):
        """Test that None is returned when all models fail."""
        caller = ParallelLLMCaller()

        # Mock that always raises exception
        async def failing_caller(model, prompt, task_type, context, brand_id, agent_name):
            raise Exception("Model failed")

        caller.set_llm_caller(failing_caller)

        result, latency = await caller.call_first_success(
            ["model1", "model2"],
            "prompt"
        )

        assert result is None
        assert latency > 0

    @pytest.mark.asyncio
    async def test_call_first_success_timeout(self):
        """Test timeout handling."""
        caller = ParallelLLMCaller(timeout_per_model=0.1, overall_timeout=0.2)

        # Mock that takes longer than timeout
        async def slow_caller(model, prompt, task_type, context, brand_id, agent_name):
            await asyncio.sleep(1.0)  # Longer than timeout
            return {"model": model, "content": "response"}

        caller.set_llm_caller(slow_caller)

        result, latency = await caller.call_first_success(
            ["model1"],
            "prompt"
        )

        assert result is None
        assert latency > 0.1  # Should timeout after overall_timeout

    @pytest.mark.asyncio
    async def test_call_with_fallback_primary_succeeds(self):
        """Test fallback when primary succeeds."""
        caller = ParallelLLMCaller()

        async def mock_caller(model, prompt, task_type, context, brand_id, agent_name):
            await asyncio.sleep(0.05)
            return {"model": model, "content": "response"}

        caller.set_llm_caller(mock_caller)

        result, latency, used_fallback = await caller.call_with_fallback(
            primary_models=["primary1", "primary2"],
            fallback_models=["fallback1"],
            prompt="test"
        )

        assert result is not None
        assert used_fallback is False

    @pytest.mark.asyncio
    async def test_call_with_fallback_fallback_used(self):
        """Test fallback when primary fails."""
        caller = ParallelLLMCaller()

        async def failing_caller(model, prompt, task_type, context, brand_id, agent_name):
            if model.startswith("primary"):
                raise Exception("Primary failed")
            else:
                await asyncio.sleep(0.05)
                return {"model": model, "content": "fallback response"}

        caller.set_llm_caller(failing_caller)

        result, latency, used_fallback = await caller.call_with_fallback(
            primary_models=["primary1", "primary2"],
            fallback_models=["fallback1"],
            prompt="test"
        )

        assert result is not None
        assert used_fallback is True
        assert result["model"] == "fallback1"

    @pytest.mark.asyncio
    async def test_get_performance_stats(self):
        """Test getting performance statistics."""
        caller = ParallelLLMCaller()

        stats = caller.get_performance_stats()

        assert "timeout_per_model" in stats
        assert "overall_timeout" in stats
        assert "caller_configured" in stats
        assert stats["caller_configured"] is False

        caller.set_llm_caller(AsyncMock())

        stats = caller.get_performance_stats()
        assert stats["caller_configured"] is True


class TestParallelCallMetrics:
    """Test ParallelCallMetrics implementation."""

    def test_metrics_initialization(self):
        """Test metrics initialization."""
        metrics = ParallelCallMetrics()

        assert metrics.total_calls == 0
        assert metrics.successful_calls == 0
        assert metrics.failed_calls == 0
        assert metrics.total_latency_ms == 0.0
        assert len(metrics.model_success_counts) == 0

    def test_record_successful_call(self):
        """Test recording a successful call."""
        metrics = ParallelCallMetrics()

        metrics.record_call(
            success=True,
            latency_ms=1000,
            model_used="claude-sonnet-4-20250514",
            models_tried=3
        )

        assert metrics.total_calls == 1
        assert metrics.successful_calls == 1
        assert metrics.failed_calls == 0
        assert metrics.total_latency_ms == 1000
        assert metrics.model_success_counts["claude-sonnet-4-20250514"] == 1

    def test_record_failed_call(self):
        """Test recording a failed call."""
        metrics = ParallelCallMetrics()

        metrics.record_call(
            success=False,
            latency_ms=5000,
            models_tried=3
        )

        assert metrics.total_calls == 1
        assert metrics.successful_calls == 0
        assert metrics.failed_calls == 1
        assert metrics.total_latency_ms == 0.0

    def test_record_mixed_calls(self):
        """Test recording mixed success and failure."""
        metrics = ParallelCallMetrics()

        metrics.record_call(success=True, latency_ms=1000, model_used="model1")
        metrics.record_call(success=False, latency_ms=2000)
        metrics.record_call(success=True, latency_ms=1500, model_used="model2")

        assert metrics.total_calls == 3
        assert metrics.successful_calls == 2
        assert metrics.failed_calls == 1
        assert metrics.total_latency_ms == 2500

    def test_get_stats(self):
        """Test getting statistics."""
        metrics = ParallelCallMetrics()

        # Record some calls
        metrics.record_call(success=True, latency_ms=1000, model_used="model1")
        metrics.record_call(success=True, latency_ms=2000, model_used="model1")
        metrics.record_call(success=False, latency_ms=3000)

        stats = metrics.get_stats()

        assert stats["total_calls"] == 3
        assert stats["successful_calls"] == 2
        assert stats["failed_calls"] == 1
        assert stats["success_rate"] == 2/3
        assert stats["avg_latency_ms"] == 1500
        assert stats["model_success_counts"]["model1"] == 2

    def test_get_stats_empty(self):
        """Test getting stats with no calls."""
        metrics = ParallelCallMetrics()

        stats = metrics.get_stats()

        assert stats["total_calls"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["avg_latency_ms"] == 0.0


class TestGlobalInstances:
    """Test global instances."""

    def test_parallel_llm_caller_accessible(self):
        """Test that global parallel caller is accessible."""
        from src.content_engine.utils.parallel_llm import parallel_llm_caller

        assert parallel_llm_caller is not None
        assert isinstance(parallel_llm_caller, ParallelLLMCaller)

    def test_parallel_call_metrics_accessible(self):
        """Test that global metrics is accessible."""
        from src.content_engine.utils.parallel_llm import parallel_call_metrics

        assert parallel_call_metrics is not None
        assert isinstance(parallel_call_metrics, ParallelCallMetrics)


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    @pytest.mark.asyncio
    async def test_concurrent_model_calls(self):
        """Test concurrent calls to multiple models."""
        caller = ParallelLLMCaller()

        # Track which models were called
        called_models = []

        async def mock_caller(model, prompt, task_type, context, brand_id, agent_name):
            called_models.append(model)
            await asyncio.sleep(0.1)  # Simulate different response times
            return {"model": model, "content": f"Response from {model}"}

        caller.set_llm_caller(mock_caller)

        result, latency = await caller.call_first_success(
            ["model1", "model2", "model3"],
            "prompt"
        )

        assert result is not None
        # Should have tried all models (or at least started all tasks)
        assert len(called_models) >= 1

    @pytest.mark.asyncio
    async def test_partial_failure_handling(self):
        """Test handling where some models fail but one succeeds."""
        caller = ParallelLLMCaller()

        async def mixed_caller(model, prompt, task_type, context, brand_id, agent_name):
            await asyncio.sleep(0.1)
            if model == "failing_model":
                raise Exception("This model fails")
            return {"model": model, "content": "Success"}

        caller.set_llm_caller(mixed_caller)

        result, latency = await caller.call_first_success(
            ["failing_model", "working_model"],
            "prompt"
        )

        assert result is not None
        assert result["model"] == "working_model"


# Run tests with: pytest tests/test_parallel_llm.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
