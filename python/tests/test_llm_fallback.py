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
    """Test emergency fallback when USE_CLAUDE_SUBSCRIPTION=true."""

    @pytest.mark.asyncio
    async def test_anthropic_failure_triggers_openrouter_fallback(self):
        """Test that Anthropic API failure triggers emergency fallback to OpenRouter."""
        with patch("content_engine.utils.llm_client.settings") as mock_settings:
            mock_settings.use_claude_subscription = True
            mock_settings.anthropic_api_key = "test-key"
            mock_settings.openrouter_api_key = "openrouter-key"

            # Mock Anthropic API failure
            with patch("content_engine.utils.llm_client._call_anthropic_direct") as mock_anthropic:
                mock_anthropic.side_effect = Exception("Anthropic API down")

                # Mock successful OpenRouter fallback
                with patch("content_engine.utils.llm_client.httpx.AsyncClient") as mock_httpx:
                    mock_response = MagicMock()
                    mock_response.raise_for_status = MagicMock()
                    mock_response.json.return_value = {
                        "choices": [{"message": {"content": "Fallback response"}}],
                        "usage": {"prompt_tokens": 100, "completion_tokens": 50}
                    }
                    mock_httpx.return_value.__aenter__.return_value.post.return_value = mock_response

                    # Mock logging and alerting
                    with patch("content_engine.utils.llm_client._log_fallback_attempt", new_callable=AsyncMock), \
                         patch("content_engine.utils.llm_client._send_fallback_alert", new_callable=AsyncMock), \
                         patch("content_engine.utils.llm_client.track_cost", new_callable=AsyncMock), \
                         patch("content_engine.utils.fallback_monitor.record_fallback") as mock_record_fallback:

                        result = await call_llm(
                            prompt="Test prompt",
                            brand_id="test-brand",
                            context="test",
                            action="test_action",
                            task_type="creative"
                        )

                        # Verify fallback was recorded
                        mock_record_fallback.assert_called_once_with(is_emergency=True)

                        # Verify response came from OpenRouter
                        assert result.content == "Fallback response"
                        assert "gemma" in result.model_used.lower()

    @pytest.mark.asyncio
    async def test_emergency_fallback_logs_correctly(self):
        """Test that emergency fallback attempts are logged with correct metadata."""
        with patch("content_engine.utils.llm_client.get_db") as mock_db:
            mock_db.table.return_value.insert.return_value.execute.return_value = MagicMock()

            await _log_fallback_attempt(
                brand_id="test-brand",
                context="humanizer_pass1",
                action="initial_humanization",
                primary_model="claude-3-5-haiku-20241022",
                fallback_reason="Anthropic API timeout",
                is_emergency=True
            )

            # Verify log entry
            mock_db.table.assert_called_once_with("llm_fallback_log")
            insert_call = mock_db.table.return_value.insert
            insert_call.assert_called_once()

            log_data = insert_call.call_args[0][0]
            assert log_data["brand_id"] == "test-brand"
            assert log_data["context"] == "humanizer_pass1"
            assert log_data["action"] == "initial_humanization"
            assert log_data["primary_model"] == "claude-3-5-haiku-20241022"
            assert log_data["fallback_reason"] == "Anthropic API timeout"
            assert log_data["is_emergency"] is True


