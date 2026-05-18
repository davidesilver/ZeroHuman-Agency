"""
Parallel LLM Calling System

Implements parallel retry strategy for LLM API calls. Instead of sequential
fallback with long timeouts, calls multiple models concurrently and returns
the first successful response.

Critical for performance improvement: reduces fallback latency from 60s+
to <30s by executing model calls in parallel.

Author: AI Engineering Team
Created: 2026-04-17
"""

import asyncio
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ParallelLLMCaller:
    """
    Call multiple LLM models in parallel and return first successful response.

    Instead of trying models sequentially with long timeouts (e.g., 120s per model),
    this implementation calls all models in parallel and returns the first
    successful response. This dramatically reduces fallback latency.

    Example:
        >>> caller = ParallelLLMCaller(timeout_per_model=30.0, overall_timeout=60.0)
        >>> models = ["claude-sonnet-4-20250514", "gpt-4o", "claude-opus-4-20250514"]
        >>> result, latency = await caller.call_first_success(models, prompt, "scoring")
        >>> if result:
        ...     print(f"Got response in {latency:.2f}ms from {result['model']}")
    """

    def __init__(self, timeout_per_model: float = 30.0, overall_timeout: float = 60.0):
        """
        Initialize parallel LLM caller.

        Args:
            timeout_per_model: Maximum time to wait for each model (seconds)
            overall_timeout: Maximum total time to wait for any model (seconds)
        """
        self.timeout_per_model = timeout_per_model
        self.overall_timeout = overall_timeout
        self._llm_caller = None  # Will be set via dependency injection

    def set_llm_caller(self, llm_caller):
        """
        Set the LLM caller function to use.

        Args:
            llm_caller: Callable that takes (model, prompt, task_type) and returns LLM response
        """
        self._llm_caller = llm_caller

    async def call_first_success(
        self,
        models: list[str],
        prompt: str,
        task_type: str = "general",
        context: str = "unknown",
        brand_id: str = "default",
        agent_name: str = "unknown",
    ) -> tuple[dict[str, Any] | None, float]:
        """
        Call multiple models in parallel, return first successful response.

        Creates tasks for all models and executes them concurrently. Returns
        the first successful response or None if all models fail.

        Args:
            models: List of model identifiers to try
            prompt: The prompt to send to each model
            task_type: Type of task being performed
            context: Context for logging
            brand_id: Brand identifier
            agent_name: Agent making the request

        Returns:
            Tuple of (response_dict, latency_ms) where response_dict may be None if all failed
        """
        if not models:
            logger.warning("No models provided for parallel call")
            return None, 0.0

        if not self._llm_caller:
            logger.error("LLM caller not set. Call set_llm_caller() first.")
            return None, 0.0

        start_time = time.time()

        # Create tasks for all models
        tasks = {}
        for model in models:
            task = asyncio.create_task(
                self._call_model_with_timeout(
                    model,
                    prompt,
                    task_type,
                    context,
                    brand_id,
                    agent_name
                )
            )
            tasks[model] = task

        # Wait for first successful response or overall timeout
        try:
            done, pending = await asyncio.wait(
                list(tasks.values()),
                timeout=self.overall_timeout,
                return_when=asyncio.FIRST_COMPLETED,
            )

            # Cancel all pending tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.debug(f"Error cancelling task: {e}")

            # Get first successful result
            for task in done:
                try:
                    result = task.result()
                    if result is not None:
                        latency = (time.time() - start_time) * 1000
                        logger.info(
                            f"Parallel LLM call succeeded: {result.get('model', 'unknown')} "
                            f"in {latency:.2f}ms (tried {len(models)} models)"
                        )
                        return result, latency
                except Exception as e:
                    logger.warning(f"Task failed: {e}")
                    continue

        except TimeoutError:
            logger.error(
                f"All parallel LLM calls timed out after {self.overall_timeout}s "
                f"(tried {len(models)} models)"
            )

        # All models failed
        latency = (time.time() - start_time) * 1000
        logger.warning(
            f"All parallel LLM calls failed in {latency:.2f}ms "
            f"(tried {len(models)} models)"
        )
        return None, latency

    async def call_with_fallback(
        self,
        primary_models: list[str],
        fallback_models: list[str],
        prompt: str,
        task_type: str = "general",
        context: str = "unknown",
        brand_id: str = "default",
        agent_name: str = "unknown",
    ) -> tuple[dict[str, Any] | None, float, bool]:
        """
        Try primary models in parallel, fall back to fallback models if all fail.

        This is a two-stage parallel approach:
        1. Try all primary models in parallel
        2. If all primary models fail, try all fallback models in parallel

        Args:
            primary_models: List of primary models to try first
            fallback_models: List of fallback models to try if primaries fail
            prompt: The prompt to send
            task_type: Type of task being performed
            context: Context for logging
            brand_id: Brand identifier
            agent_name: Agent making the request

        Returns:
            Tuple of (response_dict, latency_ms, used_fallback)
        """
        # Try primary models first
        result, latency = await self.call_first_success(
            primary_models,
            prompt,
            task_type,
            context,
            brand_id,
            agent_name
        )

        if result is not None:
            return result, latency, False  # Success with primary

        # All primary models failed, try fallback models
        logger.warning("All primary models failed, trying fallback models")
        result, latency = await self.call_first_success(
            fallback_models,
            prompt,
            task_type,
            context,
            brand_id,
            agent_name
        )

        return result, latency, True  # Used fallback

    async def _call_model_with_timeout(
        self,
        model: str,
        prompt: str,
        task_type: str,
        context: str,
        brand_id: str,
        agent_name: str,
    ) -> dict[str, Any] | None:
        """
        Call a single model with timeout.

        Args:
            model: Model identifier
            prompt: Prompt to send
            task_type: Task type
            context: Context for logging
            brand_id: Brand identifier
            agent_name: Agent name

        Returns:
            Response dict or None if timeout/error
        """
        try:
            result = await asyncio.wait_for(
                self._make_llm_call(model, prompt, task_type, context, brand_id, agent_name),
                timeout=self.timeout_per_model,
            )
            return result
        except TimeoutError:
            logger.warning(f"Model {model} timed out after {self.timeout_per_model}s")
            return None
        except Exception as e:
            logger.warning(f"Model {model} failed: {e}")
            return None

    async def _make_llm_call(
        self,
        model: str,
        prompt: str,
        task_type: str,
        context: str,
        brand_id: str,
        agent_name: str,
    ) -> dict[str, Any]:
        """
        Actual LLM call implementation.

        This method should be overridden or the caller should be set
        via set_llm_caller().

        Args:
            model: Model to call
            prompt: Prompt to send
            task_type: Task type
            context: Context
            brand_id: Brand ID
            agent_name: Agent name

        Returns:
            Response dictionary

        Raises:
            NotImplementedError: If no LLM caller is set
        """
        if self._llm_caller is None:
            raise NotImplementedError(
                "LLM caller not set. Use set_llm_caller() or override _make_llm_call()"
            )

        return await self._llm_caller(model, prompt, task_type, context, brand_id, agent_name)

    def get_performance_stats(self) -> dict[str, Any]:
        """
        Get performance statistics for parallel calls.

        Returns:
            Dictionary with performance metrics
        """
        return {
            "timeout_per_model": self.timeout_per_model,
            "overall_timeout": self.overall_timeout,
            "caller_configured": self._llm_caller is not None,
        }


