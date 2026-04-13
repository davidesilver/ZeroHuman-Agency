"""Scoring Engine — 6-parameter LLM evaluation using Claude Sonnet via OpenRouter or Anthropic."""

from __future__ import annotations

import json

import httpx

from ..config import settings
from ..db import get_db
from ..models import ScoreResult, ScoringRequest
from ..utils.cost_tracker import track_cost

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


from ..utils.llm_client import call_llm

async def score_item(item: dict, brand: dict) -> tuple[ScoreResult, float, str]:
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

    resp = await call_llm(
        prompt=prompt,
        brand_id=brand.get("id", ""),
        context="scoring_agent",
        action="score_item",
        task_type="reasoning"  # Reasoning makes more sense for precise scoring
    )
    raw = resp.content
    model_used = resp.model_used

    # Parse JSON from response (handle markdown code blocks)
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        text = text.rsplit("```", 1)[0]
    parsed = json.loads(text)
    result = ScoreResult(**parsed)
    final = _compute_final_score(result)
    return result, final, model_used


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

    # NOTE: the loop below is intentionally sequential (not asyncio.gather) 
    # to prevent race conditions during semantic deduplication of parallel items.
    for item in items:
        try:
            from ..utils.embedding_client import generate_embedding
            
            # 1. Semantic Deduplication
            text_to_embed = f"{item.get('title', '')} {item.get('summary', '')}".strip()
            if text_to_embed:
                emb = await generate_embedding(text_to_embed, brand_id)
                if emb:
                    # Update embedding in DB
                    db.table("research_items").update({"embedding": emb}).eq("id", item["id"]).execute()
                    
                    # Check for duplicates using RPC
                    dups_resp = db.rpc("find_semantic_duplicates", {
                        "p_brand_id": brand_id,
                        "p_embedding": emb,
                        "p_threshold": settings.dedup_threshold,
                        "p_limit": 1
                    }).execute()
                    
                    dups = dups_resp.data
                    if dups and len(dups) > 0 and dups[0]["id"] != item["id"]:
                        # Duplicate found! Skip scoring and mark as archived
                        db.table("research_items").update({
                            "status": "archived",
                            "metadata": {"semantic_duplicate_of": dups[0]["id"], "similarity": dups[0]["similarity"]}
                        }).eq("id", item["id"]).execute()
                        continue

            # 2. Score via LLM
            result, final_score, model_used = await score_item(item, brand_data)

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
                "model_used": model_used,
            }).execute()

            # Auto-approve/reject
            new_status = "scored"
            
            # Fetch brand-specific thresholds or fallback to globals
            brand_approve_thresh = brand_data.get("auto_approve_threshold")
            if brand_approve_thresh is None:
                brand_approve_thresh = settings.auto_approve_threshold
                
            brand_reject_thresh = brand_data.get("auto_reject_threshold")
            if brand_reject_thresh is None:
                brand_reject_thresh = settings.auto_reject_threshold

            if final_score >= brand_approve_thresh:
                new_status = "approved"
                approved += 1
            elif final_score <= brand_reject_thresh:
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
