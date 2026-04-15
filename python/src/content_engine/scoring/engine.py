"""Scoring Engine — 6-parameter LLM evaluation using Claude Sonnet via OpenRouter or Anthropic."""

from __future__ import annotations

import json

import httpx

from ..config import settings
from ..db import get_db
from ..models import ScoreResult, ScoringRequest
from ..utils.cost_tracker import track_cost

SCORING_PROMPT = """You are a content scoring agent for an AI content engine.
Evaluate this research item on 5 parameters (0-10 scale).

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

Return ONLY a JSON object with these exact keys:
{{
  "applicability": <number 0-10>,
  "credibility": <number 0-10>,
  "alignment": <number 0-10>,
  "trend_prediction": <number 0-10>,
  "italy_relevance": <number 0-10>,
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

ANTI_HYPE_GATE_PROMPT = """You are an editorial filter for {brand_name}.
Your mission: discard clickbait content that doesn't provide immediate practical value.

## Brand Principles
{founder_principles}

## Gold Examples (VALID content - passes gate)
{gold_examples}

## Discard Examples (HYPE content - fails gate)
{discard_examples}

## Content to Evaluate
Title: {title}
Summary: {summary}
Source: {source_name}

Return ONLY JSON: {{"is_hype": true/false, "confidence": 0.0-1.0, "reason": "<one sentence>"}

Note: confidence < 0.7 means borderline - needs human review, not automatic rejection.
"""


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


async def check_anti_hype(item: dict, brand: dict) -> dict:
    """
    Evaluate if content is hype/clickbait using few-shot learning.

    Returns:
        {"is_hype": bool, "confidence": float, "reason": str}
    """
    brand_name = brand.get("name", "Brand")
    founder_principles = brand.get("founder_principles") or \
                        (brand.get("scoring_weights") or {}).get("founder_principles", [])
    gold_examples = brand.get("gold_examples") or []
    discard_examples = brand.get("discard_examples") or []

    prompt = ANTI_HYPE_GATE_PROMPT.format(
        brand_name=brand_name,
        founder_principles="\n".join(f"- {p}" for p in founder_principles),
        gold_examples="\n".join(f"- {ex}" for ex in gold_examples[:5]),  # Limit to 5 examples
        discard_examples="\n".join(f"- {ex}" for ex in discard_examples[:5]),  # Limit to 5 examples
        title=item.get("title", ""),
        summary=item.get("summary", ""),
        source_name=item.get("source_name", ""),
    )

    resp = await call_llm(
        prompt=prompt,
        brand_id=brand.get("id", ""),
        context="anti_hype_gate",
        action="check_anti_hype",
        task_type="fast"  # Fast model for binary classification
    )
    raw = resp.content

    # Parse JSON from response
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        text = text.rsplit("```", 1)[0]
    parsed = json.loads(text)

    return parsed

async def score_item(item: dict, brand: dict) -> tuple[ScoreResult, float, str]:
    # Bug 0.1 Fix: Load brand_data from DB to avoid NameError
    from ..db import get_db
    db = get_db()
    brand_resp = db.table("brands").select("*").eq("id", brand.get("id", "")).single().execute()
    brand_data = brand_resp.data if brand_resp.data else brand

    topics = brand_data.get("topics") or []
    principles = brand_data.get("founder_principles") or \
                 (brand_data.get("scoring_weights") or {}).get("founder_principles", [])

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

    # Inject feedback_bonus from database (not from LLM)
    feedback_bonus = brand_data.get("feedback_bonus", 5.0)
    parsed["feedback_bonus"] = feedback_bonus

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
    anti_hype_discarded = 0
    archived_duplicates = 0

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
                        archived_duplicates += 1
                        continue

            # 2. Anti-Hype Gate (before expensive LLM scoring)
            gate_result = await check_anti_hype(item, brand_data)
            if gate_result.get("is_hype") and gate_result.get("confidence", 0) >= 0.7:
                # Confirmed hype - reject immediately
                db.table("research_items").update({
                    "status": "rejected",
                    "metadata": {**item.get("metadata", {}),
                                 "rejection_reason": "anti_hype_gate",
                                 "gate_confidence": gate_result.get("confidence"),
                                 "gate_reason": gate_result.get("reason", "")}
                }).eq("id", item["id"]).execute()
                anti_hype_discarded += 1
                continue
            elif gate_result.get("is_hype") and gate_result.get("confidence", 0) < 0.7:
                # Borderline - needs human review
                db.table("research_items").update({
                    "status": "pending_review",
                    "metadata": {**item.get("metadata", {}),
                                 "review_reason": "borderline_hype",
                                 "gate_confidence": gate_result.get("confidence"),
                                 "gate_reason": gate_result.get("reason", "")}
                }).eq("id", item["id"]).execute()
                continue

            # 3. Score via LLM (only for items that pass the gate)
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
        "archived_duplicates": duplicate_count,
        "anti_hype_discarded": anti_hype_discarded,
    }