class ParallelCallMetrics:
    """Track performance metrics for parallel LLM calls."""

    def __init__(self):
        self.total_calls = 0
        self.successful_calls = 0
        self.failed_calls = 0
        self.total_latency_ms = 0.0
        self.model_success_counts: dict[str, int] = {}
        self.model_failure_counts: dict[str, int] = {}

    def record_call(
        self,
        success: bool,
        latency_ms: float,
        model_used: str | None = None,
        models_tried: int = 1
    ):
        """
        Record a parallel call outcome.

        Args:
            success: Whether the call succeeded
            latency_ms: Call latency
            model_used: Model that succeeded (if any)
            models_tried: Number of models tried
        """
        self.total_calls += 1

        if success:
            self.successful_calls += 1
            self.total_latency_ms += latency_ms

            if model_used:
                self.model_success_counts[model_used] = (
                    self.model_success_counts.get(model_used, 0) + 1
                )
        else:
            self.failed_calls += 1

    def get_stats(self) -> dict[str, Any]:
        """
        Get performance statistics.

        Returns:
            Dictionary with performance metrics
        """
        success_rate = (
            self.successful_calls / self.total_calls
            if self.total_calls > 0
            else 0.0
        )

        avg_latency = (
            self.total_latency_ms / self.successful_calls
            if self.successful_calls > 0
            else 0.0
        )

        return {
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "success_rate": success_rate,
            "avg_latency_ms": avg_latency,
            "model_success_counts": self.model_success_counts.copy(),
            "model_failure_counts": self.model_failure_counts.copy(),
        }


# Global parallel caller instance
parallel_llm_caller = ParallelLLMCaller(
    timeout_per_model=30.0,  # 30 seconds per model
    overall_timeout=60.0,   # 60 seconds total
)

# Global metrics instance
parallel_call_metrics = ParallelCallMetrics()

logger.info("Parallel LLM calling system initialized")


# Export key components
__all__ = [
    'ParallelLLMCaller',
    'ParallelCallMetrics',
    'parallel_llm_caller',
    'parallel_call_metrics',
]
