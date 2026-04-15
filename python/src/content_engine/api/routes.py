from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request

_logger = logging.getLogger("content_engine.api")

# C-06: Scheduler secret — set SCHEDULER_SECRET env var in production
_SCHEDULER_SECRET = os.environ.get("SCHEDULER_SECRET", "")


async def _require_scheduler_secret(request: Request) -> None:
    """C-06: Guard scheduler endpoints with a shared secret."""
    if not _SCHEDULER_SECRET:
        # Allow in local dev if env var is not set (but log a warning)
        _logger.warning("SCHEDULER_SECRET not set — scheduler endpoints are unprotected!")
        return
    provided = request.headers.get("X-Scheduler-Secret", "")
    if not provided or provided != _SCHEDULER_SECRET:
        raise HTTPException(403, "Invalid or missing scheduler secret")

from pydantic import BaseModel

from ..db import get_db, get_user_db
from ..models import TriggerRequest, ScoringRequest
from ..orchestrator.research import run_research
from ..orchestrator.content import generate_content, generate_and_god, generate_and_god_and_humanize
from ..agents.god_system import run_god_mode
from ..agents.adapter import adapt_content
from ..agents.writing_lab import create_session, vote_round
from ..scoring.engine import run_scoring
from ..services.newsletter_delivery import send_newsletter, preview_newsletter
from ..services.social_publisher import publish_to_postiz, schedule_post
from ..services.feedback_loop import record_social_metrics, update_feedback_bonus
from ..services.postiz_analytics import pull_daily_metrics, run_daily_analytics_cycle
from ..services.scheduler import daily_research_pipeline, publish_scheduled_posts

router = APIRouter(prefix="/api")

import os


def _get_brand_id(request: Request) -> str:
    """Resolve the authenticated user's brand_id from JWT middleware.

    The JWTAuthMiddleware sets request.state.brand_id on every authenticated
    request. This dependency makes every route automatically brand-scoped.
    Raises 401 if the middleware didn't populate the brand (shouldn't happen
    for authenticated routes, but acts as a safety net).
    """
    brand_id = getattr(request.state, "brand_id", None)
    if not brand_id:
        raise HTTPException(
            status_code=401,
            detail="Authenticated brand context not found. Ensure you are logged in.",
        )
    return brand_id


# System-level brand for cron/scheduler calls (no user JWT).
# Deployers set this in their .env — it is intentionally blank in the template.
_SCHEDULER_BRAND_ID = os.environ.get("SCHEDULER_BRAND_ID", "")


def _get_scheduler_brand_id() -> str:
    """Resolve brand_id for scheduler endpoints called by external cron.

    These endpoints use X-Scheduler-Secret instead of a user JWT, so
    request.state.brand_id is not set. Deployers must configure
    SCHEDULER_BRAND_ID in their environment.
    """
    if not _SCHEDULER_BRAND_ID:
        raise HTTPException(
            status_code=503,
            detail="SCHEDULER_BRAND_ID is not configured. Set it in your .env before enabling scheduled jobs.",
        )
    return _SCHEDULER_BRAND_ID


def _get_client_db(request: Request):
    """Retrieve a Supabase client scoped to the user JWT if available (RLS active).
    Falls back to the service_role client if no JWT is present (e.g. cron routes).
    """
    jwt = getattr(request.state, "jwt", None)
    if jwt:
        return get_user_db(jwt)
    return get_db()


@router.post("/research/trigger")
async def trigger_research(request: Request, req: TriggerRequest | None = None):
    brand_id = _get_brand_id(request)
    if req is None:
        req = TriggerRequest()
    result = await run_research(brand_id, req)
    return {"success": True, "data": result.model_dump()}


