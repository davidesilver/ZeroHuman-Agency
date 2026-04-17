"""
Comprehensive Test Suite for Graceful Degradation System

Tests cover circuit breaker pattern, degradation level management,
and graceful service failure handling.

Author: AI Engineering Team
Created: 2026-04-17
"""

import pytest
import asyncio
from src.content_engine.utils.degradation import (
    DegradationLevel,
    DegradationResponse,
    CircuitBreaker,
    GracefulDegradationManager,
    degradation_manager,
)


class TestCircuitBreaker:
    """Test CircuitBreaker implementation."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_initially_closed(self):
        """Test that circuit breaker starts closed."""
        breaker = CircuitBreaker(failure_threshold=3, timeout_seconds=60)
        assert not breaker.is_open
        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_threshold(self):
        """Test that circuit breaker opens after failure threshold."""
        breaker = CircuitBreaker(failure_threshold=3, timeout_seconds=60)

        await breaker.record_failure()
        await breaker.record_failure()
        assert not breaker.is_open

        await breaker.record_failure()
        assert breaker.is_open
        assert breaker.failure_count == 3

    @pytest.mark.asyncio
    async def test_circuit_breaker_closes_on_success(self):
        """Test that circuit breaker closes on success."""
        breaker = CircuitBreaker(failure_threshold=3, timeout_seconds=60)

        # Open the circuit
        for _ in range(3):
            await breaker.record_failure()
        assert breaker.is_open

        # Close with success
        await breaker.record_success()
        assert not breaker.is_open
        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_prevents_attempts_when_open(self):
        """Test that circuit breaker prevents attempts when open."""
        breaker = CircuitBreaker(failure_threshold=3, timeout_seconds=60)

        # Open the circuit
        for _ in range(3):
            await breaker.record_failure()

        assert not await breaker.can_attempt()

    @pytest.mark.asyncio
    async def test_circuit_breaker_allows_attempt_after_timeout(self):
        """Test that circuit breaker allows attempt after timeout."""
        breaker = CircuitBreaker(failure_threshold=3, timeout_seconds=1)  # 1 second timeout

        # Open the circuit
        for _ in range(3):
            await breaker.record_failure()

        assert not await breaker.can_attempt()

        # Wait for timeout
        await asyncio.sleep(1.1)

        # Should now allow attempt
        assert await breaker.can_attempt()
        # And should be closed
        assert not breaker.is_open

    @pytest.mark.asyncio
    async def test_circuit_breaker_get_state(self):
        """Test getting circuit breaker state."""
        breaker = CircuitBreaker(failure_threshold=5, timeout_seconds=60)

        state = breaker.get_state()
        assert state["is_open"] is False
        assert state["failure_count"] == 0
        assert state["failure_threshold"] == 5
        assert state["timeout_seconds"] == 60

        # Open the circuit
        for _ in range(5):
            await breaker.record_failure()

        state = breaker.get_state()
        assert state["is_open"] is True
        assert state["failure_count"] == 5
        assert state["time_until_recovery"] > 0


class TestDegradationLevel:
    """Test DegradationLevel enum and responses."""

    def test_degradation_level_enum(self):
        """Test degradation level enum values."""
        assert DegradationLevel.NORMAL.value == "normal"
        assert DegradationLevel.DEGRADED.value == "degraded"
        assert DegradationLevel.MINIMAL.value == "minimal"
        assert DegradationLevel.UNAVAILABLE.value == "unavailable"

    def test_degraded_response_normal(self):
        """Test degraded response for normal level."""
        response = DegradationResponse(
            level=DegradationLevel.NORMAL,
            message="System operating normally",
            can_retry=False
        )
        assert response.level == DegradationLevel.NORMAL
        assert response.can_retry is False
        assert response.data is None

    def test_degraded_response_degraded(self):
        """Test degraded response for degraded level."""
        response = DegradationResponse(
            level=DegradationLevel.DEGRADED,
            message="Some services unavailable",
            data={"quality": "reduced"},
            can_retry=True,
            retry_after_seconds=30
        )
        assert response.level == DegradationLevel.DEGRADED
        assert response.can_retry is True
        assert response.retry_after_seconds == 30
        assert response.data["quality"] == "reduced"


class TestGracefulDegradationManager:
    """Test GracefulDegradationManager."""

    @pytest.mark.asyncio
    async def test_manager_initial_state(self):
        """Test manager starts in normal state."""
        manager = GracefulDegradationManager()
        assert manager.current_level == DegradationLevel.NORMAL
        assert len(manager.failure_counts) == 0

    @pytest.mark.asyncio
    async def test_record_failure_increases_count(self):
        """Test that recording failure increases count."""
        manager = GracefulDegradationManager()
        await manager.record_failure("test_service", Exception("test error"))

        assert manager.failure_counts["test_service"] == 1

    @pytest.mark.asyncio
    async def test_record_success_resets_count(self):
        """Test that recording success resets count."""
        manager = GracefulDegradationManager()
        await manager.record_failure("test_service", Exception("test error"))
        await manager.record_success("test_service")

        assert manager.failure_counts["test_service"] == 0

    @pytest.mark.asyncio
    async def test_degraded_response_normal_level(self):
        """Test degraded response when system is normal."""
        manager = GracefulDegradationManager()
        response = manager.get_degraded_response("test_task")

        assert response.level == DegradationLevel.NORMAL
        assert response.can_retry is False

    @pytest.mark.asyncio
    async def test_can_attempt_service_no_breaker(self):
        """Test can attempt service when no breaker exists."""
        manager = GracefulDegradationManager()
        assert await manager.can_attempt_service("new_service") is True

    @pytest.mark.asyncio
    async def test_can_attempt_service_closed_breaker(self):
        """Test can attempt service when breaker is closed."""
        manager = GracefulDegradationManager()
        await manager.record_failure("test_service", Exception("test"))
        await manager.record_success("test_service")  # Reset

        assert await manager.can_attempt_service("test_service") is True

    @pytest.mark.asyncio
    async def test_cannot_attempt_service_open_breaker(self):
        """Test cannot attempt service when breaker is open."""
        manager = GracefulDegradationManager()

        # Open the circuit breaker
        for _ in range(5):
            await manager.record_failure("test_service", Exception("test"))

        assert not await manager.can_attempt_service("test_service")

    @pytest.mark.asyncio
    async def test_get_system_status(self):
        """Test getting system status."""
        manager = GracefulDegradationManager()
        await manager.record_failure("service1", Exception("test1"))
        await manager.record_failure("service2", Exception("test2"))

        status = manager.get_system_status()

        assert status["current_level"] == DegradationLevel.NORMAL.value
        assert "failure_counts" in status
        assert "circuit_breakers" in status
        assert len(status["circuit_breakers"]) == 2

    @pytest.mark.asyncio
    async def test_multiple_services_failing(self):
        """Test degradation with multiple failing services."""
        manager = GracefulDegradationManager()

        # Fail service1 enough to open circuit
        for _ in range(5):
            await manager.record_failure("anthropic", Exception("timeout"))

        # Should now be degraded
        response = manager.get_degraded_response("test")
        assert response.level == DegradationLevel.DEGRADED

        # Fail another service
        for _ in range(5):
            await manager.record_failure("openai", Exception("error"))

        # Should now be minimal
        response = manager.get_degraded_response("test")
        assert response.level == DegradationLevel.MINIMAL


class TestGlobalDegradationManager:
    """Test global degradation manager instance."""

    @pytest.mark.asyncio
    async def test_global_manager_accessible(self):
        """Test that global manager is accessible."""
        from src.content_engine.utils.degradation import degradation_manager

        assert degradation_manager is not None
        assert isinstance(degradation_manager, GracefulDegradationManager)

    @pytest.mark.asyncio
    async def test_global_manager_state_persistence(self):
        """Test that global manager maintains state."""
        from src.content_engine.utils.degradation import degradation_manager

        initial_level = degradation_manager.current_level

        # Record a failure
        await degradation_manager.record_failure("test_global", Exception("test"))

        # Check that state changed
        assert "test_global" in degradation_manager.failure_counts


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    @pytest.mark.asyncio
    async def test_service_failure_recovery_cycle(self):
        """Test complete failure and recovery cycle."""
        manager = GracefulDegradationManager()

        # Service is working normally
        assert await manager.can_attempt_service("api_service") is True
        response = manager.get_degraded_response("task")
        assert response.level == DegradationLevel.NORMAL

        # Service starts failing
        for i in range(5):
            await manager.record_failure("api_service", Exception(f"failure_{i}"))

        # Circuit should be open
        assert not await manager.can_attempt_service("api_service")
        response = manager.get_degraded_response("task")
        assert response.level == DegradationLevel.DEGRADED

        # Service recovers
        await manager.record_success("api_service")

        # Circuit should be closed
        assert await manager.can_attempt_service("api_service")
        response = manager.get_degraded_response("task")
        assert response.level == DegradationLevel.NORMAL

    @pytest.mark.asyncio
    async def test_concurrent_failure_recording(self):
        """Test handling concurrent failure recordings."""
        manager = GracefulDegradationManager()

        # Record failures concurrently
        tasks = [
            manager.record_failure(f"service_{i}", Exception(f"error_{i}"))
            for i in range(10)
        ]
        await asyncio.gather(*tasks)

        # All failures should be recorded
        assert len(manager.failure_counts) == 10
        for i in range(10):
            assert manager.failure_counts[f"service_{i}"] == 1


# Run tests with: pytest tests/test_degradation.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
