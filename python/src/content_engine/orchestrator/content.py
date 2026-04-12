"""Content Orchestrator — chains Writer -> Editor -> saves draft, runs GOD mode."""

from __future__ import annotations

from ..agents.writer import generate_draft
from ..agents.editor import edit_draft
from ..agents.adapter import adapt_content
from ..agents.god_system import run_god_mode


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
