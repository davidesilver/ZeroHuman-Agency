"""Content Orchestrator — chains Writer -> Editor -> Humanizer -> saves draft, runs GOD mode."""

from __future__ import annotations

import logging

from ..agents.editor import edit_draft
from ..agents.god_system import run_god_mode
from ..agents.humanizer import humanize_draft
from ..agents.writer import generate_draft
from ..db import get_db

logger = logging.getLogger("content_engine.orchestrator")


async def generate_content(
    brand_id: str,
    research_item_id: str,
    platform: str = "linkedin",
    content_type: str = "post",
) -> dict:
    """Full pipeline: Writer -> Editor -> draft ready for review."""
    # Step 1: Generate initial draft
    writer_result = await generate_draft(brand_id, research_item_id, platform, content_type)
    draft_id = writer_result["draft"]["id"]

    # Step 2: Edit and improve
    editor_result = await edit_draft(brand_id, draft_id)

    return {
        "draft_id": draft_id,
        "version": editor_result["version"],
        "changes_summary": editor_result["changes_summary"],
        "hooks": writer_result["hooks"],
        "cta": writer_result["cta"],
        "hashtags": writer_result["hashtags"],
    }


async def generate_and_god(
    brand_id: str,
    research_item_id: str,
    platform: str = "linkedin",
    content_type: str = "post",
) -> dict:
    """Full pipeline with GOD mode: Writer -> Editor -> GOD."""
    result = await generate_content(brand_id, research_item_id, platform, content_type)
    god_result = await run_god_mode(brand_id, result["draft_id"])
    return {**result, "god": god_result}


async def generate_and_god_and_humanize(
    brand_id: str,
    research_item_id: str,
    platform: str = "linkedin",
    content_type: str = "post",
) -> dict:
    """Full pipeline with GOD mode and Humanizer: Writer -> Editor -> GOD -> Humanizer.

    Humanizer runs only if:
    1. Brand has `use_humanizer = TRUE`
    2. Platform is in brand's `humanizer_channels`
    3. GOD mode verdict is "pass"

    Uses FREE models by default (Gemma 4 → Haiku).
    """
    # Run standard pipeline
    result = await generate_and_god(brand_id, research_item_id, platform, content_type)
    draft_id = result["draft_id"]

    # Check if humanizer should run
    god_verdict = result.get("god", {}).get("verdict", "needs_revision")
    if god_verdict != "pass":
        logger.info("GOD mode verdict is '%s', skipping humanizer for draft %s", god_verdict, draft_id)
        return {**result, "humanizer": {"status": "skipped", "reason": f"god_verdict_{god_verdict}"}}

    # Check brand settings
    db = get_db()
    brand = db.table("brands").select("*").eq("id", brand_id).single().execute()
    brand_data = brand.data

    if not brand_data.get("use_humanizer", False):
        logger.info("Humanizer disabled for brand %s, skipping draft %s", brand_id, draft_id)
        return {**result, "humanizer": {"status": "skipped", "reason": "disabled"}}

    # Check platform
    enabled_channels = brand_data.get("humanizer_channels", ["linkedin", "blog"])
    if platform not in enabled_channels:
        logger.info("Humanizer not enabled for platform %s, skipping draft %s", platform, draft_id)
        return {**result, "humanizer": {"status": "skipped", "reason": "platform_not_enabled"}}

    # Run humanizer
    try:
        model_override = brand_data.get("humanizer_model_override")
        humanizer_result = await humanize_draft(
            brand_id=brand_id,
            draft_id=draft_id,
            model_override=model_override,
        )
        logger.info("Humanizer completed for draft %s", draft_id)
        return {**result, "humanizer": {"status": "completed", **humanizer_result}}
    except Exception as e:
        logger.error("Humanizer failed for draft %s: %s", draft_id, e)
        return {**result, "humanizer": {"status": "failed", "error": str(e)}}
