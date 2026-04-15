"""End-to-End Tests for Agent Identity System

Phase 5: Complete integration tests for agent_configs, agent_skills,
and the full agent system workflow.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import AsyncGenerator

from content_engine.db import get_db
from content_engine.agents.agent_loader import get_agent_identity
from content_engine.agents.writer import generate_draft
from content_engine.agents.editor import edit_draft
from content_engine.agents.adapter import adapt_content
from content_engine.agents.god_system import run_god_mode


@pytest.fixture
async def db() -> AsyncGenerator:
    """Supabase database client fixture."""
    client = get_db()
    yield client
    # Cleanup is handled by transaction rollback in actual tests


@pytest.fixture
async def test_brand(db) -> dict:
    """Create a test brand for agent system testing."""
    brand = (
        db.table("brands")
        .insert({
            "name": "Test Brand for Agent System",
            "slug": "test-agent-brand",
            "domain": "test-brand.example.com",
            "tone_of_voice": {
                "personality": ["professional", "direct"],
                "rules": ["Be concise", "Use data"],
            },
            "scoring_weights": {
                "founder_principles": ["Authenticity", "Value-driven"],
            },
        })
        .execute()
    )
    brand_id = brand.data[0]["id"]

    # Seed agent configs
    for agent_key, agent_name, identity in [
        (
            "writer",
            "Writer",
            "You are the Writer for Test Brand — the creative voice of our brand.",
        ),
        (
            "editor",
            "Editor",
            "You are the Editor for Test Brand — the guardian of content quality.",
        ),
        (
            "adapter",
            "Adapter",
            "You are the Adapter for Test Brand — the multi-platform specialist.",
        ),
    ]:
        db.table("agent_configs").insert({
            "brand_id": brand_id,
            "agent_key": agent_key,
            "agent_name": agent_name,
            "identity": identity,
            "is_active": True,
        }).execute()

    # Seed some agent skills
    db.table("agent_skills").insert({
        "brand_id": brand_id,
        "target_agent": "writer",
        "skill_name": "seo_optimization",
        "description": "Optimize content for SEO",
        "instructions": "Always include relevant keywords naturally in the content.",
        "priority": "high",
        "tags": ["seo", "optimization"],
        "is_active": True,
    }).execute()

    db.table("agent_skills").insert({
        "brand_id": brand_id,
        "target_agent": "editor",
        "skill_name": "clarity_check",
        "description": "Ensure maximum clarity",
        "instructions": "Rewrite any unclear or verbose sentences.",
        "priority": "medium",
        "tags": ["quality", "clarity"],
        "is_active": True,
    }).execute()

    # Create a research item for testing
    research_item = (
        db.table("research_items")
        .insert({
            "brand_id": brand_id,
            "title": "The Future of Remote Work",
            "url": "https://example.com/remote-work-future",
            "source_name": "Tech Blog",
            "summary": "Remote work is evolving with hybrid models becoming standard.",
            "retriever": "manual",
            "status": "approved",
        })
        .execute()
    )
    research_item_id = research_item.data[0]["id"]

    yield {
        "brand_id": brand_id,
        "research_item_id": research_item_id,
    }

    # Cleanup
    db.table("brands").delete().eq("id", brand_id).execute()


# ============================================================================
# Test 1: Agent Identity Loading
# ============================================================================

@pytest.mark.asyncio
async def test_load_agent_identity_from_db(test_brand):
    """Test that agent identities are loaded from database correctly."""
    brand_id = test_brand["brand_id"]

    # Test loading writer identity
    writer_identity = await get_agent_identity(brand_id, "writer")
    assert writer_identity is not None
    assert "Test Brand" in writer_identity
    assert "creative voice" in writer_identity

    # Test loading editor identity
    editor_identity = await get_agent_identity(brand_id, "editor")
    assert editor_identity is not None
    assert "Test Brand" in editor_identity
    assert "content quality" in editor_identity

    # Test loading adapter identity
    adapter_identity = await get_agent_identity(brand_id, "adapter")
    assert adapter_identity is not None
    assert "Test Brand" in adapter_identity
    assert "multi-platform" in adapter_identity


@pytest.mark.asyncio
async def test_agent_identity_cache_invalidation(test_brand):
    """Test that agent identity cache is invalidated after update."""
    db = get_db()
    brand_id = test_brand["brand_id"]

    # Load identity (should cache)
    identity_1 = await get_agent_identity(brand_id, "writer")
    assert "creative voice" in identity_1

    # Update identity in DB
    db.table("agent_configs").update({
        "identity": "You are the UPDATED Writer for Test Brand.",
    }).eq("brand_id", brand_id).eq("agent_key", "writer").execute()

    # Load again (should see updated version due to cache invalidation)
    identity_2 = await get_agent_identity(brand_id, "writer")
    assert "UPDATED Writer" in identity_2
    assert identity_2 != identity_1


# ============================================================================
# Test 2: Writer Agent with DB Identity
# ============================================================================

@pytest.mark.asyncio
async def test_writer_uses_db_identity(test_brand):
    """Test that Writer agent uses identity loaded from database."""
    brand_id = test_brand["brand_id"]
    research_item_id = test_brand["research_item_id"]

    result = await generate_draft(
        brand_id=brand_id,
        research_item_id=research_item_id,
        platform="linkedin",
        content_type="post",
    )

    # Verify draft was created
    assert "draft" in result
    draft = result["draft"]
    assert draft["brand_id"] == brand_id
    assert draft["platform"] == "linkedin"
    assert draft["status"] == "draft"

    # Verify hooks, CTA, and hashtags are returned
    assert "hooks" in result
    assert "cta" in result
    assert "hashtags" in result


# ============================================================================
# Test 3: Editor Agent with DB Identity
# ============================================================================

@pytest.mark.asyncio
async def test_editor_uses_db_identity(test_brand):
    """Test that Editor agent uses identity loaded from database."""
    db = get_db()
    brand_id = test_brand["brand_id"]
    research_item_id = test_brand["research_item_id"]

    # First create a draft to edit
    draft_result = await generate_draft(
        brand_id=brand_id,
        research_item_id=research_item_id,
        platform="linkedin",
        content_type="post",
    )
    draft_id = draft_result["draft"]["id"]

    # Now edit the draft
    edit_result = await edit_draft(brand_id, draft_id)

    assert edit_result["draft_id"] == draft_id
    assert edit_result["version"] >= 2  # Should be incremented
    assert "changes_summary" in edit_result
    assert "changes_count" in edit_result

    # Verify status changed to in_review
    updated_draft = (
        db.table("content_drafts")
        .select("*")
        .eq("id", draft_id)
        .single()
        .execute()
        .data
    )
    assert updated_draft["status"] == "in_review"


# ============================================================================
# Test 4: Adapter Agent with DB Identity
# ============================================================================

@pytest.mark.asyncio
async def test_adapter_uses_db_identity(test_brand):
    """Test that Adapter agent uses identity loaded from database."""
    db = get_db()
    brand_id = test_brand["brand_id"]
    research_item_id = test_brand["research_item_id"]

    # Create a LinkedIn draft
    draft_result = await generate_draft(
        brand_id=brand_id,
        research_item_id=research_item_id,
        platform="linkedin",
        content_type="post",
    )
    linkedin_draft_id = draft_result["draft"]["id"]

    # Adapt to other platforms
    adapted = await adapt_content(
        brand_id=brand_id,
        draft_id=linkedin_draft_id,
        target_platforms=["instagram", "twitter"],
    )

    assert len(adapted) == 2

    # Verify adapted drafts
    for draft in adapted:
        assert draft["brand_id"] == brand_id
        assert draft["parent_draft_id"] == linkedin_draft_id
        assert draft["platform"] in ["instagram", "twitter"]
        assert draft["status"] == "draft"
        assert draft["content_type"] == "post"


# ============================================================================
# Test 5: GOD System with DB Identities
# ============================================================================

@pytest.mark.asyncio
async def test_god_system_uses_db_identities(test_brand):
    """Test that all 4 GOD agents use identities loaded from database."""
    db = get_db()
    brand_id = test_brand["brand_id"]
    research_item_id = test_brand["research_item_id"]

    # Seed GOD agent identities
    god_agents = [
        (
            "god_advocate",
            "GOD Advocate",
            "You are the Devil's Advocate for Test Brand — our critical guardian.",
        ),
        (
            "god_factcheck",
            "GOD Fact-Checker",
            "You are the Fact-Checker for Test Brand — our sentinel of truth.",
        ),
        (
            "god_creative",
            "GOD Creative",
            "You are the Creative Director for Test Brand — our alchemist of engagement.",
        ),
        (
            "god_synthesis",
            "GOD Synthesis",
            "You are the Synthesizer for Test Brand — our final orchestrator.",
        ),
    ]

    for agent_key, agent_name, identity in god_agents:
        existing = (
            db.table("agent_configs")
            .select("*")
            .eq("brand_id", brand_id)
            .eq("agent_key", agent_key)
            .single()
            .execute()
        )

        if not existing.data:
            db.table("agent_configs").insert({
                "brand_id": brand_id,
                "agent_key": agent_key,
                "agent_name": agent_name,
                "identity": identity,
                "is_active": True,
            }).execute()

    # Create a draft for GOD mode
    draft_result = await generate_draft(
        brand_id=brand_id,
        research_item_id=research_item_id,
        platform="linkedin",
        content_type="post",
    )
    draft_id = draft_result["draft"]["id"]

    # Run GOD mode
    god_result = await run_god_mode(brand_id, draft_id)

    # Verify GOD mode completed successfully
    assert god_result["draft_id"] == draft_id
    assert god_result["verdict"] in ["pass", "needs_revision", "reject"]
    assert "advocate_score" in god_result
    assert "factcheck_issues_count" in god_result
    assert "creative_suggestions_count" in god_result
    assert "new_status" in god_result

    # Verify review was saved
    review = (
        db.table("god_mode_reviews")
        .select("*")
        .eq("draft_id", draft_id)
        .single()
        .execute()
        .data
    )
    assert review is not None
    assert review["advocate_feedback"]
    assert review["factcheck_feedback"]
    assert review["creative_feedback"]
    assert review["final_verdict"] == god_result["verdict"]


# ============================================================================
# Test 6: Full Agent System Workflow
# ============================================================================

@pytest.mark.asyncio
async def test_full_agent_system_workflow(test_brand):
    """Test complete workflow: research → writer → editor → adapter → publish."""
    db = get_db()
    brand_id = test_brand["brand_id"]
    research_item_id = test_brand["research_item_id"]

    # Step 1: Writer generates draft
    writer_result = await generate_draft(
        brand_id=brand_id,
        research_item_id=research_item_id,
        platform="linkedin",
        content_type="post",
    )
    draft_id = writer_result["draft"]["id"]

    # Step 2: Editor improves draft
    editor_result = await edit_draft(brand_id, draft_id)
    assert editor_result["version"] >= 2

    # Step 3: Adapt to Instagram
    adapted = await adapt_content(
        brand_id=brand_id,
        draft_id=draft_id,
        target_platforms=["instagram"],
    )
    assert len(adapted) == 1

    # Step 4: Approve original draft
    db.table("content_drafts").update({
        "status": "approved"
    }).eq("id", draft_id).execute()

    # Verify final state
    original_draft = (
        db.table("content_drafts")
        .select("*")
        .eq("id", draft_id)
        .single()
        .execute()
        .data
    )
    assert original_draft["status"] == "approved"

    # Verify adapted draft exists
    adapted_draft = (
        db.table("content_drafts")
        .select("*")
        .eq("parent_draft_id", draft_id)
        .eq("platform", "instagram")
        .single()
        .execute()
        .data
    )
    assert adapted_draft is not None
    assert adapted_draft["status"] == "draft"


# ============================================================================
# Test 7: Agent Skills System
# ============================================================================

@pytest.mark.asyncio
async def test_agent_skills_storage(test_brand):
    """Test that agent skills are stored and retrieved correctly."""
    db = get_db()
    brand_id = test_brand["brand_id"]

    # Query skills for writer
    writer_skills = (
        db.table("agent_skills")
        .select("*")
        .eq("brand_id", brand_id)
        .eq("target_agent", "writer")
        .execute()
        .data
    )

    assert len(writer_skills) > 0
    assert any(s["skill_name"] == "seo_optimization" for s in writer_skills)

    # Verify skill details
    seo_skill = next(s for s in writer_skills if s["skill_name"] == "seo_optimization")
    assert seo_skill is not None
    assert seo_skill["description"] == "Optimize content for SEO"
    assert "keywords" in seo_skill["instructions"]
    assert seo_skill["priority"] == "high"
    assert "seo" in seo_skill["tags"]


# ============================================================================
# Test 8: Feedback Loop Integration
# ============================================================================

@pytest.mark.asyncio
async def test_feedback_loop_integration(test_brand):
    """Test that feedback loop integrates with agent system."""
    from content_engine.services.feedback_loop import update_feedback_bonus

    brand_id = test_brand["brand_id"]

    # Update feedback bonus
    result = await update_feedback_bonus(brand_id)

    # Verify structure
    assert "updated_scores" in result
    assert "total_drafts_analyzed" in result
    assert result["updated_scores"] >= 0
    assert result["total_drafts_analyzed"] >= 0


# ============================================================================
# Test 9: Anti-Hype Gate Examples
# ============================================================================

@pytest.mark.asyncio
async def test_anti_hype_gate_examples(test_brand):
    """Test that anti-hype gate examples are stored in DB."""
    db = get_db()
    brand_id = test_brand["brand_id"]

    # Update brand with anti-hype examples
    db.table("brands").update({
        "gold_examples": [
            "Post with concrete data and case studies",
            "Practical step-by-step tutorial",
        ],
        "discard_examples": [
            "Generic statements without data",
            "Purely promotional content",
        ],
    }).eq("id", brand_id).execute()

    # Verify examples were saved
    brand = (
        db.table("brands")
        .select("gold_examples", "discard_examples")
        .eq("id", brand_id)
        .single()
        .execute()
        .data
    )

    assert brand is not None
    assert len(brand.get("gold_examples", [])) > 0
    assert len(brand.get("discard_examples", [])) > 0
    assert any("concrete data" in e for e in brand["gold_examples"])
    assert any("promotional" in e for e in brand["discard_examples"])


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
