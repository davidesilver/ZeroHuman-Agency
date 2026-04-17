"""Centralized LLM Client routing via OpenRouter and Anthropic.

This file has been integrated with all Phase 1-3 improvements:
- Phase 1: Robust JSON parsing, Rate limiting, Enhanced cost tracking
- Phase 2: Graceful degradation, Comprehensive fallback metrics
- Phase 3: Parallel retry strategy, Centralized model routing
"""

from __future__ import annotations

import httpx
import logging
import time
import asyncio
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Tuple

from ..config import settings
from ..db import get_db
from .cost_tracker import track_cost, cost_tracker
from .fallback_monitor import record_call, record_fallback
from .json_parser import RobustJSONParser, json_parser
from .llm_rate_limiter import rate_limiter, RateLimitStrategy
from .degradation import degradation_manager, DegradationLevel
from .fallback_metrics import fallback_metrics
from .parallel_llm import parallel_llm_caller
from ..config.llm_models import (
    ModelCapability,
    get_models_for_capability,
    get_model_ids_for_capability,
    get_model_config,
    get_primary_models_for_capability,
    get_fallback_models_for_capability,
    get_models_by_provider,
)

logger = logging.getLogger("content_engine.llm")


class LLMResponse(BaseModel):
    content: str
    model_used: str
    tokens_prompt: int
    tokens_completion: int
    engine: str = "unknown"          # "anthropic" | "openrouter"
    latency_ms: Optional[int] = None
    fallback_to: Optional[str] = None
    # New fields from Phase 1-3 integration
    degradation_level: Optional[str] = None
    used_parallel: bool = False
    used_fallback: bool = False
    is_emergency: bool = False
    cost_usd: Optional[float] = None


async def call_llm(
    prompt: str,
    brand_id: str,
    context: str = "general",
    action: str = "call_llm",
    system_prompt: Optional[str] = None,
    # Depending on task, we route to the right capability-based model
    task_type: str = "creative",
    temperature: float = 0.7,
) -> LLMResponse:
    """
    Call the best LLM depending on the requested capability, with comprehensive
    Phase 1-3 integration: rate limiting, parallel retry, graceful degradation,
    comprehensive metrics, and robust JSON parsing.

    Model Selection Strategy:
    - Uses centralized model routing from config/llm_models.py
    - Maps task_type to ModelCapability
    - Supports parallel retry for faster fallbacks
    - Applies rate limiting before API calls
    - Records comprehensive metrics
    - Handles graceful degradation

    `task_type` semantic routing (mapped to ModelCapability):
    - reasoning: ModelCapability.REASONING
    - creative: ModelCapability.CREATIVE
    - scoring: ModelCapability.SCORING
    - fact_check: ModelCapability.FACT_CHECK
    - editing: ModelCapability.EDITING
    - research: ModelCapability.RESEARCH
    - default/general: ModelCapability.GENERAL
    """
    start_time = time.monotonic()

    # Map task_type to ModelCapability
    capability = _map_task_type_to_capability(task_type)
    logger.debug("Mapped task_type=%s to capability=%s", task_type, capability)

    # Check current degradation level
    current_degradation = await degradation_manager.get_current_level()
    logger.debug("Current degradation level: %s", current_degradation)

    # Get models based on capability and degradation level
    primary_models, fallback_models = await _get_models_for_degradation(
        capability, current_degradation
    )

    if not primary_models and not fallback_models:
        raise RuntimeError(f"No models available for capability {capability} at degradation level {current_degradation}")

    logger.debug("Primary models: %s, Fallback models: %s", primary_models, fallback_models)

    # Try parallel retry with primary models first
    try:
        if primary_models:
            logger.debug("Attempting parallel call with primary models: %s", primary_models)
            result = await _call_llm_parallel(
                models=primary_models,
                prompt=prompt,
                system_prompt=system_prompt,
                brand_id=brand_id,
                context=context,
                action=action,
                task_type=task_type,
                temperature=temperature,
                start_time=start_time,
                is_emergency=False,
                capability=capability,
            )

            # Record success for degradation manager
            await degradation_manager.record_success("llm_primary")
            record_call()

            # Record heartbeat
            asyncio.create_task(
                _record_heartbeat_safely(
                    brand_id=brand_id,
                    llm_meta={
                        "model_used": result.model_used,
                        "engine": result.engine,
                        "latency_ms": result.latency_ms,
                        "tokens_prompt": result.tokens_prompt,
                        "tokens_completion": result.tokens_completion,
                        "degradation_level": result.degradation_level,
                        "used_parallel": result.used_parallel,
                    },
                    context=context,
                    action=action,
                    status="healthy"
                )
            )

            return result

    except Exception as e:
        logger.error("Primary models failed: %s. Recording failure and trying fallback...", e)
        await degradation_manager.record_failure("llm_primary", e)

    # If primary models failed, try fallback models
    if fallback_models:
        logger.warning("Primary models exhausted, trying fallback models: %s", fallback_models)

        try:
            result = await _call_llm_parallel(
                models=fallback_models,
                prompt=prompt,
                system_prompt=system_prompt,
                brand_id=brand_id,
                context=context,
                action=action,
                task_type=task_type,
                temperature=temperature,
                start_time=start_time,
                is_emergency=False,
                capability=capability,
            )

            # Record fallback usage
            record_fallback(is_emergency=False)
            await degradation_manager.record_success("llm_fallback")

            # Record heartbeat with degraded status
            asyncio.create_task(
                _record_heartbeat_safely(
                    brand_id=brand_id,
                    llm_meta={
                        "model_used": result.model_used,
                        "engine": result.engine,
                        "latency_ms": result.latency_ms,
                        "tokens_prompt": result.tokens_prompt,
                        "tokens_completion": result.tokens_completion,
                        "degradation_level": result.degradation_level,
                        "used_parallel": result.used_parallel,
                    },
                    context=context,
                    action=action,
                    status="degraded"
                )
            )

            return result

        except Exception as e:
            logger.error("Fallback models also failed: %s", e)
            await degradation_manager.record_failure("llm_fallback", e)

    raise RuntimeError(f"All LLM routing options failed for capability {capability} at degradation level {current_degradation}")


