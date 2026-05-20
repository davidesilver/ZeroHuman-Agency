"""Pragmatic Heartbeat System Tests.

Tests focus on resilience and graceful degradation rather than
complete feature coverage.
"""

import pytest
import asyncio
import time
from content_engine.utils.heartbeat import (
    HeartbeatCache,
    RateLimiter,
    record_agent_heartbeat,
    get_cached_heartbeat,
    get_all_cached_heartbeats,
    get_cache_stats,
    _extract_agent_identifier,
)


class TestHeartbeatCache:
    """Test bounded cache implementation."""

    def test_cache_basic_operations(self):
        """Test basic get/set operations."""
        cache = HeartbeatCache(max_size=10, ttl_seconds=60)

        # Set and get
        cache.set("key1", {"data": "value1", "timestamp": time.time()})
        result = cache.get("key1")

        assert result is not None
        assert result["data"] == "value1"

    def test_cache_ttl_expiration(self):
        """Test that cache entries expire after TTL."""
        cache = HeartbeatCache(max_size=10, ttl_seconds=1)

        # Set entry
        cache.set("key1", {"data": "value1", "timestamp": time.time()})

        # Should be available immediately
        assert cache.get("key1") is not None

        # Wait for expiration
        time.sleep(1.1)

        # Should be expired
        assert cache.get("key1") is None

    def test_cache_lru_eviction(self):
        """Test that cache evicts oldest entries when full."""
        cache = HeartbeatCache(max_size=3, ttl_seconds=60)

        # Fill cache
        for i in range(5):
            cache.set(f"key{i}", {"data": f"value{i}", "timestamp": time.time()})

        # Only last 3 should remain
        assert cache.get("key0") is None
        assert cache.get("key1") is None
        assert cache.get("key2") is not None
        assert cache.get("key3") is not None
        assert cache.get("key4") is not None

    def test_cache_lru_promotion(self):
        """Test that accessing an entry promotes it in LRU order."""
        cache = HeartbeatCache(max_size=3, ttl_seconds=60)

        # Fill cache
        cache.set("key1", {"data": "value1", "timestamp": time.time()})
        cache.set("key2", {"data": "value2", "timestamp": time.time()})
        cache.set("key3", {"data": "value3", "timestamp": time.time()})

        # Access key1 (should promote it)
        cache.get("key1")

        # Add new entry (key4)
        cache.set("key4", {"data": "value4", "timestamp": time.time()})

        # key2 should be evicted (oldest unused), key1 should remain
        assert cache.get("key1") is not None
        assert cache.get("key2") is None
        assert cache.get("key3") is not None
        assert cache.get("key4") is not None


class TestRateLimiter:
    """Test rate limiting implementation."""

    def test_rate_limiter_basic(self):
        """Test basic rate limiting."""
        limiter = RateLimiter(max_requests=5, time_window_seconds=60)

        brand_id = "test-brand"

        # First 5 requests should be allowed
        for _ in range(5):
            assert limiter.is_allowed(brand_id) is True

        # 6th request should be denied
        assert limiter.is_allowed(brand_id) is False

    def test_rate_limiter_time_window(self):
        """Test that rate limit resets after time window."""
        limiter = RateLimiter(max_requests=2, time_window_seconds=1)

        brand_id = "test-brand"

        # First 2 requests allowed
        assert limiter.is_allowed(brand_id) is True
        assert limiter.is_allowed(brand_id) is True

        # 3rd request denied
        assert limiter.is_allowed(brand_id) is False

        # Wait for time window
        time.sleep(1.1)

        # Should be allowed again
        assert limiter.is_allowed(brand_id) is True

    def test_rate_limiter_per_brand(self):
        """Test that rate limiting is per-brand."""
        limiter = RateLimiter(max_requests=2, time_window_seconds=60)

        # Each brand should have its own limit
        assert limiter.is_allowed("brand1") is True
        assert limiter.is_allowed("brand1") is True
        assert limiter.is_allowed("brand1") is False  # brand1 limit reached

        # brand2 should still be allowed
        assert limiter.is_allowed("brand2") is True


class TestAgentIdentifierExtraction:
    """Test agent identifier extraction from context/action."""

    def test_god_system_sub_agents(self):
        """Test extraction for God System sub-agents."""
        assert _extract_agent_identifier("god_advocate", "advocate") == "god_advocate"
        assert _extract_agent_identifier("god_factcheck", "factcheck") == "god_factcheck"
        assert _extract_agent_identifier("god_creative", "creative") == "god_creative"
        assert _extract_agent_identifier("god_synthesis", "synthesis") == "god_synthesis"

    def test_regular_agents(self):
        """Test extraction for regular agents."""
        assert _extract_agent_identifier("writer_initial", "generate_content") == "writer"
        assert _extract_agent_identifier("editor_refine", "edit_content") == "editor"
        assert _extract_agent_identifier("humanizer_pass1", "humanize") == "humanizer"

    def test_fallback_to_action(self):
        """Test fallback to action when context has no underscore."""
        assert _extract_agent_identifier("general", "call_llm") == "call_llm"
        assert _extract_agent_identifier("simple", "generate") == "generate"


