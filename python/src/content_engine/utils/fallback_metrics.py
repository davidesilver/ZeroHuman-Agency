"""
Fallback Metrics and Monitoring System

Tracks and analyzes fallback patterns to monitor system health and
understand when and how often we're falling back to alternative models
or degraded service levels.

Critical for production observability: provides visibility into system
quality and helps identify problematic models or services.

Author: AI Engineering Team
Created: 2026-04-16
"""

import json
import logging
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

logger = logging.getLogger(__name__)


@dataclass
class FallbackEvent:
    """Record a single fallback event.

    Attributes:
        timestamp: When the fallback occurred (ISO format)
        primary_model: The model that failed
        fallback_model: The model we fell back to
        reason: Why the fallback occurred
        task_type: Type of task being performed
        latency_ms_primary: Latency of primary model before failure
        latency_ms_fallback: Latency of fallback model
        success: Whether the fallback attempt succeeded
    """

    timestamp: str
    primary_model: str
    fallback_model: str
    reason: str
    task_type: str
    latency_ms_primary: int
    latency_ms_fallback: int
    success: bool


class FallbackMetrics:
    """
    Track and analyze fallback patterns.

    Provides comprehensive metrics on fallback behavior, helping
    identify problematic models and optimize system performance.

    Example:
        >>> metrics = FallbackMetrics()
        >>> metrics.record_fallback(
        ...     primary_model="claude-sonnet-4-20250514",
        ...     fallback_model="gpt-4o",
        ...     reason="timeout",
        ...     task_type="scoring",
        ...     latency_ms_primary=30000,
        ...     latency_ms_fallback=5000,
        ...     success=True
        ... )
        >>> rate = metrics.get_fallback_rate(hours=1)
    """

    def __init__(self, storage_path: str = "fallback_metrics.json"):
        self.storage_path = storage_path
        self.events: list[FallbackEvent] = []
        self._by_model: dict[str, dict[str, int]] = defaultdict(
            lambda: {"count": 0, "success": 0}
        )
        self._by_reason: dict[str, int] = defaultdict(int)
        self._by_task: dict[str, int] = defaultdict(int)

    def record_fallback(
        self,
        primary_model: str,
        fallback_model: str,
        reason: str,
        task_type: str,
        latency_ms_primary: int,
        latency_ms_fallback: int,
        success: bool,
    ):
        """
        Record a fallback event.

        Args:
            primary_model: The model that failed
            fallback_model: The model we fell back to (or "unknown" if unknown)
            reason: Why the fallback occurred (e.g., "timeout", "error", "rate_limited")
            task_type: Type of task being performed
            latency_ms_primary: Latency of primary model before failure
            latency_ms_fallback: Latency of fallback model (0 if unknown)
            success: Whether the fallback attempt succeeded
        """
        event = FallbackEvent(
            timestamp=datetime.now(UTC).isoformat(),
            primary_model=primary_model,
            fallback_model=fallback_model,
            reason=reason[:100],  # Limit reason length
            task_type=task_type,
            latency_ms_primary=latency_ms_primary,
            latency_ms_fallback=latency_ms_fallback,
            success=success,
        )

        self.events.append(event)
        self._by_model[primary_model]["count"] += 1
        if success:
            self._by_model[primary_model]["success"] += 1
        self._by_reason[reason] += 1
        self._by_task[task_type] += 1

        logger.info(
            f"Fallback recorded: {primary_model} -> {fallback_model} "
            f"(reason: {reason}, success: {success}, task: {task_type})"
        )

        # Save periodically (every 10 events)
        if len(self.events) % 10 == 0:
            self._save_events()

    def get_fallback_rate(self, hours: int = 24) -> dict[str, any]:
        """
        Get fallback rates for the last N hours.

        Args:
            hours: Number of hours to look back

        Returns:
            Dictionary with comprehensive fallback metrics
        """
        cutoff_time = datetime.now(UTC).timestamp() - (hours * 3600)

        recent_events = [
            e for e in self.events
            if datetime.fromisoformat(e.timestamp).timestamp() > cutoff_time
        ]

        total_fallbacks = len(recent_events)

        # Calculate total requests (this is an estimate - in production
        # you'd track total requests separately)
        total_requests = sum(stats["count"] for stats in self._by_model.values())

        # Build breakdown by model
        fallback_by_model = {}
        for model, stats in self._by_model.items():
            if stats["count"] > 0:
                fallback_by_model[model] = {
                    "count": stats["count"],
                    "success_count": stats["success"],
                    "success_rate": stats["success"] / stats["count"],
                    "fallback_rate": stats["count"] / total_requests if total_requests > 0 else 0.0,
                }

        return {
            "total_fallbacks": total_fallbacks,
            "total_requests": total_requests,
            "overall_fallback_rate": total_fallbacks / total_requests if total_requests > 0 else 0.0,
            "by_model": fallback_by_model,
            "by_reason": dict(self._by_reason),
            "by_task": dict(self._by_task),
            "time_period_hours": hours,
        }

    def get_problematic_models(self, threshold: float = 0.10) -> list[str]:
        """
        Get models with fallback rates above threshold.

        Args:
            threshold: Fallback rate threshold (0.0 to 1.0)

        Returns:
            List of model names sorted by fallback rate (highest first)
        """
        metrics = self.get_fallback_rate()

        problematic = []

        for model, stats in metrics["by_model"].items():
            if stats["fallback_rate"] > threshold:
                problematic.append((model, stats["fallback_rate"]))

        # Sort by fallback rate (highest first)
        problematic.sort(key=lambda x: x[1], reverse=True)

        return [model for model, _ in problematic]

    def get_latency_comparison(self, hours: int = 24) -> dict[str, any]:
        """
        Get latency comparison between primary and fallback models.

        Args:
            hours: Number of hours to look back

        Returns:
            Dictionary with latency statistics
        """
        cutoff_time = datetime.now(UTC).timestamp() - (hours * 3600)

        recent_events = [
            e for e in self.events
            if datetime.fromisoformat(e.timestamp).timestamp() > cutoff_time
        ]

        if not recent_events:
            return {
                "time_period_hours": hours,
                "total_fallbacks": 0,
                "avg_primary_latency_ms": 0,
                "avg_fallback_latency_ms": 0,
                "latency_improvement_pct": 0,
            }

        primary_latencies = [e.latency_ms_primary for e in recent_events]
        fallback_latencies = [e.latency_ms_fallback for e in recent_events if e.latency_ms_fallback > 0]

        avg_primary = sum(primary_latencies) / len(primary_latencies)
        avg_fallback = (
            sum(fallback_latencies) / len(fallback_latencies)
            if fallback_latencies
            else 0
        )

        latency_improvement = (
            ((avg_primary - avg_fallback) / avg_primary * 100)
            if avg_primary > 0
            else 0
        )

        return {
            "time_period_hours": hours,
            "total_fallbacks": len(recent_events),
            "avg_primary_latency_ms": avg_primary,
            "avg_fallback_latency_ms": avg_fallback,
            "latency_improvement_pct": latency_improvement,
            "primary_latencies": primary_latencies,
            "fallback_latencies": fallback_latencies,
        }

    def get_fallback_trends(self, hours: int = 24, bucket_minutes: int = 60) -> dict[str, any]:
        """
        Get fallback trends over time.

        Args:
            hours: Total time period to analyze
            bucket_minutes: Size of each time bucket in minutes

        Returns:
            Dictionary with trend data broken into time buckets
        """
        cutoff_time = datetime.now(UTC).timestamp() - (hours * 3600)
        bucket_seconds = bucket_minutes * 60

        recent_events = [
            e for e in self.events
            if datetime.fromisoformat(e.timestamp).timestamp() > cutoff_time
        ]

        # Create time buckets
        num_buckets = (hours * 3600) // bucket_seconds
        buckets = {i: {"count": 0, "success": 0} for i in range(int(num_buckets))}

        for event in recent_events:
            event_time = datetime.fromisoformat(event.timestamp).timestamp()
            bucket_index = int((event_time - cutoff_time) // bucket_seconds)

            if bucket_index in buckets:
                buckets[bucket_index]["count"] += 1
                if event.success:
                    buckets[bucket_index]["success"] += 1

        # Convert to list format
        trend_data = []
        for bucket_idx, data in buckets.items():
            trend_data.append({
                "bucket": bucket_idx,
                "time_start": cutoff_time + (bucket_idx * bucket_seconds),
                "time_end": cutoff_time + ((bucket_idx + 1) * bucket_seconds),
                "fallback_count": data["count"],
                "success_count": data["success"],
                "success_rate": data["success"] / data["count"] if data["count"] > 0 else 0.0,
            })

        return {
            "time_period_hours": hours,
            "bucket_minutes": bucket_minutes,
            "trends": trend_data,
        }

    def get_recent_events(self, limit: int = 10) -> list[dict[str, any]]:
        """
        Get most recent fallback events.

        Args:
            limit: Maximum number of events to return

        Returns:
            List of recent fallback events
        """
        recent = self.events[-limit:] if len(self.events) >= limit else self.events
        return [asdict(event) for event in reversed(recent)]

    def get_summary(self, hours: int = 24) -> dict[str, any]:
        """
        Get comprehensive summary of fallback metrics.

        Args:
            hours: Time period to analyze

        Returns:
            Dictionary with all key metrics
        """
        fallback_rate = self.get_fallback_rate(hours)
        problematic_models = self.get_problematic_models()
        latency_comparison = self.get_latency_comparison(hours)
        recent_events = self.get_recent_events(5)

        return {
            "summary_period_hours": hours,
            "overall_fallback_rate": fallback_rate["overall_fallback_rate"],
            "total_fallbacks": fallback_rate["total_fallbacks"],
            "problematic_models": problematic_models,
            "avg_primary_latency_ms": latency_comparison["avg_primary_latency_ms"],
            "avg_fallback_latency_ms": latency_comparison["avg_fallback_latency_ms"],
            "latency_improvement_pct": latency_comparison["latency_improvement_pct"],
            "top_reasons": sorted(
                fallback_rate["by_reason"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5],
            "top_tasks": sorted(
                fallback_rate["by_task"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5],
            "recent_events": recent_events,
        }

    def _save_events(self):
        """Save events to file."""
        try:
            # Keep only last 500 events to manage file size
            data = [asdict(e) for e in self.events[-500:]]

            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save fallback metrics: {e}")

    def _load_events(self):
        """Load events from file."""
        try:
            with open(self.storage_path) as f:
                data = json.load(f)
                self.events = [FallbackEvent(**item) for item in data]

            # Rebuild internal statistics
            self._by_model.clear()
            self._by_reason.clear()
            self._by_task.clear()

            for event in self.events:
                self._by_model[event.primary_model]["count"] += 1
                if event.success:
                    self._by_model[event.primary_model]["success"] += 1
                self._by_reason[event.reason] += 1
                self._by_task[event.task_type] += 1

            logger.info(f"Loaded {len(self.events)} historical fallback events")

        except FileNotFoundError:
            logger.info("No existing fallback metrics file found, starting fresh")
        except Exception as e:
            logger.error(f"Failed to load fallback metrics: {e}, starting fresh")
            self.events = []


# Global fallback metrics instance
fallback_metrics = FallbackMetrics()

logger.info("Fallback metrics system initialized")


# Export key components
__all__ = [
    'FallbackEvent',
    'FallbackMetrics',
    'fallback_metrics',
]