async def call_llm_with_json(
    prompt: str,
    brand_id: str,
    context: str = "general",
    action: str = "call_llm_json",
    system_prompt: Optional[str] = None,
    task_type: str = "creative",
    temperature: float = 0.7,
    allow_partial: bool = False,
) -> Dict[str, Any]:
    """
    Call LLM and parse JSON response using robust JSON parser.

    This is a convenience function that combines call_llm with robust JSON parsing.
    Uses all Phase 1-3 integration features.

    Args:
        prompt: The user prompt
        brand_id: Brand ID for tracking
        context: Context label
        action: Action label
        system_prompt: Optional system prompt
        task_type: Type of task
        temperature: Temperature
        allow_partial: Whether to allow partial JSON parsing on failure

    Returns:
        Parsed JSON dictionary

    Raises:
        RuntimeError: If LLM call fails or JSON parsing fails completely
    """
    response = await call_llm(
        prompt=prompt,
        brand_id=brand_id,
        context=context,
        action=action,
        system_prompt=system_prompt,
        task_type=task_type,
        temperature=temperature,
    )

    # Use robust JSON parser
    parsed = json_parser.parse_llm_response(
        text=response.content,
        context=f"{context}:{action}",
        allow_partial=allow_partial,
    )

    if parsed is None:
        raise RuntimeError(
            f"Failed to parse JSON response from {response.model_used}. "
            f"Content: {response.content[:200]}..."
        )

    return parsed


# ============================================================================
# HELPER FUNCTIONS FOR PHASE 1-3 INTEGRATION
# ============================================================================

def _map_task_type_to_capability(task_type: str) -> ModelCapability:
    """Map task_type string to ModelCapability enum.

    Args:
        task_type: Task type string (e.g., "reasoning", "creative", "scoring")

    Returns:
        ModelCapability enum value
    """
    mapping = {
        "reasoning": ModelCapability.REASONING,
        "creative": ModelCapability.CREATIVE,
        "scoring": ModelCapability.SCORING,
        "fact_check": ModelCapability.FACT_CHECK,
        "editing": ModelCapability.EDITING,
        "research": ModelCapability.RESEARCH,
        "coding": ModelCapability.REASONING,
        "agentic": ModelCapability.REASONING,
        "knowledge": ModelCapability.RESEARCH,
        "language": ModelCapability.CREATIVE,
    }

    return mapping.get(task_type, ModelCapability.GENERAL)


