"""Centralized LLM Client routing via OpenRouter and Anthropic."""

from __future__ import annotations

import httpx
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from ..config import settings
from .cost_tracker import track_cost

class LLMResponse(BaseModel):
    content: str
    model_used: str
    tokens_prompt: int
    tokens_completion: int

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
    
    `task_type` semantic routing (Primary OpenRouter Free + Fallbacks):
    - reasoning: Xiaomi MiMo (309B) -> o3-mini
    - creative / language: Gemma 4 (150B) -> Claude 3.5 Haiku
    - knowledge: Arcee Trinity (400B) -> Gemini 2.5 Flash
    - agentic: Zhipu GLM 5.5 Pro (260B) -> Claude 3.5 Sonnet
    - coding: Qwen 3.5 Max (180B) -> Mistral Devstral 2
    """
    import logging
    logger = logging.getLogger("content_engine.llm")
    
    # Capability Router
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
                            "X-Title": "Content Engine"
                        },
                    )
                    resp.raise_for_status()
                    
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    usage = data.get("usage", {})
                    prompt_tok = usage.get("prompt_tokens", 0)
                    comp_tok = usage.get("completion_tokens", 0)
                    
                    # Track EXACT model that responded successfully
                    await track_cost(brand_id, context, current_model, action, prompt_tok, comp_tok)
                    return LLMResponse(content=content, model_used=current_model, tokens_prompt=prompt_tok, tokens_completion=comp_tok)
                except Exception as e:
                    logger.warning("OpenRouter failed for model %s: %s. Trying fallback...", current_model, e)
                    last_error = e
                    continue

    # 2. Native Anthropic SDK Fallback (if specifically an Anthropic model or no OpenRouter key)
    # We only get here if ALL OpenRouter models failed or if there was no OpenRouter key.
    # We will pick the first model in the list that is Anthropic (if any), or default to sonnet.
    if settings.anthropic_api_key:
        ant_model = "claude-3-5-sonnet-20241022" # sensible generic fallback
        for m in models:
            if "anthropic" in m or "claude" in m:
                ant_model = "claude-3-5-sonnet-20241022" if "sonnet" in m else "claude-3-5-haiku-20241022"
                break
                
        import anthropic
        ant_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        
        ant_messages = [{"role": "user", "content": prompt}]
        kwargs = {
            "model": ant_model,
            "max_tokens": 4096,
            "messages": ant_messages,
            "temperature": temperature
        }
        if system_prompt:
            kwargs["system"] = system_prompt
            
        try:
            message = await ant_client.messages.create(**kwargs)
            content = message.content[0].text
            
            prompt_tok = message.usage.input_tokens
            comp_tok = message.usage.output_tokens
            
            await track_cost(brand_id, context, ant_model, action, prompt_tok, comp_tok)
            return LLMResponse(content=content, model_used=ant_model, tokens_prompt=prompt_tok, tokens_completion=comp_tok)
        except Exception as e:
            logger.error("Anthropic Native SDK also failed: %s", e)
            last_error = e

    raise RuntimeError(f"All LLM routing options failed. Last error: {last_error}")
