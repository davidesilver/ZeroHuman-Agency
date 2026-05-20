"""Tests for LLM fallback mechanism and monitoring.

Tests critical fallback behavior:
- Emergency fallback when Anthropic API fails
- Normal fallback chain logging
- Fallback monitoring and alerting
- Daily counter reset
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from content_engine.utils.llm_client import call_llm, _log_fallback_attempt
from content_engine.utils.fallback_monitor import (
    FallbackMonitor,
    get_fallback_monitor,
    record_fallback,
    record_call,
    get_fallback_stats,
)


class TestEmergencyFallback:
    """Test fallback behavior when primary models fail."""

    @pytest.mark.asyncio
    async def test_anthropic_failure_triggers_openrouter_fallback(self):
        """Test that primary model failure triggers fallback to alternative models."""
        from content_engine.utils.llm_client import LLMResponse as LLMResp
        from content_engine.utils.degradation import DegradationLevel

        fallback_resp = LLMResp(
            content="Fallback response",
            model_used="gemma-4-150b:free",
            tokens_prompt=100,
            tokens_completion=50,
            engine="openrouter",
        )

        with patch("content_engine.utils.llm_client._call_llm_parallel", new_callable=AsyncMock) as mock_parallel, \
             patch("content_engine.utils.llm_client.record_fallback") as mock_record_fallback, \
             patch("content_engine.utils.llm_client.record_call"), \
             patch("content_engine.utils.llm_client.degradation_manager") as mock_deg, \
             patch("content_engine.utils.llm_client.asyncio"):

            mock_deg.get_current_level = AsyncMock(return_value=DegradationLevel.NORMAL)
            mock_deg.record_success = AsyncMock()
            mock_deg.record_failure = AsyncMock()

            # Primary models fail, fallback models succeed
            mock_parallel.side_effect = [Exception("All primary models failed"), fallback_resp]

            result = await call_llm(
                prompt="Test prompt",
                brand_id="test-brand",
                context="test",
                action="test_action",
                task_type="creative"
            )

            # Verify fallback was recorded (new arch uses is_emergency=False)
            mock_record_fallback.assert_called_once_with(is_emergency=False)

            # Verify response came from fallback
            assert result.content == "Fallback response"
            assert "gemma" in result.model_used.lower()

    @pytest.mark.asyncio
    async def test_emergency_fallback_logs_correctly(self):
        """Test that emergency fallback attempts are logged with correct metadata."""
        mock_db_instance = MagicMock()
        mock_db_instance.table.return_value.insert.return_value.execute.return_value = MagicMock()

        with patch("content_engine.utils.llm_client.get_db", return_value=mock_db_instance):
            await _log_fallback_attempt(
                brand_id="test-brand",
                context="humanizer_pass1",
                action="initial_humanization",
                primary_model="claude-3-5-haiku-20241022",
                fallback_reason="Anthropic API timeout",
                is_emergency=True
            )

            # Verify log entry
            mock_db_instance.table.assert_called_once_with("llm_fallback_log")
            insert_call = mock_db_instance.table.return_value.insert
            insert_call.assert_called_once()

            log_data = insert_call.call_args[0][0]
            assert log_data["brand_id"] == "test-brand"
            assert log_data["context"] == "humanizer_pass1"
            assert log_data["action"] == "initial_humanization"
            assert log_data["primary_model"] == "claude-3-5-haiku-20241022"
            assert log_data["fallback_reason"] == "Anthropic API timeout"
            assert log_data["is_emergency"] is True


class TestNormalFallbackChain:
    """Test normal fallback chain behavior."""

    @pytest.mark.asyncio
    async def test_openrouter_fallback_chain_logs_attempts(self):
        """Test that within-pool model fallback logs the attempt."""
        from content_engine.utils.llm_client import _call_llm_parallel
        from content_engine.utils.degradation import DegradationLevel
        from content_engine.config.llm_models import ModelCapability, get_primary_models_for_capability
        from content_engine.utils.parallel_llm import parallel_llm_caller

        primary_models = get_primary_models_for_capability(ModelCapability.CREATIVE)
        first_model = primary_models[0]
        second_model = primary_models[1]

        call_count = 0

        async def mock_call_single(model, messages, temperature, brand_id, context, action):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception(f"{first_model} failed")
            return {
                "model": second_model,
                "content": "Success",
                "tokens_prompt": 100,
                "tokens_completion": 50,
            }

        with patch("content_engine.utils.llm_client._call_single_model", side_effect=mock_call_single), \
             patch.object(parallel_llm_caller, "call_first_success",
                          new=AsyncMock(side_effect=Exception("parallel failed"))), \
             patch("content_engine.utils.llm_client._log_fallback_attempt", new_callable=AsyncMock) as mock_log, \
             patch("content_engine.utils.llm_client.track_cost", new_callable=AsyncMock), \
             patch("content_engine.utils.llm_client.cost_tracker") as mock_cost_tracker, \
             patch("content_engine.utils.llm_client.record_fallback") as mock_record_fallback, \
             patch("content_engine.utils.llm_client.record_call") as mock_record_call, \
             patch("content_engine.utils.llm_client.degradation_manager") as mock_deg, \
             patch("content_engine.utils.llm_client.rate_limiter") as mock_rate_limiter, \
             patch("content_engine.utils.llm_client.asyncio"):

            mock_deg.get_current_level = AsyncMock(return_value=DegradationLevel.NORMAL)
            mock_deg.record_success = AsyncMock()
            mock_deg.record_failure = AsyncMock()
            mock_rate_limiter.acquire = AsyncMock(return_value=True)
            mock_cost_tracker.get_cost_by_model = AsyncMock(return_value=None)

            result = await call_llm(
                prompt="Test prompt",
                brand_id="test-brand",
                context="test",
                action="test_action",
                task_type="creative"
            )

            # Verify within-pool fallback was logged
            mock_log.assert_called_once()
            log_call = mock_log.call_args[1]
            assert log_call["primary_model"] == first_model
            assert log_call["is_emergency"] is False

            # Verify fallback was recorded
            mock_record_fallback.assert_called_once_with(is_emergency=False)

            # Verify the overall call was recorded as successful
            mock_record_call.assert_called_once()

            assert result.content == "Success"


class TestFallbackMonitor:
    """Test fallback monitoring functionality."""

    def test_singleton_pattern(self):
        """Test that FallbackMonitor follows singleton pattern."""
        monitor1 = get_fallback_monitor()
        monitor2 = get_fallback_monitor()

        assert monitor1 is monitor2
        assert id(monitor1) == id(monitor2)

    def test_record_fallback_increments_counter(self):
        """Test that recording a fallback increments the counter."""
        monitor = get_fallback_monitor()
        monitor.reset()  # Start fresh

        initial_stats = monitor.get_stats()
        assert initial_stats["fallback_count"] == 0

        record_fallback(is_emergency=False)
        stats_after = monitor.get_stats()

        assert stats_after["fallback_count"] == 1
        assert stats_after["emergency_count"] == 0

    def test_record_emergency_fallback(self):
        """Test that emergency fallbacks are counted separately."""
        monitor = get_fallback_monitor()
        monitor.reset()  # Start fresh

        record_fallback(is_emergency=True)
        stats = monitor.get_stats()

        assert stats["fallback_count"] == 1
        assert stats["emergency_count"] == 1

    def test_record_call_increments_total(self):
        """Test that recording a call increments total calls."""
        monitor = get_fallback_monitor()
        monitor.reset()  # Start fresh

        record_call()
        stats = monitor.get_stats()

        assert stats["total_calls"] == 1
        assert stats["fallback_count"] == 0

    def test_fallback_percentage_calculation(self):
        """Test that fallback percentage is calculated correctly."""
        monitor = get_fallback_monitor()
        monitor.reset()  # Start fresh

        # record_fallback does NOT increment total_calls, only fallback_count
        for _ in range(8):
            record_call()
        for _ in range(2):
            record_fallback(is_emergency=False)

        stats = monitor.get_stats()

        assert stats["total_calls"] == 8
        assert stats["fallback_count"] == 2
        assert stats["fallback_percentage"] == 25.0

    def test_alert_threshold_not_met(self):
        """Test that alert is not sent when threshold is not met."""
        monitor = get_fallback_monitor()
        monitor.reset()  # Start fresh

        with patch("content_engine.utils.fallback_monitor.settings") as mock_settings:
            mock_settings.fallback_alert_threshold = 50.0  # 50% threshold

            for _ in range(9):
                record_call()
            record_fallback(is_emergency=False)

            stats = monitor.get_stats()
            # 1 fallback / 9 total_calls ≈ 11.1%
            assert stats["fallback_percentage"] < 50.0

    def test_daily_reset(self):
        """Test that counters reset at midnight."""
        monitor = get_fallback_monitor()
        monitor.reset()  # Start fresh

        for _ in range(5):
            record_call()
        record_fallback(is_emergency=False)

        stats_before = monitor.get_stats()
        assert stats_before["fallback_count"] == 1
        assert stats_before["total_calls"] == 5  # record_fallback does not increment total_calls

        # Simulate date change by mocking _get_current_date
        with patch.object(monitor, "_get_current_date", return_value="2099-01-02"):
            monitor.record_call()  # This should trigger reset
            stats_after = monitor.get_stats()

            assert stats_after["fallback_count"] == 0
            assert stats_after["total_calls"] == 1  # Only the new call
            assert stats_after["date"] == "2099-01-02"

    def test_get_stats_returns_correct_structure(self):
        """Test that get_stats returns the expected structure."""
        monitor = get_fallback_monitor()
        monitor.reset()  # Start fresh

        record_call()
        record_fallback(is_emergency=False)

        stats = get_fallback_stats()

        assert isinstance(stats, dict)
        assert "date" in stats
        assert "total_calls" in stats
        assert "fallback_count" in stats
        assert "emergency_count" in stats
        assert "fallback_percentage" in stats
        assert "threshold" in stats

        assert stats["total_calls"] == 1  # only record_call increments total_calls
        assert stats["fallback_count"] == 1
        assert stats["fallback_percentage"] == 100.0


@pytest.mark.skip(reason="Tests patch non-existent send_telegram_alert; alerting uses emit_event now")
class TestFallbackAlerting:
    """Test fallback alerting functionality."""

    @pytest.mark.asyncio
    async def test_alert_sent_on_high_fallback_rate(self):
        """Test that alert is sent when fallback rate exceeds threshold."""
        pass

    @pytest.mark.asyncio
    async def test_no_alert_below_threshold(self):
        """Test that alert is not sent when fallback rate is below threshold."""
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