@pytest.mark.asyncio
class TestHeartbeatRecording:
    """Test heartbeat recording functionality."""

    async def test_heartbeat_logging(self, caplog):
        """Test that heartbeat logs properly."""
        import logging

        with caplog.at_level(logging.INFO):
            await record_agent_heartbeat(
                brand_id="test-brand",
                llm_meta={
                    "model_used": "claude-3-5-haiku-20241022",
                    "engine": "anthropic",
                    "latency_ms": 1234,
                    "tokens_prompt": 100,
                    "tokens_completion": 50,
                },
                context="writer_initial",
                action="generate_content",
                status="healthy",
            )

        # Check that log was created
        assert any("Heartbeat:" in record.message for record in caplog.records)
        assert any("writer" in record.message for record in caplog.records)

    async def test_heartbeat_cache_storage(self):
        """Test that heartbeat stores in cache."""
        await record_agent_heartbeat(
            brand_id="test-brand",
            llm_meta={"model_used": "test-model", "engine": "test"},
            context="god_advocate",
            action="advocate",
            status="healthy",
        )

        # Should be retrievable from cache
        cached = get_cached_heartbeat("test-brand", "god_advocate")
        assert cached is not None
        assert cached["status"] == "healthy"
        assert cached["llm_meta"]["model_used"] == "test-model"

    async def test_heartbeat_get_all_for_brand(self):
        """Test getting all heartbeats for a brand."""
        # Use unique brand IDs to avoid cache pollution from other tests
        brand_a = "get-all-brand-a"
        brand_b = "get-all-brand-b"

        # Record multiple heartbeats
        await record_agent_heartbeat(
            brand_id=brand_a,
            llm_meta={"model_used": "model1"},
            context="god_advocate",
            action="advocate",
            status="healthy",
        )

        await record_agent_heartbeat(
            brand_id=brand_a,
            llm_meta={"model_used": "model2"},
            context="god_factcheck",
            action="factcheck",
            status="healthy",
        )

        await record_agent_heartbeat(
            brand_id=brand_b,
            llm_meta={"model_used": "model3"},
            context="writer_initial",
            action="generate",
            status="healthy",
        )

        # Get all for brand_a
        all_heartbeats = get_all_cached_heartbeats(brand_a)

        assert len(all_heartbeats) == 2
        assert "god_advocate" in all_heartbeats
        assert "god_factcheck" in all_heartbeats
        assert "writer" not in all_heartbeats  # Different brand

    async def test_heartbeat_graceful_degradation(self):
        """Test that heartbeat never raises exceptions."""
        # This should not raise even with invalid data
        try:
            await record_agent_heartbeat(
                brand_id="test-brand",
                llm_meta=None,  # Invalid metadata
                context="test",
                action="test",
                status="healthy",
            )
            # If we get here, test passed
            assert True
        except Exception as e:
            pytest.fail(f"Heartbeat raised exception: {e}")


class TestCacheStats:
    """Test cache statistics."""

    def test_cache_stats(self):
        """Test that cache stats are accurate."""
        stats = get_cache_stats()

        assert "cache_size" in stats
        assert "max_size" in stats
        assert "ttl_seconds" in stats
        assert "rate_limit_max" in stats
        assert "rate_limit_window" in stats

        assert stats["max_size"] == 1000  # Default
        assert stats["ttl_seconds"] == 60  # Default


@pytest.mark.asyncio
class TestHeartbeatPerformance:
    """Test heartbeat system performance."""

    async def test_concurrent_heartbeat_recording(self):
        """Test that heartbeat handles concurrent requests."""
        import asyncio

        brand_id = "perf-test-brand"

        # Create 100 concurrent heartbeat requests
        tasks = [
            record_agent_heartbeat(
                brand_id=brand_id,
                llm_meta={"model_used": f"model{i}", "engine": "test"},
                context=f"context{i}",
                action=f"action{i}",
                status="healthy",
            )
            for i in range(100)
        ]

        # All should complete without errors
        await asyncio.gather(*tasks)

        # Verify cache has entries
        all_heartbeats = get_all_cached_heartbeats(brand_id)
        assert len(all_heartbeats) > 0

    async def test_rate_limiting_under_load(self):
        """Test rate limiting prevents cache flooding."""
        from content_engine.utils.heartbeat import _rate_limiter

        brand_id = "load-test-brand"

        # Reset rate limiter for this test
        _rate_limiter._requests[brand_id] = []

        # Try to send 200 requests (limit is 100 per 60 seconds)
        success_count = 0
        for i in range(200):
            if _rate_limiter.is_allowed(brand_id):
                success_count += 1

        # Should be limited to 100
        assert success_count == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