async def _get_models_for_degradation(
    capability: ModelCapability,
    degradation_level: DegradationLevel
) -> Tuple[List[str], List[str]]:
    """Get primary and fallback models based on degradation level.

    Args:
        capability: The required capability
        degradation_level: Current degradation level

    Returns:
        Tuple of (primary_models, fallback_models)
    """
    if degradation_level == DegradationLevel.UNAVAILABLE:
        # No models available
        return [], []

    # Get models for capability
    all_models = get_model_ids_for_capability(capability)

    if not all_models:
        return [], []

    # Split into primary and fallback
    primary = get_primary_models_for_capability(capability)
    fallback = get_fallback_models_for_capability(capability)

    # Adjust based on degradation level
    if degradation_level == DegradationLevel.MINIMAL:
        # Only use fastest, most reliable models
        # Filter to top 2 primary models only
        primary = primary[:2]
        fallback = []
    elif degradation_level == DegradationLevel.DEGRADED:
        # Use primary models, but limit count
        primary = primary[:3]
        fallback = fallback[:2]

    return primary, fallback


async def _call_llm_parallel(
    models: List[str],
    prompt: str,
    system_prompt: Optional[str],
    brand_id: str,
    context: str,
    action: str,
    task_type: str,
    temperature: float,
    start_time: float,
    is_emergency: bool,
    capability: ModelCapability,
) -> LLMResponse:
    """Call LLM models in parallel with comprehensive integration.

    This function implements the Phase 1-3 integrated flow:
    1. Apply rate limiting before calls
    2. Call models in parallel (or sequentially if not configured)
    3. Track costs with enhanced cost tracker
    4. Record comprehensive fallback metrics
    5. Handle graceful degradation
    6. Calculate accurate latency
    7. Return enhanced LLMResponse

    Args:
        models: List of model IDs to try
        prompt: User prompt
        system_prompt: Optional system prompt
        brand_id: Brand ID
        context: Context label
        action: Action label
        task_type: Task type
        temperature: Temperature
        start_time: Start time for latency calculation
        is_emergency: Whether this is an emergency call
        capability: Model capability

    Returns:
        Enhanced LLMResponse with all Phase 1-3 data

    Raises:
        RuntimeError: If all models fail
    """
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    last_error = None
    primary_model = models[0] if models else "unknown"
    fallback_start_time = time.monotonic()

    # Check if we should use parallel retry
    # For now, we'll use sequential to maintain compatibility,
    # but this can be switched to parallel easily
    use_parallel = len(models) > 1 and not is_emergency

    if use_parallel:
        logger.debug("Using parallel retry for %d models", len(models))
        try:
            # Set up the LLM caller for parallel execution
            async def llm_caller(model, prompt, task_type, context, brand_id, agent_name):
                return await _call_single_model(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    brand_id=brand_id,
                    context=context,
                    action=action,
                )

            parallel_llm_caller.set_llm_caller(llm_caller)

            # Call models in parallel
            result, latency = await parallel_llm_caller.call_first_success(
                models=models,
                prompt=prompt,
                task_type=task_type,
            )

            if result:
                # Extract response data
                model_used = result.get("model", models[0])
                content = result.get("content", "")
                prompt_tok = result.get("tokens_prompt", 0)
                comp_tok = result.get("tokens_completion", 0)

                # Calculate total latency
                total_latency_ms = int((time.monotonic() - start_time) * 1000)

                # Track cost
                await track_cost(brand_id, context, model_used, action, prompt_tok, comp_tok)

                # Get cost USD
                cost_usd = await cost_tracker.get_cost_by_model(model_used, brand_id)

                # Get current degradation level
                current_degradation = await degradation_manager.get_current_level()

                return LLMResponse(
                    content=content,
                    model_used=model_used,
                    tokens_prompt=prompt_tok,
                    tokens_completion=comp_tok,
                    engine="openrouter",
                    latency_ms=total_latency_ms,
                    degradation_level=current_degradation.value if current_degradation else None,
                    used_parallel=True,
                    used_fallback=not is_emergency and model_used != primary_model,
                    is_emergency=is_emergency,
                    cost_usd=cost_usd,
                )

        except Exception as e:
            logger.warning("Parallel retry failed: %s, falling back to sequential", e)
            last_error = e
            # Fall through to sequential

    # Sequential fallback (original behavior)
    for i, current_model in enumerate(models):
        try:
            # Apply rate limiting
            config = get_model_config(current_model)
            provider = config.provider if config else "unknown"

            rate_limit_key = f"{provider}:{current_model}"
            rate_allowed = await rate_limiter.acquire(rate_limit_key)

            if not rate_allowed:
                logger.warning("Rate limit exceeded for %s, skipping", rate_limit_key)
                raise Exception(f"Rate limit exceeded for {current_model}")

            # Call the model
            response = await _call_single_model(
                model=current_model,
                messages=messages,
                temperature=temperature,
                brand_id=brand_id,
                context=context,
                action=action,
            )

            # Extract response data
            model_used = response.get("model", current_model)
            content = response.get("content", "")
            prompt_tok = response.get("tokens_prompt", 0)
            comp_tok = response.get("tokens_completion", 0)

            # Calculate latency
            total_latency_ms = int((time.monotonic() - start_time) * 1000)

            # Track cost
            await track_cost(brand_id, context, model_used, action, prompt_tok, comp_tok)

            # Get cost USD
            cost_usd = await cost_tracker.get_cost_by_model(model_used, brand_id)

            # Record fallback metrics if this wasn't the first model
            if i > 0:
                fallback_latency_ms = int((time.monotonic() - fallback_start_time) * 1000)

                fallback_metrics.record_fallback(
                    primary_model=primary_model,
                    fallback_model=model_used,
                    reason=f"Model {models[i-1]} failed",
                    task_type=task_type,
                    latency_ms_primary=0,  # Not tracked in sequential
                    latency_ms_fallback=fallback_latency_ms,
                    success=True,
                )

            # Log fallback if this wasn't the first model
            if i > 0:
                await _log_fallback_attempt(
                    brand_id=brand_id,
                    context=context,
                    action=action,
                    primary_model=primary_model,
                    fallback_reason=f"Model {models[i-1]} failed, fell back to {current_model}",
                    is_emergency=is_emergency
                )
                record_fallback(is_emergency=is_emergency)

            # Get current degradation level
            current_degradation = await degradation_manager.get_current_level()

            return LLMResponse(
                content=content,
                model_used=model_used,
                tokens_prompt=prompt_tok,
                tokens_completion=comp_tok,
                engine="openrouter",
                latency_ms=total_latency_ms,
                fallback_to=models[i+1] if i+1 < len(models) else None,
                degradation_level=current_degradation.value if current_degradation else None,
                used_parallel=False,
                used_fallback=i > 0,
                is_emergency=is_emergency,
                cost_usd=cost_usd,
            )

        except Exception as e:
            logger.warning("Model %s failed: %s. Trying next...", current_model, e)
            last_error = e
            continue

    raise RuntimeError(f"All models failed. Last error: {last_error}")