@router.get("/research/runs")
async def list_runs(
    request: Request,
    status: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    brand_id = _get_brand_id(request)
    db = _get_client_db(request)
    query = (
        db.table("research_runs")
        .select("*", count="exact")
        .eq("brand_id", brand_id)
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


# C-05: Whitelist of allowed sort fields — prevents injection via sort_by parameter
_ALLOWED_SORT_FIELDS = frozenset({"created_at", "title", "url", "source_name", "status", "retriever_type"})


@router.get("/research/items")
async def list_items(
    request: Request,
    status: str | None = None,
    run_id: str | None = None,
    retriever: str | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    brand_id = _get_brand_id(request)
    # C-05: validate sort_by against whitelist
    if sort_by not in _ALLOWED_SORT_FIELDS:
        raise HTTPException(400, f"Invalid sort field. Allowed: {sorted(_ALLOWED_SORT_FIELDS)}")
    if sort_order not in ("asc", "desc"):
        raise HTTPException(400, "sort_order must be 'asc' or 'desc'")

    db = _get_client_db(request)
    query = (
        db.table("research_items")
        .select("*, scores(*)", count="exact")
        .eq("brand_id", brand_id)
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
async def update_item_status(item_id: str, body: dict, request: Request):
    brand_id = _get_brand_id(request)
    new_status = body.get("status")
    if new_status not in ("new", "scored", "approved", "rejected", "archived"):
        raise HTTPException(400, "Invalid status")
    db = _get_client_db(request)
    resp = (
        db.table("research_items")
        .update({"status": new_status})
        .eq("id", item_id)
        .eq("brand_id", brand_id)
        .execute()
    )
    if not resp.data:
        raise HTTPException(404, "Item not found")
    return {"success": True, "data": resp.data[0]}


@router.post("/scoring/run")
async def trigger_scoring(request: Request, req: ScoringRequest | None = None):
    brand_id = _get_brand_id(request)
    if req is None:
        req = ScoringRequest()
    result = await run_scoring(brand_id, req)
    return {"success": True, "data": result}


class GenerateRequest(BaseModel):
    research_item_id: str
    platform: str = "linkedin"
    content_type: str = "post"
    run_god: bool = False
    run_humanizer: bool = False  # NEW: Enable Humanizer after GOD mode


class GodModeRequest(BaseModel):
    pass


class AdaptRequest(BaseModel):
    target_platforms: list[str]


@router.post("/content/generate")
async def api_generate_content(req: GenerateRequest, request: Request):
    brand_id = _get_brand_id(request)

    # Choose pipeline based on flags
    if req.run_humanizer and req.run_god:
        # Full pipeline: Writer -> Editor -> GOD -> Humanizer
        result = await generate_and_god_and_humanize(
            brand_id, req.research_item_id, req.platform, req.content_type,
        )
    elif req.run_god:
        # Standard pipeline: Writer -> Editor -> GOD
        result = await generate_and_god(
            brand_id, req.research_item_id, req.platform, req.content_type,
        )
    else:
        # Basic pipeline: Writer -> Editor only
        result = await generate_content(
            brand_id, req.research_item_id, req.platform, req.content_type,
        )

    return {"success": True, "data": result}


@router.post("/content/drafts/{draft_id}/god-mode")
async def api_god_mode(draft_id: str, request: Request):
    brand_id = _get_brand_id(request)
    result = await run_god_mode(brand_id, draft_id)
    return {"success": True, "data": result}


@router.post("/content/drafts/{draft_id}/adapt")
async def api_adapt_content(draft_id: str, req: AdaptRequest, request: Request):
    brand_id = _get_brand_id(request)
    results = await adapt_content(brand_id, draft_id, req.target_platforms)
    return {"success": True, "data": results}


@router.post("/content/drafts/{draft_id}/humanize")
async def api_humanize_draft(draft_id: str, request: Request):
    """Manually trigger humanization on an existing draft.

    Uses brand settings (use_humanizer, humanizer_channels) and optional model_override.
    Returns humanization result with AI patterns found and remaining AI tells.
    """
    from ..agents.humanizer import humanize_draft
    from ..db import get_db

    brand_id = _get_brand_id(request)

    # Check if humanizer is enabled for this brand
    db = get_db()
    brand = db.table("brands").select("*").eq("id", brand_id).single().execute()
    brand_data = brand.data

    if not brand_data.get("use_humanizer", False):
        raise HTTPException(
            status_code=400,
            detail="Humanizer is disabled for this brand. Enable it in brand settings."
        )

    # Check draft platform
    draft = db.table("content_drafts").select("*").eq("id", draft_id).single().execute()
    draft_data = draft.data
    if not draft_data:
        raise HTTPException(404, "Draft not found")

    platform = draft_data.get("platform", "")
    enabled_channels = brand_data.get("humanizer_channels", ["linkedin", "blog"])
    if platform not in enabled_channels:
        raise HTTPException(
            status_code=400,
            detail=f"Humanizer is not enabled for platform '{platform}'. Enable it in brand settings."
        )

    # Run humanizer
    try:
        model_override = brand_data.get("humanizer_model_override")
        result = await humanize_draft(
            brand_id=brand_id,
            draft_id=draft_id,
            model_override=model_override,
        )
        return {"success": True, "data": result}
    except Exception as e:
        _logger.error("Manual humanization failed for draft %s: %s", draft_id, e)
        raise HTTPException(500, f"Humanization failed: {str(e)}")


@router.get("/content/drafts")
async def list_drafts(
    request: Request,
    status: str | None = None,
    content_type: str | None = None,
    platform: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    brand_id = _get_brand_id(request)
    db = _get_client_db(request)
    query = (
        db.table("content_drafts")
        .select("*", count="exact")
        .eq("brand_id", brand_id)
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
async def update_draft(draft_id: str, body: dict, request: Request):
    brand_id = _get_brand_id(request)
    allowed = {"status", "title", "body", "scheduled_at"}
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(400, "No valid fields to update")
    db = _get_client_db(request)
    resp = (
        db.table("content_drafts")
        .update(updates)
        .eq("id", draft_id)
        .eq("brand_id", brand_id)
        .execute()
    )
    if not resp.data:
        raise HTTPException(404, "Draft not found")
    return {"success": True, "data": resp.data[0]}


@router.get("/research/stats")
async def research_stats(request: Request):
    brand_id = _get_brand_id(request)
    db = _get_client_db(request)
    all_items = (
        db.table("research_items")
        .select("id, status")
        .eq("brand_id", brand_id)
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
async def api_create_session(req: WritingLabCreateRequest, request: Request):
    brand_id = _get_brand_id(request)
    result = await create_session(brand_id, req.topic, req.content_type)
    return {"success": True, "data": result}


@router.get("/writing-lab/sessions")
async def api_list_sessions(
    request: Request,
    status: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    brand_id = _get_brand_id(request)
    db = _get_client_db(request)
    query = (
        db.table("writing_lab_sessions")
        .select("*", count="exact")
        .eq("brand_id", brand_id)
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
async def api_get_session(session_id: str, request: Request):
    db = _get_client_db(request)
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
async def api_vote(session_id: str, req: VoteRequest, request: Request):
    brand_id = _get_brand_id(request)
    result = await vote_round(brand_id, session_id, req.winner, req.feedback)
    return {"success": True, "data": result}


# ── Newsletter Delivery ─────────────────────────────────────────────────────


# C-08: Email validation pattern and recipient limits
_EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')
_MAX_RECIPIENTS = 500


class SendNewsletterRequest(BaseModel):
    newsletter_id: str
    recipients: list[str]

    def model_post_init(self, __context) -> None:  # type: ignore[override]
        if not self.recipients:
            raise ValueError("recipients list cannot be empty")
        if len(self.recipients) > _MAX_RECIPIENTS:
            raise ValueError(f"Too many recipients (max {_MAX_RECIPIENTS})")
        invalid = [e for e in self.recipients if not _EMAIL_RE.match(e)]
        if invalid:
            raise ValueError(f"Invalid email addresses: {invalid[:5]}")


@router.post("/newsletter/send")
async def api_send_newsletter(req: SendNewsletterRequest, request: Request):
    brand_id = _get_brand_id(request)
    result = await send_newsletter(brand_id, req.newsletter_id, req.recipients)
    return {"success": True, "data": result}


@router.get("/newsletter/{newsletter_id}/preview")
async def api_preview_newsletter(newsletter_id: str, request: Request):
    brand_id = _get_brand_id(request)
    html = await preview_newsletter(brand_id, newsletter_id)
    return {"success": True, "data": {"html": html}}


# ── Social Publishing ────────────────────────────────────────────────────────


class PublishRequest(BaseModel):
    """C-03: access_token REMOVED — backend reads token from brands.social_accounts in DB.
    
    The token is never sent over the wire from the frontend.
    brand_id is resolved from the authenticated user's JWT (request.state.brand_id).
    """
    draft_id: str
    platforms: list[str] = ["linkedin"]  # e.g. ["linkedin", "twitter", "instagram"]


# H-06: Validate scheduled_at as ISO 8601 datetime in the future
def _validate_scheduled_at(value: str) -> str:
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        raise ValueError("scheduled_at must be a valid ISO 8601 datetime string")
    # Make timezone-aware for comparison
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    if dt <= datetime.now(timezone.utc):
        raise ValueError("scheduled_at must be in the future")
    return value


class ScheduleRequest(BaseModel):
    draft_id: str
    scheduled_at: str

    model_config = {"json_schema_extra": {"example": {"draft_id": "uuid", "scheduled_at": "2026-04-20T10:00:00+02:00"}}}

    def model_post_init(self, __context) -> None:  # type: ignore[override]
        _validate_scheduled_at(self.scheduled_at)


@router.post("/social/publish")
async def api_publish_social(req: PublishRequest, request: Request):
    """C-03: brand_id from JWT — token fetched from DB, never from client."""
    brand_id = _get_brand_id(request)
    result = await publish_to_postiz(brand_id, req.draft_id, req.platforms)
    return {"success": True, "data": result}


# Legacy compatibility routes — delegate to unified endpoint
@router.post("/social/publish/linkedin")
async def api_publish_linkedin(req: PublishRequest, request: Request):
    """C-03: Legacy route — access_token no longer accepted in body."""
    brand_id = _get_brand_id(request)
    result = await publish_to_postiz(brand_id, req.draft_id, ["linkedin"])
    return {"success": True, "data": result}


@router.post("/social/publish/twitter")
async def api_publish_twitter(req: PublishRequest, request: Request):
    """C-03: Legacy route — access_token no longer accepted in body."""
    brand_id = _get_brand_id(request)
    result = await publish_to_postiz(brand_id, req.draft_id, ["twitter"])
    return {"success": True, "data": result}


@router.post("/social/schedule")
async def api_schedule_post(req: ScheduleRequest, request: Request):
    brand_id = _get_brand_id(request)
    result = await schedule_post(brand_id, req.draft_id, req.scheduled_at)
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
async def api_feedback_loop(request: Request):
    brand_id = _get_brand_id(request)
    result = await update_feedback_bonus(brand_id)
    return {"success": True, "data": result}

# ── Postiz Analytics Scheduler ─────────────────────────────────────────────────────

@router.post("/analytics/pull-metrics", dependencies=[Depends(_require_scheduler_secret)])
async def api_pull_metrics():
    """Pull daily Postiz analytics for all brands. Requires X-Scheduler-Secret header."""
    from ..services.postiz_analytics import run_daily_analytics_cycle
    try:
        result = await run_daily_analytics_cycle()
        return {"success": True, "data": result}
    except HTTPException:
        raise
    except Exception as e:
        _logger.error("Pull metrics failed: %s", e, exc_info=True)
        raise HTTPException(500, "Pull metrics failed")


# ── Scheduler ────────────────────────────────────────────────────────────────


@router.post("/scheduler/daily-pipeline", dependencies=[Depends(_require_scheduler_secret)])
async def api_daily_pipeline():
    """Trigger full daily research + scoring pipeline. Requires X-Scheduler-Secret header.
    Operates on brand defined by SCHEDULER_BRAND_ID env var.
    """
    brand_id = _get_scheduler_brand_id()
    try:
        result = await daily_research_pipeline(brand_id)
        return {"success": True, "data": result}
    except HTTPException:
        raise
    except Exception as e:
        _logger.error("Daily pipeline failed: %s", e, exc_info=True)
        raise HTTPException(500, "Pipeline execution failed")


@router.post("/scheduler/publish-scheduled", dependencies=[Depends(_require_scheduler_secret)])
async def api_publish_scheduled():
    """Publish all posts past their scheduled_at. Requires X-Scheduler-Secret header."""
    brand_id = _get_scheduler_brand_id()
    try:
        result = await publish_scheduled_posts(brand_id)
        return {"success": True, "data": result}
    except HTTPException:
        raise
    except Exception as e:
        _logger.error("Publish scheduled failed: %s", e, exc_info=True)
        raise HTTPException(500, "Publish scheduled failed")


# ── Auth / Secret Management ─────────────────────────────────────────────────


@router.post("/auth/cache-invalidate", dependencies=[Depends(_require_scheduler_secret)])
async def api_auth_cache_invalidate():
    """L-02: Flush the JWT validation cache.

    Call this after rotating Supabase keys so the middleware immediately
    re-validates tokens against the new keys rather than serving stale cache
    entries for up to 5 minutes.

    Requires X-Scheduler-Secret header (same as scheduler endpoints).
    """
    from .auth_middleware import _AUTH_CACHE as _cache_ref  # type: ignore[attr-defined]
    try:
        # Clear the global cache dict in-place (atomic-ish for CPython GIL)
        count = len(_cache_ref)
        _cache_ref.clear()
        _logger.info("L-02: JWT cache invalidated — cleared %d entries", count)
        return {"success": True, "data": {"cleared_entries": count}}
    except Exception:
        # _AUTH_CACHE is lazily initialized — may not exist yet
        return {"success": True, "data": {"cleared_entries": 0}}


# ── LLM Fallback Monitoring ────────────────────────────────────────────────────


@router.get("/llm/fallback-stats")
async def api_get_fallback_stats(request: Request):
    """Get current LLM fallback monitoring statistics.

    Returns daily fallback count, total calls, and fallback percentage.
    Useful for monitoring provider health and cost escalation.
    """
    from ..utils.fallback_monitor import get_fallback_stats

    stats = get_fallback_stats()
    return {"success": True, "data": stats}


@router.get("/llm/fallback-log")
async def api_get_fallback_log(
    request: Request,
    limit: int = Query(50, ge=1, le=500),
    emergency_only: bool = Query(False),
):
    """Get recent LLM fallback attempts from database.

    Args:
        limit: Maximum number of entries to return (1-500)
        emergency_only: If True, only return emergency fallbacks (critical incidents)
    """
    brand_id = _get_brand_id(request)
    db = _get_client_db(request)

    query = db.table("llm_fallback_log").select("*", count="exact")

    if emergency_only:
        query = query.eq("is_emergency", True)

    query = query.eq("brand_id", brand_id).order("created_at", desc=True).limit(limit)

    resp = query.execute()
    return {
        "success": True,
        "data": resp.data,
        "meta": {
            "limit": limit,
            "emergency_only": emergency_only,
            "total": resp.count or 0,
        },
    }


@router.post("/llm/fallback-monitor/reset", dependencies=[Depends(_require_scheduler_secret)])
async def api_reset_fallback_monitor():
    """Reset the in-memory fallback monitor counters.

    Useful for testing or after resolving a major incident.
    Requires X-Scheduler-Secret header.
    """
    from ..utils.fallback_monitor import get_fallback_monitor

    monitor = get_fallback_monitor()
    old_stats = monitor.get_stats()
    monitor.reset()

    _logger.info(
        "Fallback monitor reset - previous stats: %s",
        old_stats
    )

    return {"success": True, "data": {"previous_stats": old_stats}}

