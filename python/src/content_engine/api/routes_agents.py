"""Agent Configuration API Routes — CRUD for agent_configs and agent_skills.

Phase 2: FastAPI endpoints for managing agent identities and skills.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

_logger = logging.getLogger("content_engine.api.agents")

from ..db import get_db, get_user_db
from ..api.routes import _get_brand_id, _get_client_db

router = APIRouter(prefix="/api/v1")


# ============================================================================
# Request/Response Models
# ============================================================================

class AgentConfigCreate(BaseModel):
    """Request model for creating an agent config."""
    agent_key: str  # e.g., "writer", "editor", "adapter", "god_advocate", "god_factcheck", "god_creative", "god_synthesis"
    agent_name: str  # e.g., "Writer", "Editor", "GOD Advocate"
    identity: str  # The full identity prompt for this agent
    brand_id: str | None = None  # Optional: if null, creates for current authenticated brand


class AgentConfigUpdate(BaseModel):
    """Request model for updating an agent config."""
    identity: str
    is_active: bool = True  # Allow activating/deactivating configs


class AgentSkillCreate(BaseModel):
    """Request model for creating an agent skill."""
    target_agent: str  # e.g., "writer", "editor", "adapter", "god_advocate", "god_factcheck", "god_creative", "god_synthesis"
    skill_name: str  # e.g., "seo_optimization", "brand_voice_match"
    description: str
    instructions: str  # The prompt that implements this skill (mapped to skill_prompt in API layer)
    priority: str = "medium"  # "high", "medium", "low"
    tags: list[str] = []  # Optional tags for categorization
    brand_id: str | None = None  # Optional: if null, creates for current authenticated brand


class AgentSkillUpdate(BaseModel):
    """Request model for updating an agent skill."""
    description: str
    instructions: str  # The prompt that implements this skill
    is_active: bool = True
    priority: str = "medium"
    tags: list[str] = []


# ============================================================================
# Agent Configs CRUD
# ============================================================================

@router.get("/agent-configs")
async def list_agent_configs(
    request: Request,
    agent_key: str | None = None,
    is_active: bool | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """List all agent configs for the authenticated brand."""
    brand_id = _get_brand_id(request)
    db = _get_client_db(request)

    query = (
        db.table("agent_configs")
        .select("*", count="exact")
        .eq("brand_id", brand_id)
        .order("created_at", desc=True)
    )

    if agent_key:
        query = query.eq("agent_key", agent_key)
    if is_active is not None:
        query = query.eq("is_active", is_active)

    query = query.range((page - 1) * per_page, page * per_page - 1)
    resp = query.execute()

    return {
        "success": True,
        "data": resp.data,
        "meta": {
            "page": page,
            "per_page": per_page,
            "total": resp.count or 0,
        },
    }


@router.post("/agent-configs")
async def create_agent_config(req: AgentConfigCreate, request: Request):
    """Create a new agent config."""
    brand_id = req.brand_id if req.brand_id else _get_brand_id(request)
    db = _get_client_db(request)

    # Validate agent_key is one of the expected values
    valid_agent_keys = {
        "writer", "editor", "adapter",
        "god_advocate", "god_factcheck", "god_creative", "god_synthesis"
    }
    if req.agent_key not in valid_agent_keys:
        raise HTTPException(
            400,
            f"Invalid agent_key '{req.agent_key}'. Valid: {sorted(valid_agent_keys)}"
        )

    # Check if config already exists for this agent_key/brand
    existing = (
        db.table("agent_configs")
        .select("*")
        .eq("brand_id", brand_id)
        .eq("agent_key", req.agent_key)
        .single()
        .execute()
    )

    if existing.data:
        # Update existing config instead of creating duplicate
        updated = (
            db.table("agent_configs")
            .update({
                "agent_name": req.agent_name,
                "identity": req.identity,
                "is_active": True,
            })
            .eq("id", existing.data["id"])
            .execute()
        )
        return {
            "success": True,
            "data": updated.data[0],
            "message": "Updated existing config for this agent_key",
        }

    # Create new config
    new_config = (
        db.table("agent_configs")
        .insert({
            "brand_id": brand_id,
            "agent_key": req.agent_key,
            "agent_name": req.agent_name,
            "identity": req.identity,
            "is_active": True,
        })
        .execute()
    )

    return {
        "success": True,
        "data": new_config.data[0],
    }


@router.get("/agent-configs/{config_id}")
async def get_agent_config(config_id: str, request: Request):
    """Get a specific agent config by ID."""
    brand_id = _get_brand_id(request)
    db = _get_client_db(request)

    config = (
        db.table("agent_configs")
        .select("*")
        .eq("id", config_id)
        .eq("brand_id", brand_id)
        .single()
        .execute()
    )

    if not config.data:
        raise HTTPException(404, "Agent config not found")

    return {
        "success": True,
        "data": config.data[0],
    }


@router.put("/agent-configs/{config_id}")
async def update_agent_config(config_id: str, req: AgentConfigUpdate, request: Request):
    """Update an existing agent config."""
    brand_id = _get_brand_id(request)
    db = _get_client_db(request)

    # Verify config exists and belongs to brand
    existing = (
        db.table("agent_configs")
        .select("*")
        .eq("id", config_id)
        .eq("brand_id", brand_id)
        .single()
        .execute()
    )

    if not existing.data:
        raise HTTPException(404, "Agent config not found")

    # Update config
    updated = (
        db.table("agent_configs")
        .update({
            "identity": req.identity,
            "is_active": req.is_active,
        })
        .eq("id", config_id)
        .execute()
    )

    return {
        "success": True,
        "data": updated.data[0],
    }


@router.delete("/agent-configs/{config_id}")
async def delete_agent_config(config_id: str, request: Request):
    """Delete an agent config."""
    brand_id = _get_brand_id(request)
    db = _get_client_db(request)

    # Verify config exists and belongs to brand
    existing = (
        db.table("agent_configs")
        .select("*")
        .eq("id", config_id)
        .eq("brand_id", brand_id)
        .single()
        .execute()
    )

    if not existing.data:
        raise HTTPException(404, "Agent config not found")

    # Delete config
    deleted = (
        db.table("agent_configs")
        .delete()
        .eq("id", config_id)
        .execute()
    )

    return {
        "success": True,
        "data": {"deleted_id": config_id},
    }


# ============================================================================
# Agent Skills CRUD
# ============================================================================

@router.get("/agent-skills")
async def list_agent_skills(
    request: Request,
    target_agent: str | None = None,
    is_active: bool | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """List all agent skills for the authenticated brand."""
    brand_id = _get_brand_id(request)
    db = _get_client_db(request)

    query = (
        db.table("agent_skills")
        .select("*", count="exact")
        .eq("brand_id", brand_id)
        .order("created_at", desc=True)
    )

    if target_agent:
        query = query.eq("target_agent", target_agent)
    if is_active is not None:
        query = query.eq("is_active", is_active)

    query = query.range((page - 1) * per_page, page * per_page - 1)
    resp = query.execute()

    return {
        "success": True,
        "data": resp.data,
        "meta": {
            "page": page,
            "per_page": per_page,
            "total": resp.count or 0,
        },
    }


@router.post("/agent-skills")
async def create_agent_skill(req: AgentSkillCreate, request: Request):
    """Create a new agent skill."""
    brand_id = req.brand_id if req.brand_id else _get_brand_id(request)
    db = _get_client_db(request)

    # Validate target_agent
    valid_agent_keys = {
        "writer", "editor", "adapter",
        "god_advocate", "god_factcheck", "god_creative", "god_synthesis"
    }
    if req.target_agent not in valid_agent_keys:
        raise HTTPException(
            400,
            f"Invalid target_agent '{req.target_agent}'. Valid: {sorted(valid_agent_keys)}"
        )

    # Validate priority
    if req.priority not in ("high", "medium", "low"):
        raise HTTPException(400, "priority must be 'high', 'medium', or 'low'")

    # Create new skill
    new_skill = (
        db.table("agent_skills")
        .insert({
            "brand_id": brand_id,
            "target_agent": req.target_agent,
            "skill_name": req.skill_name,
            "description": req.description,
            "instructions": req.instructions,
            "priority": req.priority,
            "tags": req.tags,
            "is_active": True,
        })
        .execute()
    )

    return {
        "success": True,
        "data": new_skill.data[0],
    }


@router.get("/agent-skills/{skill_id}")
async def get_agent_skill(skill_id: str, request: Request):
    """Get a specific agent skill by ID."""
    brand_id = _get_brand_id(request)
    db = _get_client_db(request)

    skill = (
        db.table("agent_skills")
        .select("*")
        .eq("id", skill_id)
        .eq("brand_id", brand_id)
        .single()
        .execute()
    )

    if not skill.data:
        raise HTTPException(404, "Agent skill not found")

    return {
        "success": True,
        "data": skill.data[0],
    }


@router.put("/agent-skills/{skill_id}")
async def update_agent_skill(skill_id: str, req: AgentSkillUpdate, request: Request):
    """Update an existing agent skill."""
    brand_id = _get_brand_id(request)
    db = _get_client_db(request)

    # Verify skill exists and belongs to brand
    existing = (
        db.table("agent_skills")
        .select("*")
        .eq("id", skill_id)
        .eq("brand_id", brand_id)
        .single()
        .execute()
    )

    if not existing.data:
        raise HTTPException(404, "Agent skill not found")

    # Validate priority
    if req.priority not in ("high", "medium", "low"):
        raise HTTPException(400, "priority must be 'high', 'medium', or 'low'")

    # Update skill
    updated = (
        db.table("agent_skills")
        .update({
            "description": req.description,
            "instructions": req.instructions,
            "priority": req.priority,
            "tags": req.tags,
            "is_active": req.is_active,
        })
        .eq("id", skill_id)
        .execute()
    )

    return {
        "success": True,
        "data": updated.data[0],
    }


@router.delete("/agent-skills/{skill_id}")
async def delete_agent_skill(skill_id: str, request: Request):
    """Delete an agent skill."""
    brand_id = _get_brand_id(request)
    db = _get_client_db(request)

    # Verify skill exists and belongs to brand
    existing = (
        db.table("agent_skills")
        .select("*")
        .eq("id", skill_id)
        .eq("brand_id", brand_id)
        .single()
        .execute()
    )

    if not existing.data:
        raise HTTPException(404, "Agent skill not found")

    # Delete skill
    deleted = (
        db.table("agent_skills")
        .delete()
        .eq("id", skill_id)
        .execute()
    )

    return {
        "success": True,
        "data": {"deleted_id": skill_id},
    }