async def _call_single_model(
    model: str,
    messages: List[Dict[str, str]],
    temperature: float,
    brand_id: str,
    context: str,
    action: str,
) -> Dict[str, Any]:
    """Call a single model (either OpenRouter or Anthropic).

    Args:
        model: Model ID
        messages: Message list
        temperature: Temperature
        brand_id: Brand ID
        context: Context label
        action: Action label

    Returns:
        Dictionary with response data

    Raises:
        Exception: If call fails
    """
    # Check if this is an Anthropic model
    if "claude" in model.lower() and settings.anthropic_api_key:
        return await _call_anthropic_direct(
            model=model,
            messages=messages,
            temperature=temperature,
        )
    else:
        # Use OpenRouter
        return await _call_openrouter(
            model=model,
            messages=messages,
            temperature=temperature,
        )


async def _call_openrouter(
    model: str,
    messages: List[Dict[str, str]],
    temperature: float,
) -> Dict[str, Any]:
    """Call OpenRouter API.

    Args:
        model: Model ID
        messages: Message list
        temperature: Temperature

    Returns:
        Dictionary with response data

    Raises:
        Exception: If call fails
    """
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            json={
                "model": model,
                "messages": messages,
                "temperature": temperature if "o3-mini" not in model else 1,
            },
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:3000",
                "X-Title": "Content Engine"
            },
        )
        resp.raise_for_status()

        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        prompt_tok = usage.get("prompt_tokens", 0)
        comp_tok = usage.get("completion_tokens", 0)

        return {
            "model": model,
            "content": content,
            "tokens_prompt": prompt_tok,
            "tokens_completion": comp_tok,
        }


