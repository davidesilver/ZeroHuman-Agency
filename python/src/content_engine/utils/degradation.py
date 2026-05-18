"""
Graceful Degradation System

Implements graceful degradation patterns to handle service failures and prevent
complete system outages when LLM APIs fail. Uses circuit breaker pattern for
automatic failure detection and recovery.

Critical for production reliability: ensures system continues to operate
at reduced capacity rather than failing completely.

Author: AI Engineering Team
Created: 2026-04-16
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class DegradationLevel(Enum):
    """System degradation levels."""

    NORMAL = "normal"           # All services operational
    DEGRADED = "degraded"       # Some services degraded, reduced functionality
    MINIMAL = "minimal"         # Minimal functionality available
    UNAVAILABLE = "unavailable" # Service unavailable


@dataclass
class DegradationResponse:
    """Response when system is in degraded state.

    Attributes:
        level: Current degradation level
        message: Human-readable message explaining the situation
        data: Optional additional data about the degradation
        can_retry: Whether the operation can be retried
        retry_after_seconds: Suggested wait time before retry (if can_retry=True)
    """

    level: DegradationLevel
    message: str
    data: dict[str, Any] | None = None
    can_retry: bool = True
    retry_after_seconds: int = 60


class CircuitBreaker:
    """
    Circuit breaker pattern for failing services.

    Prevents cascading failures by stopping calls to failing services
    and allowing them time to recover. Automatically opens after
    consecutive failures and closes after a timeout period.

    Example:
        >>> breaker = CircuitBreaker(failure_threshold=5, timeout_seconds=60)
        >>> if breaker.can_attempt():
        ...     try:
        ...         result = make_service_call()
        ...         breaker.record_success()
        ...     except Exception as e:
        ...         breaker.record_failure()
    """

    def __init__(self, failure_threshold: int = 5, timeout_seconds: int = 60):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of consecutive failures before opening
            timeout_seconds: Seconds to wait before attempting recovery
        """
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.failure_count = 0
        self.last_failure_time: float | None = None
        self.is_open = False
        self._lock = asyncio.Lock()

    async def record_failure(self):
        """
        Record a service failure.

        Opens the circuit breaker if failure threshold is reached.
        """
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.is_open = True
                logger.warning(
                    f"Circuit breaker OPENED after {self.failure_count} failures. "
                    f"Will attempt recovery after {self.timeout_seconds}s"
                )

    async def record_success(self):
        """
        Record a service success.

        Closes the circuit breaker if it was open.
        """
        async with self._lock:
            self.failure_count = 0
            self.is_open = False
            logger.debug("Circuit breaker CLOSED - service recovered")

    async def can_attempt(self) -> bool:
        """
        Check if we can attempt the operation.

        Returns:
            True if operation can be attempted, False if circuit is open
        """
        async with self._lock:
            if not self.is_open:
                return True

            # Check if timeout has passed for recovery attempt
            if self.last_failure_time and (time.time() - self.last_failure_time) > self.timeout_seconds:
                self.is_open = False
                self.failure_count = 0
                logger.info("Circuit breaker CLOSED after timeout - attempting recovery")
                return True

            return False

    def get_state(self) -> dict[str, Any]:
        """
        Get current circuit breaker state.

        Returns:
            Dictionary with current state information
        """
        return {
            "is_open": self.is_open,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "last_failure_time": self.last_failure_time,
            "timeout_seconds": self.timeout_seconds,
            "time_until_recovery": (
                max(0, self.timeout_seconds - (time.time() - (self.last_failure_time or 0)))
                if self.is_open and self.last_failure_time
                else 0
            ),
        }


