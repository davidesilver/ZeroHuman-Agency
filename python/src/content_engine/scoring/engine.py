"""Scoring Engine — 6-parameter LLM evaluation using Claude Sonnet via OpenRouter or Anthropic."""

from __future__ import annotations

import json

import httpx

from ..config import settings
from ..db import get_db
from ..models import ScoreResult, ScoringRequest

SCORING_PROMPT = """You are a content scoring agent for an AI content engine.
Evaluate this research item on 6 parameters (0-10 scale).

## Brand Context
Topics: {topics}
Principles: {principles}

## Item to Score
Title: {title}
Source: {source_name}
Summary: {summary}
URL: {url}

## Scoring Parameters

1. **applicability** (weight 25%): How immediately actionable is this content? Can the reader apply it on Monday morning?
2. **credibility** (weight 20%): Is the source/author credible? Does it cite data, case studies, or expert opinion?
3. **alignment** (weight 25%): How well does this align with the brand's topics and founder principles?
4. **trend_prediction** (weight 15%): Is this content about an emerging trend? Will it be relevant in 6 months?
5. **italy_relevance** (weight 10%): Is this applicable to the Italian market?
6. **feedback_bonus** (weight 5%): Default 5.0, adjusted by historical engagement data.

Return ONLY a JSON object with these exact keys:
{{
  "applicability": <number 0-10>,
  "credibility": <number 0-10>,
  "alignment": <number 0-10>,
  "trend_prediction": <number 0-10>,
  "italy_relevance": <number 0-10>,
  "feedback_bonus": 5.0,
  "reasoning": "<one sentence explaining the overall score>"
}}
"""

WEIGHTS = {
    "applicability": 0.25,
    "credibility": 0.20,
    "alignment": 0.25,
    "trend_prediction": 0.15,
    "italy_relevance": 0.10,
    "feedback_bonus": 0.05,
}


def _compute_final_score(result: ScoreResult) -> float:
    return round(
        result.applicability * WEIGHTS["applicability"]
        + result.credibility * WEIGHTS["credibility"]
        + result.alignment * WEIGHTS["alignment"]
        + result.trend_prediction * WEIGHTS["trend_prediction"]
        + result.italy_relevance * WEIGHTS["italy_relevance"]
        + result.feedback_bonus * WEIGHTS["feedback_bonus"],
        2,
    )


async def _call_llm(prompt: str) -> str:
    """Call Claude Sonnet via Anthropic API or OpenRouter."""
    if settings.anthropic_api_key:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        message = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text

    if settings.openrouter_api_key:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                json={
                    "model": settings.scoring_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 512,
                },
                headers={
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    raise RuntimeError("No AI API key configured (set ANTHROPIC_API_KEY or OPENROUTER_API_KEY)")


async def score_item(item: dict, brand: dict) -> tuple[ScoreResult, float]:
    topics = brand.get("topics") or []
    principles = (brand.get("scoring_weights") or {}).get("founder_principles", [])

    prompt = SCORING_PROMPT.format(
        topics=", ".join(topics),
        principles="\n".join(f"- {p}" for p in principles),
        title=item.get("title", ""),
        source_name=item.get("source_name", ""),
        summary=item.get("summary", ""),
        url=item.get("url", ""),
    )

    raw = await _call_llm(prompt)

    # Parse JSON from response (handle markdown code blocks)
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        text = text.rsplit("```", 1)[0]
    parsed = json.loads(text)
    result = ScoreResult(**parsed)
    final = _compute_final_score(result)
    return result, final


async def run_scoring(brand_id: str, request: ScoringRequest) -> dict:
    db = get_db()

    # Load brand config
    brand = db.table("brands").select("*").eq("id", brand_id).single().execute()
    brand_data = brand.data

    # Get items to score
    query = db.table("research_items").select("*").eq("brand_id", brand_id).eq("status", "new")
    if request.run_id:
        query = query.eq("run_id", request.run_id)
    if request.item_ids:
        query = query.in_("id", request.item_ids)
    items_resp = query.execute()
    items = items_resp.data

    scored = 0
    approved = 0
    rejected = 0
    errors: list[str] = []

    for item in items:
        try:
            result, final_score = await score_item(item, brand_data)

            # Save score (columns match DB schema)
            db.table("scores").insert({
                "research_item_id": item["id"],
                "applicability": result.applicability,
                "credibility": result.credibility,
                "alignment": result.alignment,
                "trend_prediction": result.trend_prediction,
                "italy_relevance": result.italy_relevance,
                "feedback_bonus": result.feedback_bonus,
                "final_score": final_score,
                "model_used": "claude-sonnet-4",
            }).execute()

            # Auto-approve/reject
            new_status = "scored"
            if final_score >= settings.auto_approve_threshold:
                new_status = "approved"
                approved += 1
            elif final_score <= settings.auto_reject_threshold:
                new_status = "rejected"
                rejected += 1

            db.table("research_items").update({
                "status": new_status,
            }).eq("id", item["id"]).execute()

            scored += 1

        except Exception as e:
            errors.append(f"Item {item['id']}: {e}")

    return {
        "scored": scored,
        "approved": approved,
        "rejected": rejected,
        "errors": errors,
        "total_items": len(items),
    }
