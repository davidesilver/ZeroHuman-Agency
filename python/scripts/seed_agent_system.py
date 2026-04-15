"""Seed Script for Agent Identity System

Phase 5: Populates initial agent_configs and agent_skills for existing brands.
Run this script after applying migrations 005 and 008.

Usage:
    python -m scripts.seed_agent_system
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from content_engine.db import get_db


async def seed_agent_configs_for_brands() -> dict:
    """Seed agent_configs for all existing brands."""
    db = get_db()

    # Get all brands
    brands_resp = db.table("brands").select("id, name").execute()
    brands = brands_resp.data or []

    if not brands:
        print("❌ No brands found in database")
        return {"status": "skipped", "brands_count": 0}

    # Define default agent configs
    default_configs = [
        (
            "writer",
            "Writer",
            "You are the Writer for {brand_name} — the creative voice and founder in digital communication. Your goal is to transform approved research into compelling, original content that embodies our brand's personality.",
        ),
        (
            "editor",
            "Editor",
            "You are the Editor for {brand_name} — the guardian of quality and coherence. Your goal is to refine drafts into polished, error-free content while preserving the core message.",
        ),
        (
            "adapter",
            "Adapter",
            "You are the Adapter for {brand_name} — the multi-platform specialist. Your goal is to seamlessly adapt content across different platforms while maintaining brand voice.",
        ),
        (
            "god_advocate",
            "GOD Advocate",
            "You are the Devil's Advocate of the GOD System for {brand_name} — the intellectual counterweight protecting our brand from mediocrity. Your goal is to meticulously scrutinize content, identify logical flaws, and prevent reputational risks.",
        ),
        (
            "god_factcheck",
            "GOD Fact-Checker",
            "You are the Fact-Checker of the GOD System for {brand_name} — the sentinel of factual truth. Your goal is to scrutinize every statement, identify unverifiable claims, and prevent factual errors.",
        ),
        (
            "god_creative",
            "GOD Creative",
            "You are the Creative Director of the GOD System for {brand_name} — the alchemist who transforms 'correct' content into 'memorable' content. Your goal is to find hidden opportunities and elevate the narrative.",
        ),
        (
            "god_synthesis",
            "GOD Synthesis",
            "You are the Synthesizer of the GOD System for {brand_name} — the orchestrator who merges contrasting perspectives into a flawless final piece. Your goal is to balance rigorous logic, creativity, and accuracy.",
        ),
    ]

    configs_created = 0
    configs_updated = 0
    errors = []

    for brand in brands:
        brand_id = brand["id"]
        brand_name = brand["name"]

        print(f"\n📋 Seeding agent configs for brand: {brand_name}")

        for agent_key, agent_name, identity_template in default_configs:
            try:
                # Format identity with brand name
                identity = identity_template.format(brand_name=brand_name)

                # Check if config already exists
                existing = (
                    db.table("agent_configs")
                    .select("*")
                    .eq("brand_id", brand_id)
                    .eq("agent_key", agent_key)
                    .single()
                    .execute()
                )

                if existing.data:
                    # Update existing config
                    db.table("agent_configs").update({
                        "agent_name": agent_name,
                        "identity": identity,
                    }).eq("id", existing.data["id"]).execute()
                    configs_updated += 1
                    print(f"  ✓ Updated: {agent_name}")
                else:
                    # Create new config
                    db.table("agent_configs").insert({
                        "brand_id": brand_id,
                        "agent_key": agent_key,
                        "agent_name": agent_name,
                        "identity": identity,
                        "is_active": True,
                    }).execute()
                    configs_created += 1
                    print(f"  ✓ Created: {agent_name}")

            except Exception as e:
                error_msg = f"Failed to seed {agent_key} for brand {brand_id}: {e}"
                errors.append(error_msg)
                print(f"  ❌ Error: {error_msg}")

    return {
        "status": "success",
        "brands_processed": len(brands),
        "configs_created": configs_created,
        "configs_updated": configs_updated,
        "errors": errors,
    }


async def seed_agent_skills_for_brands() -> dict:
    """Seed agent_skills for all existing brands."""
    db = get_db()

    # Get all brands
    brands_resp = db.table("brands").select("id, name").execute()
    brands = brands_resp.data or []

    if not brands:
        print("❌ No brands found in database")
        return {"status": "skipped", "brands_count": 0}

    # Define default agent skills
    default_skills = [
        # Writer skills
        {
            "target_agent": "writer",
            "skill_name": "seo_optimization",
            "description": "Optimize content for search engines",
            "instructions": "Naturally incorporate relevant keywords and phrases without keyword stuffing. Focus on semantic SEO by using language that matches user search intent.",
            "priority": "high",
            "tags": ["seo", "optimization", "search"],
        },
        {
            "target_agent": "writer",
            "skill_name": "brand_voice_consistency",
            "description": "Maintain consistent brand voice across all content",
            "instructions": "Always write in the brand's established tone: direct, practical, and engaging. Use consistent vocabulary and sentence structure that aligns with the brand personality.",
            "priority": "high",
            "tags": ["brand", "consistency", "voice"],
        },
        {
            "target_agent": "writer",
            "skill_name": "engagement_hooks",
            "description": "Create magnetic hooks that grab attention",
            "instructions": "Start with a surprising insight, provocative question, or bold statement. The first sentence must compel the reader to continue. Avoid generic openers.",
            "priority": "medium",
            "tags": ["engagement", "hooks", "writing"],
        },
        # Editor skills
        {
            "target_agent": "editor",
            "skill_name": "clarity_enhancement",
            "description": "Ensure maximum clarity and readability",
            "instructions": "Rewrite any unclear, verbose, or convoluted sentences. Use short paragraphs and simple, direct language. Remove jargon unless it adds specific value.",
            "priority": "high",
            "tags": ["clarity", "readability", "editing"],
        },
        {
            "target_agent": "editor",
            "skill_name": "cta_sharpening",
            "description": "Strengthen calls to action",
            "instructions": "Make the CTA specific, actionable, and compelling. Replace weak CTAs like 'learn more' with specific directions that tell the user exactly what they'll get.",
            "priority": "medium",
            "tags": ["cta", "conversion", "editing"],
        },
        {
            "target_agent": "editor",
            "skill_name": "fact_verification",
            "description": "Verify all factual claims",
            "instructions": "Check that all statistics, claims, and data points are plausible. Flag any unsupported assertions for review. Accuracy is non-negotiable.",
            "priority": "high",
            "tags": ["facts", "accuracy", "verification"],
        },
        # Adapter skills
        {
            "target_agent": "adapter",
            "skill_name": "platform_compliance",
            "description": "Follow platform-specific rules perfectly",
            "instructions": "Adapt to the target platform's character limits, format requirements, and engagement patterns. Each platform has unique conventions—respect them.",
            "priority": "high",
            "tags": ["platform", "compliance", "adaptation"],
        },
        {
            "target_agent": "adapter",
            "skill_name": "emoji_optimization",
            "description": "Use emojis strategically for each platform",
            "instructions": "Adjust emoji usage per platform: moderate on LinkedIn, higher on Instagram, minimal on X (as bullet points). Never overuse—every emoji must add value.",
            "priority": "low",
            "tags": ["emojis", "platform", "formatting"],
        },
        {
            "target_agent": "adapter",
            "skill_name": "hashtag_strategy",
            "description": "Apply optimal hashtag strategy per platform",
            "instructions": "Tailor hashtags: 3-5 on LinkedIn, 15-20 on Instagram, 1-2 on Facebook, 3-5 on TikTok. Mix broad and specific tags naturally.",
            "priority": "medium",
            "tags": ["hashtags", "platform", "discovery"],
        },
    ]

    skills_created = 0
    errors = []

    for brand in brands:
        brand_id = brand["id"]
        brand_name = brand["name"]

        print(f"\n🎯 Seeding agent skills for brand: {brand_name}")

        for skill_def in default_skills:
            try:
                # Check if skill already exists
                existing = (
                    db.table("agent_skills")
                    .select("*")
                    .eq("brand_id", brand_id)
                    .eq("skill_name", skill_def["skill_name"])
                    .single()
                    .execute()
                )

                if existing.data:
                    print(f"  ⊙ Skipped (exists): {skill_def['skill_name']}")
                    continue

                # Create new skill
                db.table("agent_skills").insert({
                    "brand_id": brand_id,
                    "target_agent": skill_def["target_agent"],
                    "skill_name": skill_def["skill_name"],
                    "description": skill_def["description"],
                    "instructions": skill_def["instructions"],
                    "priority": skill_def["priority"],
                    "tags": skill_def["tags"],
                    "is_active": True,
                }).execute()
                skills_created += 1
                print(f"  ✓ Created: {skill_def['skill_name']}")

            except Exception as e:
                error_msg = (
                    f"Failed to seed {skill_def['skill_name']} for brand {brand_id}: {e}"
                )
                errors.append(error_msg)
                print(f"  ❌ Error: {error_msg}")

    return {
        "status": "success",
        "brands_processed": len(brands),
        "skills_created": skills_created,
        "errors": errors,
    }


async def seed_anti_hype_examples() -> dict:
    """Seed anti-hype gate examples for brands."""
    db = get_db()

    # Get all brands
    brands_resp = db.table("brands").select("id, name").execute()
    brands = brands_resp.data or []

    if not brands:
        print("❌ No brands found in database")
        return {"status": "skipped", "brands_count": 0}

    # Default anti-hype examples
    gold_examples = [
        "Post with concrete data points and case studies",
        "Practical step-by-step tutorial with real outcomes",
        "Analysis backed by verifiable statistics",
        "Original insight based on first-hand experience",
        "Balanced perspective acknowledging trade-offs",
    ]

    discard_examples = [
        "Generic statements without specific examples",
        "Purely promotional content with no value",
        "Overly hype-filled language without substance",
        "Unverified claims or fake precision",
        "Circular arguments or tautologies",
    ]

    brands_updated = 0
    errors = []

    for brand in brands:
        brand_id = brand["id"]
        brand_name = brand["name"]

        try:
            db.table("brands").update({
                "gold_examples": gold_examples,
                "discard_examples": discard_examples,
            }).eq("id", brand_id).execute()
            brands_updated += 1
            print(f"✓ Seeded anti-hype examples for: {brand_name}")

        except Exception as e:
            error_msg = f"Failed to seed anti-hype examples for brand {brand_id}: {e}"
            errors.append(error_msg)
            print(f"❌ Error: {error_msg}")

    return {
        "status": "success",
        "brands_processed": len(brands),
        "brands_updated": brands_updated,
        "errors": errors,
    }


async def main():
    """Run all seed operations."""
    print("=" * 60)
    print("🌱 Seeding Agent Identity System")
    print("=" * 60)

    # Step 1: Seed agent configs
    print("\n📦 Step 1: Seeding Agent Identities...")
    configs_result = await seed_agent_configs_for_brands()
    print(f"\n✓ Agent Identities: {configs_result['configs_created']} created, {configs_result['configs_updated']} updated")

    if configs_result["errors"]:
        print(f"\n⚠️ Errors ({len(configs_result['errors'])}):")
        for error in configs_result["errors"][:5]:  # Show first 5 errors
            print(f"  - {error}")

    # Step 2: Seed agent skills
    print("\n🎯 Step 2: Seeding Agent Skills...")
    skills_result = await seed_agent_skills_for_brands()
    print(f"\n✓ Agent Skills: {skills_result['skills_created']} created")

    if skills_result["errors"]:
        print(f"\n⚠️ Errors ({len(skills_result['errors'])}):")
        for error in skills_result["errors"][:5]:  # Show first 5 errors
            print(f"  - {error}")

    # Step 3: Seed anti-hype examples
    print("\n🛡️ Step 3: Seeding Anti-Hype Gate Examples...")
    anti_hype_result = await seed_anti_hype_examples()
    print(f"\n✓ Anti-Hype Examples: {anti_hype_result['brands_updated']} brands updated")

    if anti_hype_result["errors"]:
        print(f"\n⚠️ Errors ({len(anti_hype_result['errors'])}):")
        for error in anti_hype_result["errors"][:5]:  # Show first 5 errors
            print(f"  - {error}")

    # Summary
    print("\n" + "=" * 60)
    print("📊 Seeding Complete!")
    print("=" * 60)
    print(f"\n✅ Agent Identities: {configs_result['configs_created']} created, {configs_result['configs_updated']} updated")
    print(f"✅ Agent Skills: {skills_result['skills_created']} created")
    print(f"✅ Anti-Hype Examples: {anti_hype_result['brands_updated']} brands updated")

    total_errors = (
        len(configs_result.get("errors", []))
        + len(skills_result.get("errors", []))
        + len(anti_hype_result.get("errors", []))
    )

    if total_errors > 0:
        print(f"\n⚠️ Total Errors: {total_errors}")
        print("  Review logs above for details.")
    else:
        print("\n✅ All seeding operations completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
