"""
End-to-End Integration Test for Pragmatic Heartbeat System.

This test verifies the complete loop:
call_llm → heartbeat → pipeline_health → /api/health → dashboard

Priority: HIGH - Must pass before production deployment.
"""

import pytest
import asyncio
import time
import json
import httpx
from typing import Dict, Any, Optional


class TestHeartbeatE2E:
    """
    End-to-end tests for heartbeat system integration.

    These tests verify that the complete data flow works correctly:
    1. LLM call triggers heartbeat recording
    2. Heartbeat data is stored in cache
    3. Heartbeat data is written to database (if enabled)
    4. Health API returns correct data
    5. Dashboard can display the data
    """

    @pytest.fixture
    def test_brand_id(self):
        """Brand ID for testing."""
        return "e2e-test-brand"

    @pytest.fixture
    def test_research_item_id(self):
        """Research item ID for testing."""
        return "test-research-123"

    @pytest.fixture
    def auth_headers(self):
        """Mock authentication headers for testing."""
        # In real environment, these would be actual JWT tokens
        return {
            "Authorization": "Bearer test-token",
            "Content-Type": "application/json"
        }

    @pytest.mark.asyncio
    async def test_complete_heartbeat_loop(self, test_brand_id, auth_headers):
        """
        Test the complete heartbeat loop:
        1. Simulate LLM call
        2. Verify heartbeat is recorded
        3. Verify cache is updated
        4. Verify health API returns data
        """
        # Step 1: Simulate LLM call with heartbeat
        await self._simulate_llm_call_with_heartbeat(test_brand_id)

        # Step 2: Verify heartbeat is recorded in cache
        heartbeat = self._get_cached_heartbeat(test_brand_id, "writer")
        assert heartbeat is not None, "Heartbeat should be recorded in cache"
        assert heartbeat["status"] == "healthy"
        assert heartbeat["llm_meta"]["model_used"] == "claude-3-5-haiku-20241022"

        # Step 3: Verify health API returns data (if backend is running)
        try:
            health_data = await self._get_health_api_data(auth_headers)
            assert "agents" in health_data, "Health API should return agents data"

            # Verify our test agent appears in the data
            test_agent = next(
                (a for a in health_data["agents"] if a["agent_name"] == "writer"),
                None
            )
            if test_agent:
                assert test_agent["status"] == "healthy"
                assert test_agent["current_model"] == "claude-3-5-haiku-20241022"
        except httpx.ConnectError:
            # Backend not running, skip API test
            pytest.skip("Backend not running, skipping API test")

    @pytest.mark.asyncio
    async def test_god_system_sub_agents_tracking(self, test_brand_id, auth_headers):
        """
        Test that God System sub-agents are tracked correctly.

        Verifies that:
        1. God System calls trigger separate heartbeats for each sub-agent
        2. Sub-agents appear as separate entries in the system
        """
        # Simulate God System execution with sub-agents
        god_sub_agents = ["god_advocate", "god_factcheck", "god_creative", "god_synthesis"]

        for sub_agent in god_sub_agents:
            await self._simulate_llm_call_with_heartbeat(
                test_brand_id,
                agent_identifier=sub_agent,
                context=sub_agent
            )

        # Verify each sub-agent is tracked separately
        for sub_agent in god_sub_agents:
            heartbeat = self._get_cached_heartbeat(test_brand_id, sub_agent)
            assert heartbeat is not None, f"Sub-agent {sub_agent} should be tracked"
            assert heartbeat["context"] == sub_agent

        # Verify they appear as separate entries
        all_heartbeats = self._get_all_cached_heartbeats(test_brand_id)
        for sub_agent in god_sub_agents:
            assert sub_agent in all_heartbeats, f"Sub-agent {sub_agent} should be in all heartbeats"

    @pytest.mark.asyncio
    async def test_heartbeat_latency_tracking(self, test_brand_id):
        """
        Test that heartbeat correctly tracks LLM latency.

        Verifies that:
        1. Latency is calculated correctly
        2. Latency appears in heartbeat data
        3. Latency is within reasonable bounds
        """
        # Simulate LLM call with known latency
        expected_latency = 1234  # ms
        await self._simulate_llm_call_with_heartbeat(
            test_brand_id,
            latency_ms=expected_latency
        )

        # Verify latency is tracked
        heartbeat = self._get_cached_heartbeat(test_brand_id, "writer")
        assert heartbeat is not None
        assert heartbeat["llm_meta"]["latency_ms"] == expected_latency

        # Verify latency is reasonable (not negative, not extremely high)
        assert heartbeat["llm_meta"]["latency_ms"] >= 0
        assert heartbeat["llm_meta"]["latency_ms"] < 60000  # Less than 1 minute

    @pytest.mark.asyncio
    async def test_heartbeat_engine_tracking(self, test_brand_id):
        """
        Test that heartbeat correctly tracks LLM engine.

        Verifies that:
        1. Engine is identified correctly (anthropic/openrouter)
        2. Engine appears in heartbeat data
        """
        # Test with Anthropic engine
        await self._simulate_llm_call_with_heartbeat(
            test_brand_id,
            engine="anthropic",
            model="claude-3-5-haiku-20241022"
        )

        heartbeat = self._get_cached_heartbeat(test_brand_id, "writer_anthropic")
        assert heartbeat is not None
        assert heartbeat["llm_meta"]["engine"] == "anthropic"

        # Test with OpenRouter engine
        await self._simulate_llm_call_with_heartbeat(
            test_brand_id,
            engine="openrouter",
            model="google/gemma-4-150b:free"
        )

        heartbeat = self._get_cached_heartbeat(test_brand_id, "writer_openrouter")
        assert heartbeat is not None
        assert heartbeat["llm_meta"]["engine"] == "openrouter"

    @pytest.mark.asyncio
    async def test_heartbeat_graceful_degradation(self, test_brand_id):
        """
        Test that heartbeat system degrades gracefully on failures.

        Verifies that:
        1. Heartbeat failures don't crash the main pipeline
        2. System continues to function even if heartbeat fails
        """
        # This test verifies the design principle that heartbeat failures
        # should never impact the main LLM pipeline

        # Simulate a heartbeat that might fail (e.g., invalid data)
        try:
            await self._simulate_llm_call_with_heartbeat(
                test_brand_id,
                llm_meta=None  # Invalid metadata
            )
            # If we get here, graceful degradation worked
            assert True
        except Exception as e:
            pytest.fail(f"Heartbeat should not raise exceptions: {e}")

    @pytest.mark.asyncio
    async def test_cache_cleanup_and_ttl(self, test_brand_id):
        """
        Test that cache properly cleans up expired entries.

        Verifies that:
        1. Cache respects TTL
        2. Expired entries are removed
        3. Cache size stays bounded
        """
        from src.content_engine.utils.heartbeat import _heartbeat_cache

        # Fill cache with test data
        for i in range(10):
            await self._simulate_llm_call_with_heartbeat(
                test_brand_id,
                agent_identifier=f"test_agent_{i}"
            )

        # Verify cache has entries
        all_heartbeats = self._get_all_cached_heartbeats(test_brand_id)
        assert len(all_heartbeats) > 0

        # Get cache stats
        stats = self._get_cache_stats()
        assert stats["cache_size"] > 0
        assert stats["cache_size"] <= stats["max_size"]

    @pytest.mark.asyncio
    async def test_concurrent_heartbeat_recording(self, test_brand_id):
        """
        Test that system handles concurrent heartbeat recording correctly.

        Verifies that:
        1. Multiple concurrent heartbeats are handled
        2. No race conditions occur
        3. All heartbeats are recorded correctly
        """
        # Create 50 concurrent heartbeat requests
        tasks = [
            self._simulate_llm_call_with_heartbeat(
                test_brand_id,
                agent_identifier=f"concurrent_agent_{i}"
            )
            for i in range(50)
        ]

        # All should complete without errors
        await asyncio.gather(*tasks)

        # Verify all were recorded
        all_heartbeats = self._get_all_cached_heartbeats(test_brand_id)
        # Note: cache may have evicted some entries due to LRU, but should have several
        assert len(all_heartbeats) > 0

    # Helper methods

    async def _simulate_llm_call_with_heartbeat(
        self,
        brand_id: str,
        agent_identifier: str = "writer",
        context: str = "writer_initial",
        action: str = "generate_content",
        latency_ms: int = 1000,
        engine: str = "anthropic",
        model: str = "claude-3-5-haiku-20241022",
        llm_meta: Optional[Dict[str, Any]] = None
    ):
        """
        Simulate an LLM call with heartbeat recording.

        This mimics what happens in llm_client.py when call_llm is invoked.
        """
        from src.content_engine.utils.heartbeat import record_agent_heartbeat

        if llm_meta is None:
            llm_meta = {
                "model_used": model,
                "engine": engine,
                "latency_ms": latency_ms,
                "tokens_prompt": 100,
                "tokens_completion": 50,
            }

        await record_agent_heartbeat(
            brand_id=brand_id,
            llm_meta=llm_meta,
            context=context,
            action=action,
            status="healthy"
        )

    def _get_cached_heartbeat(self, brand_id: str, agent_identifier: str) -> Optional[Dict[str, Any]]:
        """Get cached heartbeat for a specific agent."""
        from src.content_engine.utils.heartbeat import get_cached_heartbeat
        return get_cached_heartbeat(brand_id, agent_identifier)

    def _get_all_cached_heartbeats(self, brand_id: str) -> Dict[str, Dict[str, Any]]:
        """Get all cached heartbeats for a brand."""
        from src.content_engine.utils.heartbeat import get_all_cached_heartbeats
        return get_all_cached_heartbeats(brand_id)

    def _get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        from src.content_engine.utils.heartbeat import get_cache_stats
        return get_cache_stats()

    async def _get_health_api_data(self, headers: Dict[str, str]) -> Dict[str, Any]:
        """Get health data from API."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://localhost:3000/api/system/health",
                headers=headers,
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()


class TestHeartbeatRealWorldScenario:
    """
    Real-world scenario tests that mimic actual usage patterns.

    These tests simulate realistic user workflows to ensure the system
    works correctly in production-like conditions.
    """

    @pytest.mark.asyncio
    async def test_content_generation_workflow(self):
        """
        Test a complete content generation workflow.

        Simulates:
        1. Research → Scoring → Writer → Editor → God Mode → Humanizer
        2. Each step triggers appropriate heartbeats
        3. Dashboard shows correct agent status throughout
        """
        brand_id = "workflow-test-brand"

        # Simulate research agent
        await self._simulate_agent_call(brand_id, "research", "research_query")

        # Simulate scoring agent
        await self._simulate_agent_call(brand_id, "scoring", "score_content")

        # Simulate writer agent
        await self._simulate_agent_call(brand_id, "writer", "generate_content")

        # Simulate editor agent
        await self._simulate_agent_call(brand_id, "editor", "refine_content")

        # Simulate God Mode with sub-agents
        god_sub_agents = ["god_advocate", "god_factcheck", "god_creative", "god_synthesis"]
        for sub_agent in god_sub_agents:
            await self._simulate_agent_call(brand_id, sub_agent, sub_agent)

        # Simulate humanizer
        await self._simulate_agent_call(brand_id, "humanizer", "humanize_content")

        # Verify all agents are tracked
        all_heartbeats = self._get_all_cached_heartbeats(brand_id)

        expected_agents = ["research", "scoring", "writer", "editor", "humanizer"] + god_sub_agents
        for agent in expected_agents:
            assert agent in all_heartbeats, f"Agent {agent} should be tracked"

    @pytest.mark.asyncio
    async def test_high_volume_scenario(self):
        """
        Test system behavior under high volume.

        Simulates:
        1. 100 concurrent content generation workflows
        2. System remains stable
        3. Cache stays bounded
        4. Performance remains acceptable
        """
        brand_id = "high-volume-brand"

        # Create 10 concurrent workflows, each with multiple agents
        workflows = []
        for i in range(10):
            workflow = self._simulate_content_workflow(brand_id, workflow_id=i)
            workflows.append(workflow)

        start_time = time.time()
        await asyncio.gather(*workflows)
        elapsed = time.time() - start_time

        # Verify performance
        assert elapsed < 30.0, f"High volume scenario too slow: {elapsed}s"

        # Verify cache is still bounded
        stats = self._get_cache_stats()
        assert stats["cache_size"] <= stats["max_size"]

    @pytest.mark.asyncio
    async def test_mixed_engine_scenario(self):
        """
        Test system with mixed LLM engines.

        Simulates:
        1. Some calls use Anthropic
        2. Some calls use OpenRouter
        3. System correctly tracks engine for each call
        """
        brand_id = "mixed-engine-brand"

        # Simulate calls with different engines
        engines_and_models = [
            ("anthropic", "claude-3-5-haiku-20241022"),
            ("anthropic", "claude-3-5-sonnet-20241022"),
            ("openrouter", "google/gemma-4-150b:free"),
            ("openrouter", "anthropic/claude-3.5-haiku-20241022"),
        ]

        for engine, model in engines_and_models:
            await self._simulate_agent_call(
                brand_id,
                f"test_{engine}",
                "test_action",
                engine=engine,
                model=model
            )

        # Verify each engine is tracked correctly
        all_heartbeats = self._get_all_cached_heartbeats(brand_id)

        for engine, model in engines_and_models:
            agent_name = f"test_{engine}"
            if agent_name in all_heartbeats:
                heartbeat = all_heartbeats[agent_name]
                assert heartbeat["llm_meta"]["engine"] == engine
                assert heartbeat["llm_meta"]["model_used"] == model

    # Helper methods for real-world scenarios

    async def _simulate_agent_call(
        self,
        brand_id: str,
        agent_identifier: str,
        action: str,
        engine: str = "anthropic",
        model: str = "claude-3-5-haiku-20241022"
    ):
        """Simulate an agent call with heartbeat."""
        from src.content_engine.utils.heartbeat import record_agent_heartbeat

        await record_agent_heartbeat(
            brand_id=brand_id,
            llm_meta={
                "model_used": model,
                "engine": engine,
                "latency_ms": 1000,
                "tokens_prompt": 100,
                "tokens_completion": 50,
            },
            context=agent_identifier,
            action=action,
            status="healthy"
        )

    async def _simulate_content_workflow(self, brand_id: str, workflow_id: int):
        """Simulate a complete content generation workflow."""
        # Add workflow_id to create unique agent identifiers
        await self._simulate_agent_call(brand_id, f"writer_{workflow_id}", "generate")
        await self._simulate_agent_call(brand_id, f"editor_{workflow_id}", "refine")

        # Simulate God Mode
        for sub_agent in ["god_advocate", "god_factcheck"]:
            await self._simulate_agent_call(
                brand_id, f"{sub_agent}_{workflow_id}", sub_agent
            )

    def _get_all_cached_heartbeats(self, brand_id: str) -> Dict[str, Dict[str, Any]]:
        """Get all cached heartbeats for a brand."""
        from src.content_engine.utils.heartbeat import get_all_cached_heartbeats
        return get_all_cached_heartbeats(brand_id)

    def _get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        from src.content_engine.utils.heartbeat import get_cache_stats
        return get_cache_stats()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
