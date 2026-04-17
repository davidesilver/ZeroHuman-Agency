"""
Comprehensive Test Suite for Fallback Metrics System

Tests cover fallback event recording, rate calculation, trend analysis,
and performance metrics.

Author: AI Engineering Team
Created: 2026-04-17
"""

import pytest
import time
from datetime import datetime, timezone, timedelta
from src.content_engine.utils.fallback_metrics import (
    FallbackEvent,
    FallbackMetrics,
    fallback_metrics,
)


class TestFallbackEvent:
    """Test FallbackEvent dataclass."""

    def test_fallback_event_creation(self):
        """Test creating a fallback event."""
        event = FallbackEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            primary_model="claude-sonnet-4-20250514",
            fallback_model="gpt-4o",
            reason="timeout",
            task_type="scoring",
            latency_ms_primary=30000,
            latency_ms_fallback=5000,
            success=True,
        )

        assert event.primary_model == "claude-sonnet-4-20250514"
        assert event.fallback_model == "gpt-4o"
        assert event.reason == "timeout"
        assert event.success is True


class TestFallbackMetrics:
    """Test FallbackMetrics implementation."""

    def test_metrics_initialization(self):
        """Test metrics initialization."""
        metrics = FallbackMetrics()
        assert len(metrics.events) == 0
        assert len(metrics._by_model) == 0
        assert len(metrics._by_reason) == 0

    def test_record_fallback(self):
        """Test recording a fallback event."""
        metrics = FallbackMetrics()
        metrics.record_fallback(
            primary_model="claude-sonnet",
            fallback_model="gpt-4o",
            reason="timeout",
            task_type="scoring",
            latency_ms_primary=30000,
            latency_ms_fallback=5000,
            success=True,
        )

        assert len(metrics.events) == 1
        assert "claude-sonnet" in metrics._by_model
        assert metrics._by_model["claude-sonnet"]["count"] == 1
        assert metrics._by_model["claude-sonnet"]["success"] == 1
        assert metrics._by_reason["timeout"] == 1

    def test_record_multiple_fallbacks(self):
        """Test recording multiple fallback events."""
        metrics = FallbackMetrics()

        for i in range(5):
            metrics.record_fallback(
                primary_model="claude-sonnet",
                fallback_model="gpt-4o",
                reason="error",
                task_type="writing",
                latency_ms_primary=30000,
                latency_ms_fallback=5000,
                success=True,
            )

        assert len(metrics.events) == 5
        assert metrics._by_model["claude-sonnet"]["count"] == 5
        assert metrics._by_reason["error"] == 5
        assert metrics._by_task["writing"] == 5

    def test_record_failed_fallback(self):
        """Test recording a failed fallback."""
        metrics = FallbackMetrics()
        metrics.record_fallback(
            primary_model="claude-sonnet",
            fallback_model="unknown",
            reason="timeout",
            task_type="scoring",
            latency_ms_primary=30000,
            latency_ms_fallback=0,
            success=False,
        )

        assert metrics._by_model["claude-sonnet"]["count"] == 1
        assert metrics._by_model["claude-sonnet"]["success"] == 0

    def test_get_fallback_rate(self):
        """Test getting fallback rate."""
        metrics = FallbackMetrics()

        # Record some fallbacks
        for i in range(10):
            metrics.record_fallback(
                primary_model="claude-sonnet",
                fallback_model="gpt-4o",
                reason="timeout",
                task_type="scoring",
                latency_ms_primary=30000,
                latency_ms_fallback=5000,
                success=True,
            )

        rate = metrics.get_fallback_rate(hours=24)

        assert rate["total_fallbacks"] == 10
        assert rate["total_requests"] == 10
        assert rate["overall_fallback_rate"] == 1.0
        assert "by_model" in rate
        assert "by_reason" in rate

    def test_get_fallback_rate_by_model(self):
        """Test fallback rate breakdown by model."""
        metrics = FallbackMetrics()

        # Record fallbacks for different models
        for _ in range(5):
            metrics.record_fallback(
                primary_model="claude-sonnet",
                fallback_model="gpt-4o",
                reason="timeout",
                task_type="scoring",
                latency_ms_primary=30000,
                latency_ms_fallback=5000,
                success=True,
            )

        for _ in range(3):
            metrics.record_fallback(
                primary_model="gpt-4",
                fallback_model="claude-opus",
                reason="error",
                task_type="writing",
                latency_ms_primary=20000,
                latency_ms_fallback=4000,
                success=True,
            )

        rate = metrics.get_fallback_rate(hours=24)

        assert rate["by_model"]["claude-sonnet"]["count"] == 5
        assert rate["by_model"]["gpt-4"]["count"] == 3
        # Fallback rate is calculated as model_count / total_requests
        # Total requests = 5 + 3 = 8
        assert rate["by_model"]["claude-sonnet"]["fallback_rate"] == 5/8
        assert rate["by_model"]["gpt-4"]["fallback_rate"] == 3/8

    def test_get_problematic_models(self):
        """Test identifying problematic models."""
        metrics = FallbackMetrics()

        # Model with high fallback rate
        for _ in range(15):
            metrics.record_fallback(
                primary_model="problematic_model",
                fallback_model="stable_model",
                reason="timeout",
                task_type="scoring",
                latency_ms_primary=30000,
                latency_ms_fallback=5000,
                success=True,
            )

        # Model with very low fallback rate (below 10% threshold)
        for _ in range(1):
            metrics.record_fallback(
                primary_model="stable_model",
                fallback_model="backup",
                reason="error",
                task_type="writing",
                latency_ms_primary=5000,
                latency_ms_fallback=3000,
                success=True,
            )

        # Get problematic models with 10% threshold
        problematic = metrics.get_problematic_models(threshold=0.10)

        assert "problematic_model" in problematic
        # stable_model has 1 fallback out of 16 total = 6.25% < 10% threshold
        assert "stable_model" not in problematic
        # Should be sorted by rate (highest first)
        assert problematic[0] == "problematic_model"

    def test_get_latency_comparison(self):
        """Test latency comparison between primary and fallback."""
        metrics = FallbackMetrics()

        metrics.record_fallback(
            primary_model="claude-sonnet",
            fallback_model="gpt-4o",
            reason="timeout",
            task_type="scoring",
            latency_ms_primary=30000,
            latency_ms_fallback=5000,
            success=True,
        )

        metrics.record_fallback(
            primary_model="claude-sonnet",
            fallback_model="gpt-4o",
            reason="timeout",
            task_type="scoring",
            latency_ms_primary=40000,
            latency_ms_fallback=6000,
            success=True,
        )

        comparison = metrics.get_latency_comparison(hours=24)

        assert comparison["total_fallbacks"] == 2
        assert comparison["avg_primary_latency_ms"] == 35000
        assert comparison["avg_fallback_latency_ms"] == 5500
        # Fallback is much faster
        assert comparison["latency_improvement_pct"] > 80

    def test_get_latency_comparison_no_fallback_latency(self):
        """Test latency comparison when fallback latency is unknown."""
        metrics = FallbackMetrics()

        metrics.record_fallback(
            primary_model="claude-sonnet",
            fallback_model="unknown",
            reason="timeout",
            task_type="scoring",
            latency_ms_primary=30000,
            latency_ms_fallback=0,
            success=False,
        )

        comparison = metrics.get_latency_comparison(hours=24)

        assert comparison["avg_primary_latency_ms"] == 30000
        # When fallback latency is 0, there's no valid comparison
        # The calculation gives 100% improvement (from 30000 to 0)
        # But in practice this means fallback failed, so we handle it differently
        assert comparison["avg_fallback_latency_ms"] == 0
        # With no valid fallback latency data, improvement is not meaningful
        # The system records 0, which could indicate complete failure or unknown

    def test_get_fallback_trends(self):
        """Test fallback trends over time."""
        metrics = FallbackMetrics()

        # Record events at different times
        now = datetime.now(timezone.utc)

        for i in range(10):
            # Simulate events in the past
            past_time = now - timedelta(hours=i)
            event = FallbackEvent(
                timestamp=past_time.isoformat(),
                primary_model="claude-sonnet",
                fallback_model="gpt-4o",
                reason="timeout",
                task_type="scoring",
                latency_ms_primary=30000,
                latency_ms_fallback=5000,
                success=True if i % 2 == 0 else False,
            )
            metrics.events.append(event)

        trends = metrics.get_fallback_trends(hours=10, bucket_minutes=60)

        assert "trends" in trends
        assert trends["bucket_minutes"] == 60
        assert len(trends["trends"]) > 0

    def test_get_recent_events(self):
        """Test getting recent fallback events."""
        metrics = FallbackMetrics()

        # Record multiple events
        for i in range(15):
            metrics.record_fallback(
                primary_model=f"model_{i % 3}",
                fallback_model="fallback",
                reason="test",
                task_type="test",
                latency_ms_primary=1000,
                latency_ms_fallback=500,
                success=True,
            )

        recent = metrics.get_recent_events(limit=5)

        assert len(recent) == 5
        # Should be in reverse chronological order (newest first)
        assert recent[0]["primary_model"] == "model_2"

    def test_get_summary(self):
        """Test getting comprehensive summary."""
        metrics = FallbackMetrics()

        # Record diverse fallbacks
        for _ in range(10):
            metrics.record_fallback(
                primary_model="claude-sonnet",
                fallback_model="gpt-4o",
                reason="timeout",
                task_type="scoring",
                latency_ms_primary=30000,
                latency_ms_fallback=5000,
                success=True,
            )

        for _ in range(5):
            metrics.record_fallback(
                primary_model="gpt-4",
                fallback_model="claude-opus",
                reason="error",
                task_type="writing",
                latency_ms_primary=20000,
                latency_ms_fallback=4000,
                success=True,
            )

        summary = metrics.get_summary(hours=24)

        assert "overall_fallback_rate" in summary
        assert "total_fallbacks" in summary
        assert "problematic_models" in summary
        assert "avg_primary_latency_ms" in summary
        assert "top_reasons" in summary
        assert "recent_events" in summary

        assert summary["total_fallbacks"] == 15
        assert len(summary["top_reasons"]) <= 5

    def test_empty_metrics(self):
        """Test metrics with no events."""
        metrics = FallbackMetrics()

        rate = metrics.get_fallback_rate(hours=24)
        assert rate["total_fallbacks"] == 0
        assert rate["overall_fallback_rate"] == 0.0

        problematic = metrics.get_problematic_models()
        assert len(problematic) == 0

        comparison = metrics.get_latency_comparison(hours=24)
        assert comparison["total_fallbacks"] == 0

        summary = metrics.get_summary(hours=24)
        assert summary["total_fallbacks"] == 0