async def _call_anthropic_direct(
    model: str,
    messages: List[Dict[str, str]],
    temperature: float,
) -> Dict[str, Any]:
    """Call Anthropic API directly (uses Claude subscription credits).

    Args:
        model: Claude model name
        messages: Message list
        temperature: Temperature

    Returns:
        Dictionary with response data

    Raises:
        Exception: If call fails
    """
    import anthropic

    ant_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    # Extract user message
    user_prompt = ""
    system_prompt = None

    for msg in messages:
        if msg["role"] == "system":
            system_prompt = msg["content"]
        elif msg["role"] == "user":
            user_prompt = msg["content"]

    ant_messages = [{"role": "user", "content": user_prompt}]
    kwargs = {
        "model": model,
        "max_tokens": 4096,
        "messages": ant_messages,
        "temperature": temperature
    }
    if system_prompt:
        kwargs["system"] = system_prompt

    message = await ant_client.messages.create(**kwargs)
    content = message.content[0].text

    prompt_tok = message.usage.input_tokens
    comp_tok = message.usage.output_tokens

    return {
        "model": model,
        "content": content,
        "tokens_prompt": prompt_tok,
        "tokens_completion": comp_tok,
    }


# ============================================================================
# LEGACY FUNCTIONS (kept for backward compatibility)
# ============================================================================

async def _call_anthropic_direct_legacy(
    model: str,
    prompt: str,
    brand_id: str,
    context: str,
    action: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
) -> LLMResponse:
    """Legacy function for backward compatibility. Use call_llm instead."""
    import anthropic

    ant_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    ant_messages = [{"role": "user", "content": prompt}]
    kwargs = {
        "model": model,
        "max_tokens": 4096,
        "messages": ant_messages,
        "temperature": temperature
    }
    if system_prompt:
        kwargs["system"] = system_prompt

    message = await ant_client.messages.create(**kwargs)
    content = message.content[0].text

    prompt_tok = message.usage.input_tokens
    comp_tok = message.usage.output_tokens

    await track_cost(brand_id, context, model, action, prompt_tok, comp_tok)
    record_call()

    latency_ms = int((time.monotonic() - time.time()) * 1000)

    return LLMResponse(
        content=content,
        model_used=model,
        tokens_prompt=prompt_tok,
        tokens_completion=comp_tok,
        engine="anthropic",
        latency_ms=latency_ms
    )