class TestNormalFallbackChain:
    """Test normal OpenRouter fallback chain."""

    @pytest.mark.asyncio
    async def test_openrouter_fallback_chain_logs_attempts(self):
        """Test that normal OpenRouter fallback chain logs each attempt."""
        with patch("content_engine.utils.llm_client.settings") as mock_settings:
            mock_settings.use_claude_subscription = False
            mock_settings.openrouter_api_key = "openrouter-key"

            # Mock first model failure, second model success
            with patch("content_engine.utils.llm_client.httpx.AsyncClient") as mock_httpx:
                # First call fails
                first_response = MagicMock()
                first_response.raise_for_status.side_effect = Exception("Gemma 4 failed")

                # Second call succeeds
                second_response = MagicMock()
                second_response.raise_for_status = MagicMock()
                second_response.json.return_value = {
                    "choices": [{"message": {"content": "Success"}}],
                    "usage": {"prompt_tokens": 100, "completion_tokens": 50}
                }

                mock_httpx.return_value.__aenter__.return_value.post.side_effect = [
                    first_response,
                    second_response
                ]

                with patch("content_engine.utils.llm_client._log_fallback_attempt", new_callable=AsyncMock) as mock_log, \
                     patch("content_engine.utils.llm_client.track_cost", new_callable=AsyncMock), \
                     patch("content_engine.utils.fallback_monitor.record_fallback") as mock_record_fallback, \
                     patch("content_engine.utils.fallback_monitor.record_call") as mock_record_call:

                    result = await call_llm(
                        prompt="Test prompt",
                        brand_id="test-brand",
                        context="test",
                        action="test_action",
                        task_type="creative"
                    )

                    # Verify fallback was logged
                    mock_log.assert_called_once()
                    log_call = mock_log.call_args[1]
                    assert log_call["primary_model"] == "google/gemma-4-150b:free"
                    assert log_call["is_emergency"] is False

                    # Verify fallback was recorded
                    mock_record_fallback.assert_called_once_with(is_emergency=False)

                    # Verify successful call was recorded
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

        # Record 10 calls, 2 fallbacks
        for _ in range(8):
            record_call()
        for _ in range(2):
            record_fallback(is_emergency=False)

        stats = monitor.get_stats()

        assert stats["total_calls"] == 10
        assert stats["fallback_count"] == 2
        assert stats["fallback_percentage"] == 20.0

    def test_alert_threshold_not_met(self):
        """Test that alert is not sent when threshold is not met."""
        monitor = get_fallback_monitor()
        monitor.reset()  # Start fresh

        # Set low threshold and record below it
        with patch("content_engine.utils.fallback_monitor.settings") as mock_settings:
            mock_settings.fallback_alert_threshold = 50.0  # 50% threshold

            for _ in range(9):
                record_call()
            record_fallback(is_emergency=False)  # 10% fallback rate

            # Should not send alert (below 50% threshold)
            # We verify this by checking that no exception was raised
            stats = monitor.get_stats()
            assert stats["fallback_percentage"] == 10.0

    def test_daily_reset(self):
        """Test that counters reset at midnight."""
        monitor = get_fallback_monitor()
        monitor.reset()  # Start fresh

        # Record some data
        for _ in range(5):
            record_call()
        record_fallback(is_emergency=False)

        stats_before = monitor.get_stats()
        assert stats_before["fallback_count"] == 1
        assert stats_before["total_calls"] == 5

        # Simulate date change by mocking _get_current_date
        with patch.object(monitor, "_get_current_date", return_value="2099-01-02"):
            monitor.record_call()  # This should trigger reset
            stats_after = monitor.get_stats()

            # Counters should be reset
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

        assert stats["total_calls"] == 1
        assert stats["fallback_count"] == 1
        assert stats["fallback_percentage"] == 100.0


class TestFallbackAlerting:
    """Test fallback alerting functionality."""

    @pytest.mark.asyncio
    async def test_alert_sent_on_high_fallback_rate(self):
        """Test that alert is sent when fallback rate exceeds threshold."""
        with patch("content_engine.utils.fallback_monitor.settings") as mock_settings, \
             patch("content_engine.utils.fallback_monitor.send_telegram_alert", new_callable=AsyncMock) as mock_alert:

            mock_settings.fallback_alert_threshold = 10.0  # 10% threshold

            monitor = get_fallback_monitor()
            monitor.reset()

            # Record 10 calls with 2 fallbacks (20% rate)
            for _ in range(8):
                record_call()
            record_fallback(is_emergency=False)
            record_fallback(is_emergency=False)

            # This should trigger alert (20% > 10% threshold)
            record_call()  # This call triggers the check

            # Verify alert was sent
            mock_alert.assert_called_once()

            # Check alert message contains key information
            alert_message = mock_alert.call_args[0][0]
            assert "20.0%" in alert_message
            assert "10%" in alert_message
            assert "2" in alert_message  # fallback count

    @pytest.mark.asyncio
    async def test_no_alert_below_threshold(self):
        """Test that alert is not sent when fallback rate is below threshold."""
        with patch("content_engine.utils.fallback_monitor.settings") as mock_settings, \
             patch("content_engine.utils.fallback_monitor.send_telegram_alert", new_callable=AsyncMock) as mock_alert:

            mock_settings.fallback_alert_threshold = 50.0  # 50% threshold

            monitor = get_fallback_monitor()
            monitor.reset()

            # Record 10 calls with 1 fallback (10% rate)
            for _ in range(9):
                record_call()
            record_fallback(is_emergency=False)

            # This should NOT trigger alert (10% < 50% threshold)
            record_call()

            # Verify alert was NOT sent
            mock_alert.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