class GracefulDegradationManager:
    """
    Manage graceful degradation when services fail.

    Automatically detects service failures and adjusts system degradation
    level accordingly. Provides appropriate responses based on current level.

    Example:
        >>> manager = GracefulDegradationManager()
        >>> try:
        ...     result = call_service()
        ...     manager.record_success("service_name")
        ... except Exception as e:
        ...     manager.record_failure("service_name", e)
        ...     response = manager.get_degraded_response("task_type")
    """

    def __init__(self):
        self.failure_counts: dict[str, int] = {}
        self.circuit_breakers: dict[str, CircuitBreaker] = {}
        self.current_level = DegradationLevel.NORMAL
        self._lock = asyncio.Lock()

    async def record_failure(self, service: str, error: Exception):
        """
        Record a service failure and potentially degrade service level.

        Args:
            service: Service identifier (e.g., "anthropic", "openrouter")
            error: The exception that occurred
        """
        self.failure_counts[service] = self.failure_counts.get(service, 0) + 1

        logger.warning(
            f"Service failure recorded: {service} (count: {self.failure_counts[service]}) - {str(error)}"
        )

        # Get or create circuit breaker for this service
        if service not in self.circuit_breakers:
            self.circuit_breakers[service] = CircuitBreaker(
                failure_threshold=5, timeout_seconds=60
            )

        await self.circuit_breakers[service].record_failure()

        # Check if we need to degrade system level
        await self._evaluate_degradation_level()

    async def record_success(self, service: str):
        """
        Record a service success and potentially recover from degradation.

        Args:
            service: Service identifier
        """
        self.failure_counts[service] = 0

        if service in self.circuit_breakers:
            await self.circuit_breakers[service].record_success()

        # Check if we can recover from degraded state
        await self._attempt_recovery(service)

    async def can_attempt_service(self, service: str) -> bool:
        """
        Check if we can attempt a service call.

        Args:
            service: Service identifier

        Returns:
            True if service can be attempted, False if circuit is open
        """
        if service not in self.circuit_breakers:
            return True

        return await self.circuit_breakers[service].can_attempt()

    def get_degraded_response(
        self,
        task_type: str = "unknown",
        context: str = "unknown"
    ) -> DegradationResponse:
        """
        Get a response appropriate for current degradation level.

        Args:
            task_type: Type of task being attempted
            context: Additional context for logging

        Returns:
            DegradationResponse with appropriate message and data
        """
        if self.current_level == DegradationLevel.NORMAL:
            return DegradationResponse(
                level=DegradationLevel.NORMAL,
                message="System operating normally",
                can_retry=False,
            )

        elif self.current_level == DegradationLevel.DEGRADED:
            return DegradationResponse(
                level=DegradationLevel.DEGRADED,
                message="Some AI services are temporarily unavailable. Using reduced functionality.",
                data={
                    "fallback_used": True,
                    "quality": "reduced",
                    "task_type": task_type,
                },
                can_retry=True,
                retry_after_seconds=30,
            )

        elif self.current_level == DegradationLevel.MINIMAL:
            return DegradationResponse(
                level=DegradationLevel.MINIMAL,
                message="AI services are currently unavailable. Please try again later.",
                data={
                    "fallback_used": True,
                    "quality": "minimal",
                    "task_type": task_type,
                },
                can_retry=True,
                retry_after_seconds=120,
            )

        else:  # UNAVAILABLE
            return DegradationResponse(
                level=DegradationLevel.UNAVAILABLE,
                message="Service temporarily unavailable. We're working to restore full functionality.",
                can_retry=True,
                retry_after_seconds=300,
            )

    async def _evaluate_degradation_level(self):
        """
        Evaluate current state and adjust degradation level.

        Called after recording a failure to determine if we need to
        degrade the system level.
        """
        total_failures = sum(self.failure_counts.values())
        open_circuits = sum(
            1 for cb in self.circuit_breakers.values() if cb.is_open
        )

        async with self._lock:
            previous_level = self.current_level

            # Determine new degradation level
            if open_circuits == 0:
                self.current_level = DegradationLevel.NORMAL
            elif open_circuits == 1:
                self.current_level = DegradationLevel.DEGRADED
            elif open_circuits == 2:
                self.current_level = DegradationLevel.MINIMAL
            else:
                self.current_level = DegradationLevel.UNAVAILABLE

            # Log level changes
            if self.current_level != previous_level:
                logger.warning(
                    f"Degradation level changed: {previous_level.value} -> {self.current_level.value} "
                    f"(failures: {total_failures}, open circuits: {open_circuits})"
                )

    async def _attempt_recovery(self, service: str):
        """
        Attempt to recover from degraded state.

        Called after recording a success to see if we can improve
        the degradation level.
        """
        open_circuits = sum(
            1 for cb in self.circuit_breakers.values() if cb.is_open
        )

        async with self._lock:
            # Determine if we can recover
            if self.current_level == DegradationLevel.MINIMAL and open_circuits <= 1:
                self.current_level = DegradationLevel.DEGRADED
                logger.info(f"System recovered to DEGRADED level (service: {service})")

            elif self.current_level == DegradationLevel.DEGRADED and open_circuits == 0:
                self.current_level = DegradationLevel.NORMAL
                logger.info(f"System recovered to NORMAL level (service: {service})")

    async def get_current_level(self) -> DegradationLevel:
        """Return the current degradation level."""
        return self.current_level

    def get_system_status(self) -> dict[str, Any]:
        """
        Get current system status.

        Returns:
            Dictionary with comprehensive status information
        """
        circuit_states = {
            service: cb.get_state()
            for service, cb in self.circuit_breakers.items()
        }

        return {
            "current_level": self.current_level.value,
            "failure_counts": self.failure_counts.copy(),
            "circuit_breakers": circuit_states,
            "total_services": len(self.circuit_breakers),
            "open_circuits": sum(
                1 for cb in self.circuit_breakers.values() if cb.is_open
            ),
        }


# Global degradation manager instance
degradation_manager = GracefulDegradationManager()

logger.info("Graceful degradation system initialized")


# Export key components
__all__ = [
    'DegradationLevel',
    'DegradationResponse',
    'CircuitBreaker',
    'GracefulDegradationManager',
    'degradation_manager',
]
