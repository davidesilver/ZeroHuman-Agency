"""Fallback Monitor - tracks daily LLM fallback frequency and sends alerts.

This module provides:
1. In-memory daily counter for fallback attempts
2. Automatic reset at midnight (configurable timezone)
3. Alert when fallbacks exceed threshold percentage
4. Integration with existing logging and alerting systems
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from threading import Lock

from ..config import settings

logger = logging.getLogger("content_engine.fallback_monitor")


class FallbackMonitor:
    """Monitors LLM fallback attempts and sends alerts when thresholds are exceeded.

    Thread-safe singleton that tracks:
    - Daily fallback count
    - Daily total LLM calls
    - Emergency fallback count
    """

    _instance: FallbackMonitor | None = None
    _lock: Lock = Lock()

    def __new__(cls) -> FallbackMonitor:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._fallback_count: int = 0
        self._total_calls: int = 0
        self._emergency_count: int = 0
        self._last_reset_date: str = self._get_current_date()
        self._lock = Lock()

        logger.info(
            "FallbackMonitor initialized - threshold=%.1f%%, reset_hour=%d UTC",
            settings.fallback_alert_threshold,
            settings.fallback_daily_reset_hour
        )

    def _get_current_date(self) -> str:
        """Get current date string in UTC."""
        return datetime.now(UTC).strftime("%Y-%m-%d")

    def _check_and_reset_daily(self) -> None:
        """Reset counters if it's a new day."""
        current_date = self._get_current_date()
        if current_date != self._last_reset_date:
            with self._lock:
                # Double-check after acquiring lock
                if current_date != self._last_reset_date:
                    logger.info(
                        "Daily fallback reset - previous day: %s, fallbacks: %d/%d (%.1f%%), emergencies: %d",
                        self._last_reset_date,
                        self._fallback_count,
                        self._total_calls,
                        self._get_fallback_percentage(),
                        self._emergency_count
                    )

                    self._fallback_count = 0
                    self._total_calls = 0
                    self._emergency_count = 0
                    self._last_reset_date = current_date

    def record_fallback(self, is_emergency: bool = False) -> None:
        """Record a fallback attempt.

        Args:
            is_emergency: Whether this was an emergency fallback (Anthropic API down)
        """
        self._check_and_reset_daily()

        with self._lock:
            self._fallback_count += 1
            if is_emergency:
                self._emergency_count += 1

        logger.debug(
            "Fallback recorded - total: %d, emergencies: %d",
            self._fallback_count,
            self._emergency_count
        )

        # Check if we should send an alert
        if self._should_alert():
            self._send_alert()

    def record_call(self) -> None:
        """Record a successful LLM call (for calculating fallback percentage)."""
        self._check_and_reset_daily()

        with self._lock:
            self._total_calls += 1

    def _get_fallback_percentage(self) -> float:
        """Calculate fallback percentage of total calls."""
        if self._total_calls == 0:
            return 0.0
        return 100.0 * self._fallback_count / self._total_calls

    def _should_alert(self) -> bool:
        """Check if fallback percentage exceeds alert threshold."""
        if self._total_calls < 10:  # Don't alert on very low call volumes
            return False

        fallback_percentage = self._get_fallback_percentage()
        return fallback_percentage >= settings.fallback_alert_threshold

    def _send_alert(self) -> None:
        """Send alert about high fallback rate."""
        try:
            from ..services.notification import emit_event

            fallback_percentage = self._get_fallback_percentage()

            import asyncio

            async def send_async():
                try:
                    await emit_event(
                        event_type="high_fallback_rate",
                        title=f"High Fallback Rate: {fallback_percentage:.1f}%",
                        severity="warning",
                        detail={
                            "fallback_rate_pct": round(fallback_percentage, 1),
                            "threshold_pct": settings.fallback_alert_threshold,
                            "total_calls": self._total_calls,
                            "fallbacks": self._fallback_count,
                            "emergencies": self._emergency_count,
                        },
                    )
                except Exception as e:
                    logger.error("Failed to send fallback alert: %s", e)

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(send_async())
                else:
                    loop.run_until_complete(send_async())
            except RuntimeError:
                asyncio.run(send_async())

            logger.warning(
                "Fallback alert sent - rate: %.1f%%, total_calls: %d, fallbacks: %d",
                fallback_percentage,
                self._total_calls,
                self._fallback_count,
            )
        except Exception as e:
            logger.error("Failed to send fallback alert: %s", e)

    def get_stats(self) -> dict:
        """Get current monitoring statistics.

        Returns:
            Dict with current stats
        """
        self._check_and_reset_daily()

        with self._lock:
            return {
                "date": self._last_reset_date,
                "total_calls": self._total_calls,
                "fallback_count": self._fallback_count,
                "emergency_count": self._emergency_count,
                "fallback_percentage": self._get_fallback_percentage(),
                "threshold": settings.fallback_alert_threshold,
            }

    def reset(self) -> None:
        """Manually reset all counters (useful for testing)."""
        with self._lock:
            self._fallback_count = 0
            self._total_calls = 0
            self._emergency_count = 0
            self._last_reset_date = self._get_current_date()

        logger.info("FallbackMonitor manually reset")


# Singleton instance
_monitor_instance: FallbackMonitor | None = None


def get_fallback_monitor() -> FallbackMonitor:
    """Get the singleton FallbackMonitor instance."""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = FallbackMonitor()
    return _monitor_instance


def record_fallback(is_emergency: bool = False) -> None:
    """Convenience function to record a fallback."""
    get_fallback_monitor().record_fallback(is_emergency)


def record_call() -> None:
    """Convenience function to record a successful LLM call."""
    get_fallback_monitor().record_call()


def get_fallback_stats() -> dict:
    """Convenience function to get fallback statistics."""
    return get_fallback_monitor().get_stats()
