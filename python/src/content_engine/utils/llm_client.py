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
    # Depending on task complexity, we route to the right model
    complexity: str = "normal", 
    temperature: float = 0.7,
) -> LLMResponse:
    """
    Call the best LLM depending on the requested complexity, tracking costs automatically.
    
    `complexity` levels:
    - simple: GPT-4o-mini or Claude 3.5 Haiku (fast, cheap text tasks)
    - normal: Claude 3.5 Sonnet (balanced, the default)
    - high: o3-mini or Claude 3.5 Opus (deep reasoning, planning, complex reviews)
    """
    
    # Model Router
    if complexity == "high":
        model = "openai/o3-mini"
    elif complexity == "simple":
        model = "anthropic/claude-3-5-haiku-20241022"
    else:
        model = settings.scoring_model

    messages = []
    if system_prompt:
        # o3-mini doesn't support 'system' role, it requires 'developer' or 'user'. 
        # For openrouter, we can try to use 'system' and OpenRouter translates it,
        # but to be completely safe we'll just format it properly
        messages.append({"role": "system", "content": system_prompt})
        
    messages.append({"role": "user", "content": prompt})
    
    # Execute through OpenRouter if available, else fallback to standard Anthropic client if requested Anthropic
    if settings.openrouter_api_key:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature if "o3-mini" not in model else 1, # o3-mini uses fixed temp 1
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
            
            await track_cost(brand_id, context, model, action, prompt_tok, comp_tok)
            return LLMResponse(content=content, model_used=model, tokens_prompt=prompt_tok, tokens_completion=comp_tok)

    elif settings.anthropic_api_key and "anthropic" in model:
        import anthropic
        ant_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        
        ant_messages = [{"role": "user", "content": prompt}]
        
        # Anthropic uses a specific system parameter
        kwargs = {
            "model": "claude-3-5-sonnet-20241022" if "sonnet" in model else "claude-3-5-haiku-20241022",
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
        
        await track_cost(brand_id, context, kwargs["model"], action, prompt_tok, comp_tok)
        return LLMResponse(content=content, model_used=kwargs["model"], tokens_prompt=prompt_tok, tokens_completion=comp_tok)

    raise RuntimeError("No AI API key configured or fallback not applicable for requested model.")