class TestGlobalFallbackMetrics:
    """Test global fallback metrics instance."""

    def test_global_metrics_accessible(self):
        """Test that global metrics instance is accessible."""
        from src.content_engine.utils.fallback_metrics import fallback_metrics

        assert fallback_metrics is not None
        assert isinstance(fallback_metrics, FallbackMetrics)

    def test_global_metrics_persistence(self):
        """Test that global metrics maintains state."""
        from src.content_engine.utils.fallback_metrics import fallback_metrics

        initial_count = len(fallback_metrics.events)

        # Record a fallback
        fallback_metrics.record_fallback(
            primary_model="test_model",
            fallback_model="fallback",
            reason="test",
            task_type="test",
            latency_ms_primary=1000,
            latency_ms_fallback=500,
            success=True,
        )

        # Check that state changed
        assert len(fallback_metrics.events) == initial_count + 1


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_reason_truncation(self):
        """Test that long reasons are truncated."""
        metrics = FallbackMetrics()

        long_reason = "a" * 200  # 200 characters

        metrics.record_fallback(
            primary_model="model",
            fallback_model="fallback",
            reason=long_reason,
            task_type="test",
            latency_ms_primary=1000,
            latency_ms_fallback=500,
            success=True,
        )

        # Reason should be truncated to 100 characters
        assert metrics.events[0].reason == long_reason[:100]
        assert len(metrics.events[0].reason) == 100

    def test_zero_total_requests(self):
        """Test fallback rate calculation with zero total requests."""
        metrics = FallbackMetrics()

        rate = metrics.get_fallback_rate(hours=24)

        # Should handle zero requests gracefully
        assert rate["overall_fallback_rate"] == 0.0

    def test_different_task_types(self):
        """Test tracking different task types."""
        metrics = FallbackMetrics()

        task_types = ["scoring", "writing", "editing", "research", "fact-check"]

        for task_type in task_types:
            metrics.record_fallback(
                primary_model="model",
                fallback_model="fallback",
                reason="test",
                task_type=task_type,
                latency_ms_primary=1000,
                latency_ms_fallback=500,
                success=True,
            )

        summary = metrics.get_summary(hours=24)

        # All task types should be tracked
        assert len(summary["top_tasks"]) <= 5
        for task_type in task_types:
            assert task_type in metrics._by_task


# Run tests with: pytest tests/test_fallback_metrics.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
