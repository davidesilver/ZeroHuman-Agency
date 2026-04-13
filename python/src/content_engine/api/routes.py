from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from pydantic import BaseModel

from ..db import get_db
from ..models import TriggerRequest, ScoringRequest
from ..orchestrator.research import run_research
from ..orchestrator.content import generate_content, generate_and_god
from ..agents.god_system import run_god_mode
from ..agents.adapter import adapt_content
from ..agents.writing_lab import create_session, vote_round
from ..scoring.engine import run_scoring
from ..services.newsletter_delivery import send_newsletter, preview_newsletter
from ..services.social_publisher import publish_to_linkedin, schedule_post
from ..services.feedback_loop import record_social_metrics, update_feedback_bonus
from ..services.scheduler import daily_research_pipeline, publish_scheduled_posts

router = APIRouter(prefix="/api")

BRAND_ID = "b6e639ac-33e7-402b-b928-c98af55eec47"  # Vest — will be dynamic later


@router.post("/research/trigger")
async def trigger_research(req: TriggerRequest | None = None):
    if req is None:
        req = TriggerRequest()
    result = await run_research(BRAND_ID, req)
    return {"success": True, "data": result.model_dump()}


@router.get("/research/runs")
async def list_runs(
    status: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    db = get_db()
    query = (
        db.table("research_runs")
        .select("*", count="exact")
        .eq("brand_id", BRAND_ID)
        .order("created_at", desc=True)
    )
    if status:
        query = query.eq("status", status)
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


@router.get("/research/items")
async def list_items(
    status: str | None = None,
    run_id: str | None = None,
    retriever: str | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    db = get_db()
    query = (
        db.table("research_items")
        .select("*, scores(*)", count="exact")
        .eq("brand_id", BRAND_ID)
    )
    if status:
        query = query.eq("status", status)
    if run_id:
        query = query.eq("run_id", run_id)
    if retriever:
        query = query.eq("retriever", retriever)
    query = query.order(sort_by, desc=(sort_order == "desc"))
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


@router.patch("/research/items/{item_id}/status")
async def update_item_status(item_id: str, body: dict):
    new_status = body.get("status")
    if new_status not in ("new", "scored", "approved", "rejected", "archived"):
        raise HTTPException(400, "Invalid status")
    db = get_db()
    resp = (
        db.table("research_items")
        .update({"status": new_status})
        .eq("id", item_id)
        .eq("brand_id", BRAND_ID)
        .execute()
    )
    if not resp.data:
        raise HTTPException(404, "Item not found")
    return {"success": True, "data": resp.data[0]}


@router.post("/scoring/run")
async def trigger_scoring(req: ScoringRequest | None = None):
    if req is None:
        req = ScoringRequest()
    result = await run_scoring(BRAND_ID, req)
    return {"success": True, "data": result}


class GenerateRequest(BaseModel):
    research_item_id: str
    platform: str = "linkedin"
    content_type: str = "post"
    run_god: bool = False


class GodModeRequest(BaseModel):
    pass


class AdaptRequest(BaseModel):
    target_platforms: list[str]


@router.post("/content/generate")
async def api_generate_content(req: GenerateRequest):
    if req.run_god:
        result = await generate_and_god(
            BRAND_ID, req.research_item_id, req.platform, req.content_type,
        )
    else:
        result = await generate_content(
            BRAND_ID, req.research_item_id, req.platform, req.content_type,
        )
    return {"success": True, "data": result}


@router.post("/content/drafts/{draft_id}/god-mode")
async def api_god_mode(draft_id: str):
    result = await run_god_mode(BRAND_ID, draft_id)
    return {"success": True, "data": result}


@router.post("/content/drafts/{draft_id}/adapt")
async def api_adapt_content(draft_id: str, req: AdaptRequest):
    results = await adapt_content(BRAND_ID, draft_id, req.target_platforms)
    return {"success": True, "data": results}


@router.get("/content/drafts")
async def list_drafts(
    status: str | None = None,
    content_type: str | None = None,
    platform: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    db = get_db()
    query = (
        db.table("content_drafts")
        .select("*", count="exact")
        .eq("brand_id", BRAND_ID)
        .order("created_at", desc=True)
    )
    if status:
        query = query.eq("status", status)
    if content_type:
        query = query.eq("content_type", content_type)
    if platform:
        query = query.eq("platform", platform)
    query = query.range((page - 1) * per_page, page * per_page - 1)
    resp = query.execute()
    return {
        "success": True,
        "data": resp.data,
        "meta": {"page": page, "per_page": per_page, "total": resp.count or 0},
    }


@router.patch("/content/drafts/{draft_id}")
async def update_draft(draft_id: str, body: dict):
    allowed = {"status", "title", "body", "scheduled_at"}
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(400, "No valid fields to update")
    db = get_db()
    resp = (
        db.table("content_drafts")
        .update(updates)
        .eq("id", draft_id)
        .eq("brand_id", BRAND_ID)
        .execute()
    )
    if not resp.data:
        raise HTTPException(404, "Draft not found")
    return {"success": True, "data": resp.data[0]}


@router.get("/research/stats")
async def research_stats():
    db = get_db()
    items = (
        db.table("research_items")
        .select("status", count="exact")
        .eq("brand_id", BRAND_ID)
        .execute()
    )
    # Count by status
    all_items = (
        db.table("research_items")
        .select("id, status")
        .eq("brand_id", BRAND_ID)
        .execute()
    )
    counts = {"total": 0, "pending": 0, "approved": 0, "rejected": 0, "archived": 0, "top_pick": 0}
    for item in all_items.data:
        counts["total"] += 1
        s = item.get("status", "pending")
        if s in counts:
            counts[s] += 1
    return {"success": True, "data": counts}


# ── Writing Lab ──────────────────────────────────────────────────────────────


class WritingLabCreateRequest(BaseModel):
    topic: str
    content_type: str = "newsletter"


class VoteRequest(BaseModel):
    winner: str  # "champion" | "challenger" | "draw"
    feedback: str | None = None


@router.post("/writing-lab/sessions")
async def api_create_session(req: WritingLabCreateRequest):
    result = await create_session(BRAND_ID, req.topic, req.content_type)
    return {"success": True, "data": result}


@router.get("/writing-lab/sessions")
async def api_list_sessions(
    status: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    db = get_db()
    query = (
        db.table("writing_lab_sessions")
        .select("*", count="exact")
        .eq("brand_id", BRAND_ID)
        .order("created_at", desc=True)
    )
    if status:
        query = query.eq("status", status)
    query = query.range((page - 1) * per_page, page * per_page - 1)
    resp = query.execute()
    return {
        "success": True,
        "data": resp.data,
        "meta": {"page": page, "per_page": per_page, "total": resp.count or 0},
    }


@router.get("/writing-lab/sessions/{session_id}")
async def api_get_session(session_id: str):
    db = get_db()
    session = db.table("writing_lab_sessions").select("*").eq("id", session_id).single().execute().data
    if not session:
        raise HTTPException(404, "Session not found")
    rounds = (
        db.table("writing_lab_rounds")
        .select("*")
        .eq("session_id", session_id)
        .order("round_number", desc=False)
        .execute()
        .data
    )
    return {"success": True, "data": {"session": session, "rounds": rounds or []}}


@router.post("/writing-lab/sessions/{session_id}/vote")
async def api_vote(session_id: str, req: VoteRequest):
    result = await vote_round(BRAND_ID, session_id, req.winner, req.feedback)
    return {"success": True, "data": result}


# ── Newsletter Delivery ─────────────────────────────────────────────────────


class SendNewsletterRequest(BaseModel):
    newsletter_id: str
    recipients: list[str]


@router.post("/newsletter/send")
async def api_send_newsletter(req: SendNewsletterRequest):
    result = await send_newsletter(BRAND_ID, req.newsletter_id, req.recipients)
    return {"success": True, "data": result}


@router.get("/newsletter/{newsletter_id}/preview")
async def api_preview_newsletter(newsletter_id: str):
    html = await preview_newsletter(BRAND_ID, newsletter_id)
    return {"success": True, "data": {"html": html}}


# ── Social Publishing ────────────────────────────────────────────────────────


class PublishRequest(BaseModel):
    draft_id: str
    access_token: str


class ScheduleRequest(BaseModel):
    draft_id: str
    scheduled_at: str


@router.post("/social/publish/linkedin")
async def api_publish_linkedin(req: PublishRequest):
    result = await publish_to_linkedin(BRAND_ID, req.draft_id, req.access_token)
    return {"success": True, "data": result}


@router.post("/social/schedule")
async def api_schedule_post(req: ScheduleRequest):
    result = await schedule_post(BRAND_ID, req.draft_id, req.scheduled_at)
    return {"success": True, "data": result}


# ── Analytics & Feedback Loop ────────────────────────────────────────────────


class MetricsRequest(BaseModel):
    draft_id: str
    platform: str
    impressions: int = 0
    clicks: int = 0
    likes: int = 0
    shares: int = 0
    comments: int = 0
    saves: int = 0


@router.post("/analytics/metrics")
async def api_record_metrics(req: MetricsRequest):
    result = await record_social_metrics(
        req.draft_id, req.platform,
        impressions=req.impressions, clicks=req.clicks,
        likes=req.likes, shares=req.shares,
        comments=req.comments, saves=req.saves,
    )
    return {"success": True, "data": result}


@router.post("/analytics/feedback-loop")
async def api_feedback_loop():
    result = await update_feedback_bonus(BRAND_ID)
    return {"success": True, "data": result}


# ── Scheduler ────────────────────────────────────────────────────────────────


@router.post("/scheduler/daily-pipeline")
async def api_daily_pipeline():
    result = await daily_research_pipeline(BRAND_ID)
    return {"success": True, "data": result}


@router.post("/scheduler/publish-scheduled")
async def api_publish_scheduled():
    result = await publish_scheduled_posts(BRAND_ID)
    return {"success": True, "data": result}
