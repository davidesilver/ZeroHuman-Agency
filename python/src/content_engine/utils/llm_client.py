"""Centralized LLM Client routing via OpenRouter and Anthropic."""

from __future__ import annotations

import httpx
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from ..config import settings
from ..db import get_db
from .cost_tracker import track_cost
from .fallback_monitor import record_call, record_fallback

class LLMResponse(BaseModel):
    content: str
    model_used: str
    tokens_prompt: int
    tokens_completion: int
    engine: str = "unknown"          # "anthropic" | "openrouter"
    latency_ms: Optional[int] = None
    fallback_to: Optional[str] = None

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
    Call the best LLM depending on the requested capability, tracking costs automatically.

    Model Selection Strategy:
    - If settings.use_claude_subscription = TRUE: Uses Claude via Anthropic API (your subscription)
    - If settings.use_claude_subscription = FALSE: Uses OpenRouter free models (default)

    `task_type` semantic routing:
    - reasoning: Sonnet (Claude sub) or Xiaomi MiMo (OpenRouter free)
    - creative / language: Haiku (Claude sub) or Gemma 4 (OpenRouter free)
    - knowledge: Haiku (Claude sub) or Arcee Trinity (OpenRouter free)
    - agentic: Sonnet (Claude sub) or Zhipu GLM 5.5 (OpenRouter free)
    - coding: Sonnet (Claude sub) or Qwen 3.5 (OpenRouter free)
    """
    import logging
    import time
    import asyncio

    logger = logging.getLogger("content_engine.llm")
    start_time = time.monotonic()

    # Check if user wants to use Claude subscription
    use_claude = settings.use_claude_subscription and settings.anthropic_api_key

    if use_claude:
        # Use Claude via Anthropic API (subscription credits)
        logger.debug("Using Claude subscription (Anthropic API) for task_type=%s", task_type)

        if task_type == "reasoning":
            model = "claude-3-5-sonnet-20241022"
        elif task_type in ["agentic", "coding"]:
            model = "claude-3-5-sonnet-20241022"
        else:  # creative, language, knowledge, default
            model = "claude-3-5-haiku-20241022"

        # Call Anthropic API directly with emergency fallback
        try:
            return await _call_anthropic_direct(
                model=model,
                prompt=prompt,
                system_prompt=system_prompt,
                brand_id=brand_id,
                context=context,
                action=action,
                temperature=temperature,
            )
        except Exception as e:
            logger.error("Anthropic API failed for %s: %s. Triggering emergency fallback to OpenRouter...", model, e)

            # Log emergency fallback
            await _log_fallback_attempt(
                brand_id=brand_id,
                context=context,
                action=action,
                primary_model=model,
                fallback_reason=str(e),
                is_emergency=True
            )

            # Send emergency alert
            await _send_fallback_alert(
                model=model,
                error=str(e),
                is_emergency=True
            )

            # Emergency fallback: try OpenRouter
            return await _emergency_openrouter_fallback(
                task_type=task_type,
                prompt=prompt,
                system_prompt=system_prompt,
                brand_id=brand_id,
                context=context,
                action=action,
                temperature=temperature,
            )

    # Use OpenRouter free models (default behavior)
    logger.debug("Using OpenRouter free models for task_type=%s", task_type)

    # Capability Router (OpenRouter)
    if task_type == "reasoning":
        models = ["xiaomi/mimo-v2-flash:free", "openai/o3-mini"]
    elif task_type == "knowledge":
        models = ["arcee-ai/trinity-large:free", "google/gemini-2.5-flash"]
    elif task_type == "agentic":
        models = ["zhipu/glm-5.5-pro:free", "anthropic/claude-3.5-sonnet-20241022"]
    elif task_type == "coding":
        models = ["alibaba/qwen-3.5-max:free", "mistral/devstral-2:free"]
    else:  # creative, language or default
        models = ["google/gemma-4-150b:free", "anthropic/claude-3-5-haiku-20241022"]

    # If the user overrode the default scoring model in config, use it as fallback
    if settings.scoring_model not in models:
        models.append(settings.scoring_model)

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    messages.append({"role": "user", "content": prompt})
    
    # 1. OpenRouter Fallback Chain
    last_error = None
    if settings.openrouter_api_key:
        async with httpx.AsyncClient(timeout=120) as client:
            for i, current_model in enumerate(models):
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
                            "X-Title": "Content Engine"
                        },
                    )
                    resp.raise_for_status()

                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    usage = data.get("usage", {})
                    prompt_tok = usage.get("prompt_tokens", 0)
                    comp_tok = usage.get("completion_tokens", 0)

                    # Log fallback if this wasn't the first model
                    if i > 0:
                        await _log_fallback_attempt(
                            brand_id=brand_id,
                            context=context,
                            action=action,
                            primary_model=models[0],  # First model that failed
                            fallback_reason=f"OpenRouter model failed, fell back to {current_model}",
                            is_emergency=False
                        )
                        record_fallback(is_emergency=False)  # Track normal fallback

                    # Track EXACT model that responded successfully
                    await track_cost(brand_id, context, current_model, action, prompt_tok, comp_tok)
                    record_call()  # Track successful call

                    # Calculate latency
                    latency_ms = int((time.monotonic() - start_time) * 1000)

                    # Record heartbeat (fire-and-forget, never fails)
                    llm_meta = {
                        "model_used": current_model,
                        "engine": "openrouter",
                        "latency_ms": latency_ms,
                        "tokens_prompt": prompt_tok,
                        "tokens_completion": comp_tok,
                    }
                    asyncio.create_task(
                        _record_heartbeat_safely(brand_id, llm_meta, context, action, "healthy")
                    )

                    return LLMResponse(
                        content=content,
                        model_used=current_model,
                        tokens_prompt=prompt_tok,
                        tokens_completion=comp_tok,
                        engine="openrouter",
                        latency_ms=latency_ms,
                        fallback_to=models[i+1] if i+1 < len(models) else None
                    )
                except Exception as e:
                    logger.warning("OpenRouter failed for model %s: %s. Trying fallback...", current_model, e)
                    last_error = e
                    continue

    # 2. Native Anthropic SDK Fallback (if specifically an Anthropic model or no OpenRouter key)
    # We only get here if ALL OpenRouter models failed or if there was no OpenRouter key.
    if settings.anthropic_api_key:
        ant_model = "claude-3-5-sonnet-20241022" # sensible generic fallback
        for m in models:
            if "anthropic" in m or "claude" in m:
                ant_model = "claude-3-5-sonnet-20241022" if "sonnet" in m else "claude-3-5-haiku-20241022"
                break

        try:
            # Log fallback from OpenRouter to Anthropic
            await _log_fallback_attempt(
                brand_id=brand_id,
                context=context,
                action=action,
                primary_model=models[-1] if models else "unknown",
                fallback_reason=f"All OpenRouter models failed, fell back to Anthropic {ant_model}",
                is_emergency=False
            )
            record_fallback(is_emergency=False)  # Track normal fallback

            return await _call_anthropic_direct(
                model=ant_model,
                prompt=prompt,
                system_prompt=system_prompt,
                brand_id=brand_id,
                context=context,
                action=action,
                temperature=temperature,
            )
        except Exception as e:
            logger.error("Anthropic Native SDK fallback failed: %s", e)
            last_error = e

    raise RuntimeError(f"All LLM routing options failed. Last error: {last_error}")


async def _call_anthropic_direct(
    model: str,
    prompt: str,
    brand_id: str,
    context: str,
    action: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
) -> LLMResponse:
    """Call Anthropic API directly (uses Claude subscription credits).

    This function is used when:
    1. use_claude_subscription = TRUE (uses subscription credits)
    2. OpenRouter fails and Anthropic API is available as fallback

    Args:
        model: Claude model name (e.g., "claude-3-5-sonnet-20241022")
        prompt: The user prompt
        brand_id: Brand ID for cost tracking
        context: Context label for cost tracking
        action: Action label for cost tracking
        system_prompt: Optional system prompt
        temperature: Temperature for generation

    Returns:
        LLMResponse with content and metadata
    """
    import anthropic
    import logging

    logger = logging.getLogger("content_engine.llm")

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
    record_call()  # Track successful call

    # Calculate latency
    latency_ms = int((time.monotonic() - start_time) * 1000)

    # Record heartbeat (fire-and-forget, never fails)
    llm_meta = {
        "model_used": model,
        "engine": "anthropic",
        "latency_ms": latency_ms,
        "tokens_prompt": prompt_tok,
        "tokens_completion": comp_tok,
    }
    asyncio.create_task(
        _record_heartbeat_safely(brand_id, llm_meta, context, action, "healthy")
    )

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

    Uses free models first (Gemma 4) then paid fallback (Haiku).
    This is a recovery mechanism, not a default path.

    Args:
        task_type: Type of task being performed
        prompt: The user prompt
        system_prompt: Optional system prompt
        brand_id: Brand ID for cost tracking
        context: Context label for cost tracking
        action: Action label for cost tracking
        temperature: Temperature for generation

    Returns:
        LLMResponse from OpenRouter

    Raises:
        RuntimeError: If all OpenRouter attempts fail
    """
    import logging
    logger = logging.getLogger("content_engine.llm")

    # Emergency fallback models: free first, then paid as last resort
    if task_type == "reasoning":
        models = ["xiaomi/mimo-v2-flash:free", "openai/o3-mini"]
    elif task_type == "knowledge":
        models = ["arcee-ai/trinity-large:free", "google/gemini-2.5-flash"]
    elif task_type == "agentic":
        models = ["zhipu/glm-5.5-pro:free", "anthropic/claude-3.5-sonnet-20241022"]
    elif task_type == "coding":
        models = ["alibaba/qwen-3.5-max:free", "mistral/devstral-2:free"]
    else:  # creative, language, default
        models = ["google/gemma-4-150b:free", "anthropic/claude-3-5-haiku-20241022"]

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

                # Track cost and log successful fallback
                await track_cost(brand_id, context, current_model, action, prompt_tok, comp_tok)
                record_fallback(is_emergency=True)  # Track emergency fallback

                logger.warning("Emergency fallback successful: used %s instead of Anthropic API", current_model)

                # Calculate latency
                latency_ms = int((time.monotonic() - start_time) * 1000)

                # Record heartbeat with fallback status
                llm_meta = {
                    "model_used": current_model,
                    "engine": "openrouter",
                    "latency_ms": latency_ms,
                    "tokens_prompt": prompt_tok,
                    "tokens_completion": comp_tok,
                    "fallback_to": models[models.index(current_model) + 1] if models.index(current_model) + 1 < len(models) else None,
                }
                asyncio.create_task(
                    _record_heartbeat_safely(brand_id, llm_meta, context, action, "degraded")
                )

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
    """Log fallback attempt to database for monitoring and analytics.

    Args:
        brand_id: Brand ID
        context: Context label (e.g., "humanizer_pass1")
        action: Action label (e.g., "initial_humanization")
        primary_model: Model that failed
        fallback_reason: Error message or reason for fallback
        is_emergency: Whether this was an emergency fallback (Anthropic API down)
    """
    import logging
    logger = logging.getLogger("content_engine.llm.fallback")

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
    """Send alert about fallback occurrence.

    Args:
        model: Model that failed
        error: Error message
        is_emergency: Whether this was an emergency fallback
    """
    import logging
    logger = logging.getLogger("content_engine.llm.fallback")

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
    """Safely record heartbeat, never failing the main pipeline.

    This is a fire-and-forget wrapper around record_agent_heartbeat that
    ensures any errors in heartbeat recording don't impact the main LLM pipeline.

    Args:
        brand_id: Brand ID
        llm_meta: LLM metadata dictionary
        context: Context label
        action: Action label
        status: Status string
    """
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