async def _emergency_openrouter_fallback(
    task_type: str,
    prompt: str,
    system_prompt: Optional[str],
    brand_id: str,
    context: str,
    action: str,
    temperature: float,
) -> LLMResponse:
    """Emergency fallback to OpenRouter when Anthropic API fails.

    DEPRECATED: Use call_llm with proper degradation handling instead.
    """
    logger.warning("_emergency_openrouter_fallback is deprecated, use call_llm instead")

    # Map task to models
    if task_type == "reasoning":
        models = ["xiaomi/mimo-v2-flash:free", "openai/o3-mini"]
    elif task_type == "knowledge":
        models = ["arcee-ai/trinity-large:free", "google/gemini-2.5-flash"]
    elif task_type == "agentic":
        models = ["zhipu/glm-5.5-pro:free", "anthropic/claude-3.5-sonnet-20241022"]
    elif task_type == "coding":
        models = ["alibaba/qwen-3.5-max:free", "mistral/devstral-2:free"]
    else:
        models = ["google/gemma-4-150b:free", "anthropic/claude-3.5-haiku-20241022"]

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    last_error = None
    if not settings.openrouter_api_key:
        raise RuntimeError("Emergency fallback to OpenRouter requested but OPENROUTER_API_KEY not configured")

    async with httpx.AsyncClient(timeout=120) as client:
        for current_model in models:
            try:
                resp = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    json={
                        "model": current_model,
                        "messages": messages,
                        "temperature": temperature if "o3-mini" not in current_model else 1,
                    },
                    headers={
                        "Authorization": f"Bearer {settings.openrouter_api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "http://localhost:3000",
                        "X-Title": "Content Engine (Emergency Fallback)"
                    },
                )
                resp.raise_for_status()

                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                prompt_tok = usage.get("prompt_tokens", 0)
                comp_tok = usage.get("completion_tokens", 0)

                await track_cost(brand_id, context, current_model, action, prompt_tok, comp_tok)
                record_fallback(is_emergency=True)

                logger.warning("Emergency fallback successful: used %s instead of Anthropic API", current_model)

                latency_ms = int((time.monotonic() - time.time()) * 1000)

                return LLMResponse(
                    content=content,
                    model_used=current_model,
                    tokens_prompt=prompt_tok,
                    tokens_completion=comp_tok,
                    engine="openrouter",
                    latency_ms=latency_ms,
                    fallback_to=models[models.index(current_model) + 1] if models.index(current_model) + 1 < len(models) else None
                )
            except Exception as e:
                logger.warning("Emergency fallback model %s failed: %s", current_model, e)
                last_error = e
                continue

    raise RuntimeError(f"Emergency fallback failed - all OpenRouter models failed. Last error: {last_error}")


async def _log_fallback_attempt(
    brand_id: str,
    context: str,
    action: str,
    primary_model: str,
    fallback_reason: str,
    is_emergency: bool = False,
) -> None:
    """Log fallback attempt to database for monitoring and analytics."""
    try:
        db = get_db()
        db.table("llm_fallback_log").insert({
            "brand_id": brand_id,
            "context": context,
            "action": action,
            "primary_model": primary_model,
            "fallback_reason": fallback_reason,
            "is_emergency": is_emergency,
        }).execute()

        logger.info(
            "Fallback logged: brand=%s context=%s action=%s primary_model=%s emergency=%s",
            brand_id, context, action, primary_model, is_emergency
        )
    except Exception as e:
        # Don't fail the main pipeline if logging fails
        logger.error("Failed to log fallback attempt: %s", e)


async def _send_fallback_alert(
    model: str,
    error: str,
    is_emergency: bool = False,
) -> None:
    """Send alert about fallback occurrence."""
    try:
        from ..services.alerting import send_telegram_alert

        if is_emergency:
            message = (
                f"🚨 *EMERGENCY FALLBACK*\n\n"
                f"Anthropic API ({model}) failed and system fell back to OpenRouter.\n\n"
                f"**Error:** {error}\n\n"
                f"Check Anthropic API status and consider investigating the root cause."
            )
        else:
            message = (
                f"⚠️ *Fallback Detected*\n\n"
                f"Model {model} failed, system fell back to next option.\n\n"
                f"**Error:** {error}"
            )

        await send_telegram_alert(message)
        logger.info("Fallback alert sent: emergency=%s model=%s", is_emergency, model)
    except Exception as e:
        # Don't fail the main pipeline if alerting fails
        logger.error("Failed to send fallback alert: %s", e)


async def _record_heartbeat_safely(
    brand_id: str,
    llm_meta: Dict[str, Any],
    context: str,
    action: str,
    status: str,
) -> None:
    """Safely record heartbeat, never failing the main pipeline."""
    try:
        from .heartbeat import record_agent_heartbeat
        await record_agent_heartbeat(
            brand_id=brand_id,
            llm_meta=llm_meta,
            context=context,
            action=action,
            status=status,
        )
    except Exception as e:
        # Log but never fail
        logger.debug("Heartbeat recording failed (non-critical): %s", e)
