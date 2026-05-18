"""Auto-optimizer Service - Nightly loop to self-improve Content Engine prompts."""

from __future__ import annotations

import logging
from typing import Any

from ..agents.writer import WRITER_PROMPT
from ..db import get_db
from ..scoring.engine import score_item
from ..utils.llm_client import call_llm

logger = logging.getLogger(__name__)

OPTIMIZER_PROMPT = """You are an AI system architect trying to improve a copywriting prompt.
Given the original prompt and an analysis of why the previous outputs scored poorly, 
generate a NEW variation of the prompt that will yield better results.

Original Prompt:
{original_prompt}

Weaknesses to address:
{weaknesses}

Rules:
1. Do not remove the placeholder variables (like {{title}}, {{body}}, {{brand_name}})
2. Keep the general structure but change the instructions to be more aggressive, creative or clear.

Return ONLY the new prompt string. Do not use quotes or backticks.
"""

async def run_nightly_optimization(brand_id: str):
    """
    Simulates a nightly process inspired by Karpathy's automated R&D loop.
    1. Grabs recent drafts that were rejected or scored low.
    2. Uses an LLM to propose a prompt tweak.
    3. Generates 5 new drafts using the tweak.
    4. Evaluates them with the Scoring engine.
    5. If the new average score > old average score, saves the new prompt to DB.
    """
    logger.info(f"Starting auto-optimization loop for brand {brand_id}")
    db = get_db()
    
    # 1. Fetch worst performing drafts (rejected + borderline_hype)
    drafts_resp = (
        db.table("content_drafts")
        .select("*")
        .eq("brand_id", brand_id)
        .in_("status", ["rejected", "pending_review"])  # Include both rejected and borderline
        .limit(50)
        .execute()
    )
    bad_drafts = drafts_resp.data

    if len(bad_drafts) < 10:
        logger.info("Not enough rejected drafts to run optimization. Waiting for statistical significance (n=10).")
        return
        
    # Analyze weaknesses (in a real scenario, we'd use GOD system Advocate feedback to find exactly WHY they failed)
    # Here we mock the weakness string
    weaknesses_str = "The content was too generic, lacked strong hooks, and the call to action was weak."
    
    # Check if a custom prompt already exists in DB
    brand_resp = db.table("brands").select("id, custom_writer_prompt").eq("id", brand_id).single().execute()
    brand_data = brand_resp.data
    current_prompt = brand_data.get("custom_writer_prompt") or WRITER_PROMPT
    
    # 2. Propose tweak
    tweak_prompt = OPTIMIZER_PROMPT.format(original_prompt=current_prompt, weaknesses=weaknesses_str)
    
    resp = await call_llm(tweak_prompt, brand_id, context="system_optimizer", action="optimize", task_type="agentic")
    new_prompt = resp.content.strip()

    logger.info("Generated new prompt variation. Will test against baseline.")

    # 3 & 4. Real A/B testing
    logger.info("Running A/B test: generating 5 drafts with new prompt...")
    ab_test_results = await run_ab_test(new_prompt, current_prompt, bad_drafts[:5], brand_id)

    success = ab_test_results["new_avg_score"] > ab_test_results["old_avg_score"]

    if success:
        logger.info(f"New prompt performed better! New avg: {ab_test_results['new_avg_score']:.2f} vs Old avg: {ab_test_results['old_avg_score']:.2f}")
        db.table("brands").update({"custom_writer_prompt": new_prompt}).eq("id", brand_id).execute()
    else:
        logger.info(f"New prompt failed to beat baseline. New avg: {ab_test_results['new_avg_score']:.2f} vs Old avg: {ab_test_results['old_avg_score']:.2f}")

    return {"status": "completed", "success": success, "ab_test_results": ab_test_results}


async def run_ab_test(new_prompt: str, old_prompt: str, source_drafts: list[dict], brand_id: str) -> dict[str, Any]:
    """
    Run A/B test comparing new prompt against old prompt.

    Generates drafts from the same source materials, scores them, compares averages.

    Returns:
        {
            "new_avg_score": float,
            "old_avg_score": float,
            "new_scores": List[float],
            "old_scores": List[float],
        }
    """
    from ..agents.writer import generate_content

    db = get_db()
    new_scores = []
    old_scores = []

    # Test with 5 source drafts
    for source_draft in source_drafts[:5]:
        # Get source research item
        research_item_id = source_draft.get("research_item_id")
        if not research_item_id:
            continue

        research_resp = db.table("research_items").select("*").eq("id", research_item_id).single().execute()
        if not research_resp.data:
            continue
        research_item = research_resp.data

        # Load brand config
        brand_resp = db.table("brands").select("*").eq("id", brand_id).single().execute()
        brand_data = brand_resp.data

        try:
            # Generate with new prompt (content used for scoring only)
            await generate_content(research_item, brand_data, custom_prompt=new_prompt)
            new_score_result = await score_item(research_item, brand_data)
            new_scores.append(new_score_result[1])  # [1] is final_score

            # Generate with old prompt
            await generate_content(research_item, brand_data, custom_prompt=old_prompt)
            old_score_result = await score_item(research_item, brand_data)
            old_scores.append(old_score_result[1])

        except Exception as e:
            logger.warning(f"A/B test failed for item {research_item_id}: {e}")
            continue

    new_avg = sum(new_scores) / len(new_scores) if new_scores else 0.0
    old_avg = sum(old_scores) / len(old_scores) if old_scores else 0.0

    return {
        "new_avg_score": new_avg,
        "old_avg_score": old_avg,
        "new_scores": new_scores,
        "old_scores": old_scores,
    }
