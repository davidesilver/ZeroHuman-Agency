"""Brevo email automations API (Phase 6).

Endpoints:
  GET  /email-marketing/automations       — list automations for active brand
  POST /email-marketing/automations       — create automation from template
  PATCH /email-marketing/automations/:id  — update copy or toggle active/inactive
"""

from __future__ import annotations

import copy
import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..db import get_db

_logger = logging.getLogger("content_engine.automations")

router = APIRouter(prefix="/email-marketing/automations", tags=["automations"])

# ── Predefined step templates ──────────────────────────────────────────────

_TEMPLATES: dict[str, list[dict]] = {
    "welcome": [
        {
            "step": 1,
            "delay_days": 0,
            "subject": "Welcome! Here's how to get started",
            "html_content": "<p>Welcome aboard! We're thrilled to have you.</p>",
        },
        {
            "step": 2,
            "delay_days": 2,
            "subject": "Your first steps",
            "html_content": "<p>Here are a few things you can do right now to get value fast.</p>",
        },
        {
            "step": 3,
            "delay_days": 7,
            "subject": "How's it going?",
            "html_content": "<p>We'd love to hear how your first week went.</p>",
        },
    ],
    "nurture": [
        {
            "step": 1,
            "delay_days": 0,
            "subject": "Great content just for you",
            "html_content": "<p>Based on your interests, we've curated this for you.</p>",
        },
        {
            "step": 2,
            "delay_days": 3,
            "subject": "Did you check this out?",
            "html_content": "<p>In case you missed it — here's something valuable.</p>",
        },
        {
            "step": 3,
            "delay_days": 7,
            "subject": "Case study: see what others are doing",
            "html_content": "<p>Here's how others in your space are succeeding.</p>",
        },
        {
            "step": 4,
            "delay_days": 14,
            "subject": "Your weekly digest",
            "html_content": "<p>Here's a roundup of the best content from this week.</p>",
        },
        {
            "step": 5,
            "delay_days": 21,
            "subject": "A personal note from our team",
            "html_content": "<p>We wanted to reach out personally to see how things are going.</p>",
        },
    ],
    "win-back": [
        {
            "step": 1,
            "delay_days": 30,
            "subject": "We miss you!",
            "html_content": "<p>It's been a while. Here's what you've missed.</p>",
        },
        {
            "step": 2,
            "delay_days": 37,
            "subject": "Last chance — a special offer just for you",
            "html_content": "<p>We'd love to have you back. Here's an exclusive offer.</p>",
        },
    ],
}


def _brand_id(request: Request) -> str:
    brand_id = getattr(request.state, "brand_id", None)
    if not brand_id:
        raise HTTPException(401, "Not authenticated")
    return brand_id


class CreateAutomationRequest(BaseModel):
    template_key: str
    name: str | None = None


class UpdateAutomationRequest(BaseModel):
    status: str | None = None
    steps: list[dict] | None = None
    name: str | None = None


@router.get("")
async def list_automations(request: Request):
    brand_id = _brand_id(request)
    result = (
        get_db()
        .from_("email_automations")
        .select("id, name, template_key, status, steps, brevo_workflow_id, created_at, updated_at")
        .eq("brand_id", brand_id)
        .order("template_key")
        .execute()
    )
    return result.data or []


@router.post("", status_code=201)
async def create_automation(body: CreateAutomationRequest, request: Request):
    brand_id = _brand_id(request)

    if body.template_key not in _TEMPLATES:
        raise HTTPException(400, f"template_key must be one of: {', '.join(_TEMPLATES)}")

    steps = copy.deepcopy(_TEMPLATES[body.template_key])
    name = body.name or body.template_key.replace("-", " ").title() + " Automation"

    result = (
        get_db()
        .from_("email_automations")
        .upsert({
            "brand_id": brand_id,
            "name": name,
            "template_key": body.template_key,
            "status": "inactive",
            "steps": steps,
        }, on_conflict="brand_id,template_key")
        .execute()
    )

    return result.data[0] if result.data else {}


@router.patch("/{automation_id}")
async def update_automation(automation_id: str, body: UpdateAutomationRequest, request: Request):
    brand_id = _brand_id(request)

    update: dict = {}
    if body.status is not None:
        if body.status not in ("active", "inactive"):
            raise HTTPException(400, "status must be 'active' or 'inactive'")
        update["status"] = body.status
    if body.steps is not None:
        update["steps"] = body.steps
    if body.name is not None:
        update["name"] = body.name.strip()

    if not update:
        raise HTTPException(400, "Nothing to update")

    result = (
        get_db()
        .from_("email_automations")
        .update(update)
        .eq("id", automation_id)
        .eq("brand_id", brand_id)
        .execute()
    )
    return result.data[0] if result.data else {}
