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
    """C-06: Guard scheduler endpoints with a shared secret. Fail closed."""
    if not _SCHEDULER_SECRET:
        _logger.error(
            "SCHEDULER_SECRET not set — refusing to run scheduler endpoint",
        )
        raise HTTPException(
            status_code=503,
            detail="Scheduler is not configured (SCHEDULER_SECRET unset)",
        )
    provided = request.headers.get("X-Scheduler-Secret", "")
    # Constant-time comparison to avoid trivial timing leak on the secret.
    import hmac as _hmac
    if not provided or not _hmac.compare_digest(provided, _SCHEDULER_SECRET):
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
from ..services.newsletter_delivery import send_newsletter, preview_newsletter, get_newsletter_report
from ..services.postiz_publisher import publish_now as publish_to_postiz, schedule_post
from ..services.feedback_loop import record_social_metrics, update_feedback_bonus
from ..services.postiz_analytics import pull_daily_metrics, run_daily_analytics_cycle
from ..services.scheduler import daily_research_pipeline, publish_scheduled_posts
from ..services.credential_vault import (
    get_credentials,
    set_credentials,
    delete_credentials,
    list_configured_services,
)

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


# System-level brand override for cron/scheduler calls (no user JWT).
# If unset AND _SCHEDULER_ALLOW_ALL_BRANDS is false, scheduler routes refuse
# to run.  Multi-brand fan-out is opt-in to prevent a misconfigured deploy
# (missing SCHEDULER_BRAND_ID) from silently iterating across every tenant.
_SCHEDULER_BRAND_ID = os.environ.get("SCHEDULER_BRAND_ID", "")
_SCHEDULER_ALLOW_ALL_BRANDS = os.environ.get(
    "SCHEDULER_ALLOW_ALL_BRANDS", "false"
).strip().lower() in ("1", "true", "yes")


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


def _get_scheduler_brand_ids() -> list[str]:
    """Resolve the target brand set for cron-driven routes.

    Priority:
    1. SCHEDULER_BRAND_ID env var when explicitly configured (legacy/dev override).
    2. All distinct brand_ids present in brand_members ONLY when
       SCHEDULER_ALLOW_ALL_BRANDS=true is also set (multi-brand prod opt-in).

    A misconfigured deployment that simply forgets SCHEDULER_BRAND_ID must NOT
    silently fan out across every tenant — it must refuse to run.
    """
    if _SCHEDULER_BRAND_ID:
        return [_SCHEDULER_BRAND_ID]

    if not _SCHEDULER_ALLOW_ALL_BRANDS:
        raise HTTPException(
            status_code=503,
            detail=(
                "Scheduler is unconfigured: set SCHEDULER_BRAND_ID for a single brand, "
                "or SCHEDULER_ALLOW_ALL_BRANDS=true to fan out across every tenant."
            ),
        )

    db = get_db()
    memberships = db.table("brand_members").select("brand_id").execute().data or []
    brand_ids = sorted({row["brand_id"] for row in memberships if row.get("brand_id")})

    if not brand_ids:
        raise HTTPException(
            status_code=503,
            detail="No brands found for scheduler execution. Create a brand or set SCHEDULER_BRAND_ID.",
        )

    return brand_ids


def _get_client_db(request: Request):
    """Retrieve a Supabase client scoped to the user JWT if available (RLS active).
    Falls back to the service_role client if no JWT is present (e.g. cron routes).
    """
    jwt = getattr(request.state, "jwt", None)
    if jwt:
        return get_user_db(jwt)
    return get_db()


@router.get("/system/llm-routing")
async def get_llm_routing(request: Request):
    """Expose the capability→model routing matrix for the Settings UI.

    This is a read-only view of `config/llm_models.py` — the single source of
    truth used by `call_llm()`. The frontend renders it so operators can see
    exactly which model is primary, and which models will be tried on fallback,
    for each task type (creative, scoring, research, etc.).

    The endpoint is auth-gated by JWTAuthMiddleware (any logged-in user can
    read it — the data isn't sensitive, just operational metadata).
    """
    from ..config.llm_models import (
        MODEL_ROUTING,
        MODEL_CAPABILITIES,
        OPENROUTER_FALLBACK_MODELS,
        MODEL_CONFIGS,
    )

    capabilities = []
    for capability, models in MODEL_ROUTING.items():
        # Models are already ordered by priority in routing — first = primary,
        # rest = fallback chain. We surface that ordering plus per-model meta.
        ordered = sorted(models, key=lambda m: m.priority)
        capabilities.append({
            "key": capability.value,
            "label": MODEL_CAPABILITIES.get(capability, capability.value),
            "primary": {
                "model_id": ordered[0].model_id,
                "provider": ordered[0].provider,
                "cost_tier": ordered[0].cost_tier,
            } if ordered else None,
            "fallbacks": [
                {
                    "model_id": m.model_id,
                    "provider": m.provider,
                    "cost_tier": m.cost_tier,
                }
                for m in ordered[1:]
            ],
        })

    # Free-tier emergency fallbacks (used when *all* primary models fail)
    emergency = [
        {
            "model_id": mid,
            "provider": MODEL_CONFIGS[mid].provider if mid in MODEL_CONFIGS else "openrouter",
            "cost_tier": "free",
        }
        for mid in OPENROUTER_FALLBACK_MODELS
    ]

    return {
        "capabilities": capabilities,
        "emergency_fallbacks": emergency,
        "task_type_map": {
            # Mirrors the routing inside utils/llm_client.py:call_llm
            "reasoning":  "reasoning",
            "creative":   "creative",
            "research":   "research",
            "scoring":    "scoring",
            "fact_check": "fact_check",
            "editing":    "editing",
            "general":    "general",
        },
    }


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
    allowed = {"status", "title", "body", "scheduled_at", "media_urls"}
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
    # Migration 030 ships an RPC that does the GROUP BY in Postgres so we no
    # longer materialise every research_item row in Python.  Fall back to the
    # in-memory loop if the RPC is missing (older DB / partial migration set).
    try:
        rpc_resp = db.rpc(
            "research_items_status_counts", {"p_brand_id": brand_id}
        ).execute()
        counts = rpc_resp.data or {}
        if counts:
            return {"success": True, "data": counts}
    except Exception:  # pragma: no cover - defensive fallback for legacy DBs
        _logger.warning(
            "research_items_status_counts RPC unavailable; falling back to client-side aggregation",
            exc_info=True,
        )

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


@router.post("/newsletter/generate")
async def api_generate_newsletter(request: Request):
    brand_id = _get_brand_id(request)
    from ..services.newsletter_generator import generate_newsletter
    result = await generate_newsletter(brand_id)
    if not result.get("ok"):
        raise HTTPException(422, result.get("reason", "generation_failed"))
    return {"success": True, "data": result}


@router.post("/scheduler/weekly-newsletter", dependencies=[Depends(_require_scheduler_secret)])
async def api_weekly_newsletter(request: Request):
    """Generate newsletter drafts for all brands with sufficient content.
    Called by pg_cron weekly (Monday 05:00 UTC) or manually.

    Brands are fanned out concurrently with a small concurrency cap so a slow
    LLM provider on one brand does not block the others.
    """
    import asyncio

    from ..services.newsletter_generator import generate_newsletter

    db = get_db()
    brands_resp = db.table("brand_members").select("brand_id").execute()
    brand_ids = sorted({row["brand_id"] for row in (brands_resp.data or [])})

    if not brand_ids:
        return {"success": True, "data": {"brands_processed": 0, "results": []}}

    # Cap concurrency so we don't hammer LLM rate limits with N brands at once.
    sem = asyncio.Semaphore(min(5, max(1, len(brand_ids))))

    async def _one(bid: str) -> dict:
        async with sem:
            try:
                r = await generate_newsletter(bid)
                return {"brand_id": bid, **r}
            except Exception as e:
                return {"brand_id": bid, "ok": False, "error": str(e)}

    results = await asyncio.gather(*(_one(bid) for bid in brand_ids))
    return {"success": True, "data": {"brands_processed": len(results), "results": results}}


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


@router.get("/newsletter/{newsletter_id}/report")
async def api_newsletter_report(newsletter_id: str, request: Request):
    brand_id = _get_brand_id(request)
    report = await get_newsletter_report(brand_id, newsletter_id)
    return {"success": True, "data": report}


# ── Email Webhooks ───────────────────────────────────────────────────────────

@router.post("/webhooks/email/brevo")
async def webhook_brevo(request: Request):
    """Receive Brevo marketing webhook events (open, click, bounce, unsub).

    Brevo validates by source IP; we trust the payload structure.
    """
    try:
        payload = await request.json()
    except Exception:
        return {"ok": False, "error": "invalid_json"}

    db = get_db()

    # Brevo sends a list of events
    events = payload if isinstance(payload, list) else [payload]

    _brevo_event_map = {
        "delivered": "delivered",
        "opened": "opened",
        "clicks": "clicked",
        "click": "clicked",
        "soft_bounces": "bounced",
        "hard_bounces": "bounced",
        "unsubscribed": "unsubscribed",
        "spam_reports": "bounced",
    }

    for event in events:
        event_type_raw = event.get("event", "")
        event_type = _brevo_event_map.get(event_type_raw)
        if not event_type:
            continue

        campaign_id = str(event.get("campaignId") or event.get("campaign_id") or "")
        email = event.get("email", "")
        ts = event.get("ts_event") or event.get("date_event") or None

        if not campaign_id:
            continue

        # Find newsletter by provider_campaign_id
        row = (
            db.table("newsletters")
            .select("id, brand_id")
            .eq("provider_campaign_id", campaign_id)
            .maybe_single()
            .execute()
            .data
        )
        if not row:
            continue

        newsletter_id = row["id"]
        try:
            db.table("newsletter_events").insert({
                "newsletter_id": newsletter_id,
                "event_type": event_type,
                "email": email,
                "occurred_at": ts,
                "metadata": {"raw_event": event_type_raw, "provider": "brevo"},
            }).execute()
        except Exception as exc:
            _logger.warning("Failed to insert newsletter_event: %s", exc)

        # Update aggregate metrics
        _update_newsletter_metrics(db, newsletter_id)

    return {"ok": True}


@router.post("/webhooks/email/mailchimp")
async def webhook_mailchimp(request: Request):
    """Receive Mailchimp webhook events.

    Mailchimp sends form-encoded data with a shared secret in the URL.
    """
    try:
        body = await request.body()
        from urllib.parse import parse_qs
        params = parse_qs(body.decode())
        event_type_raw = (params.get("type") or [""])[0]
        email = (params.get("data[email]") or [""])[0]
        campaign_id = (params.get("data[campaign_id]") or [""])[0]
    except Exception:
        return {"ok": False, "error": "parse_error"}

    _mc_event_map = {
        "subscribe": None,
        "unsubscribe": "unsubscribed",
        "campaign": None,
        "cleaned": "bounced",
        "upemail": None,
        "profile": None,
        "opened": "opened",
        "clicked": "clicked",
    }
    event_type = _mc_event_map.get(event_type_raw)
    if not event_type or not campaign_id:
        return {"ok": True}

    db = get_db()
    row = (
        db.table("newsletters")
        .select("id")
        .eq("provider_campaign_id", campaign_id)
        .maybe_single()
        .execute()
        .data
    )
    if not row:
        return {"ok": True}

    newsletter_id = row["id"]
    try:
        db.table("newsletter_events").insert({
            "newsletter_id": newsletter_id,
            "event_type": event_type,
            "email": email,
            "metadata": {"raw_event": event_type_raw, "provider": "mailchimp"},
        }).execute()
        _update_newsletter_metrics(db, newsletter_id)
    except Exception as exc:
        _logger.warning("Failed to insert mailchimp newsletter_event: %s", exc)

    return {"ok": True}


def _update_newsletter_metrics(db, newsletter_id: str) -> None:
    """Recompute and persist aggregate metrics from newsletter_events."""
    try:
        events = (
            db.table("newsletter_events")
            .select("event_type")
            .eq("newsletter_id", newsletter_id)
            .execute()
            .data
        ) or []

        # Count delivered first for rate computation
        delivered = sum(1 for e in events if e["event_type"] == "delivered") or 1
        opens = len({e for e in events if e["event_type"] == "opened"})
        clicks = len({e for e in events if e["event_type"] == "clicked"})
        unsubs = sum(1 for e in events if e["event_type"] == "unsubscribed")

        db.table("newsletters").update({
            "open_rate": round(opens / delivered, 4),
            "click_rate": round(clicks / delivered, 4),
            "unsubscribe_count": unsubs,
        }).eq("id", newsletter_id).execute()
    except Exception as exc:
        _logger.warning("Failed to update newsletter metrics for %s: %s", newsletter_id, exc)


# ── Email Provider ──────────────────────────────────────────────────────────


class EmailProviderConfigRequest(BaseModel):
    provider: str
    api_key: str
    sender_name: str = ""
    sender_email: str = ""
    list_id: str = ""
    webhook_secret: str = ""
    ab_split_pct: int = 20
    ab_wait_hours: int = 4


@router.get("/email-provider/config")
async def api_get_email_provider_config(request: Request):
    brand_id = _get_brand_id(request)
    db = get_db()
    row = (
        db.table("email_provider_config")
        .select("provider, sender_name, sender_email, list_id, ab_split_pct, ab_wait_hours")
        .eq("brand_id", brand_id)
        .maybe_single()
        .execute()
        .data
    )
    return {"success": True, "data": row or {}}


@router.post("/email-provider/config")
async def api_upsert_email_provider_config(req: EmailProviderConfigRequest, request: Request):
    brand_id = _get_brand_id(request)
    db = get_db()
    payload = {
        "brand_id": brand_id,
        "provider": req.provider,
        "api_key": req.api_key,
        "sender_name": req.sender_name,
        "sender_email": req.sender_email,
        "list_id": req.list_id,
        "webhook_secret": req.webhook_secret,
        "ab_split_pct": req.ab_split_pct,
        "ab_wait_hours": req.ab_wait_hours,
    }
    db.table("email_provider_config").upsert(payload, on_conflict="brand_id").execute()
    return {"success": True}


@router.post("/email-provider/validate")
async def api_validate_email_provider(req: EmailProviderConfigRequest, request: Request):
    """Validate an email provider API key by calling a lightweight endpoint."""
    from ..services.email_providers import BrevoProvider, ResendProvider, ProviderConfig
    config = ProviderConfig(
        provider=req.provider,
        api_key=req.api_key,
        sender_name=req.sender_name or "Test",
        sender_email=req.sender_email or "test@example.com",
        list_id=req.list_id,
        webhook_secret=req.webhook_secret,
        ab_split_pct=req.ab_split_pct,
        ab_wait_hours=req.ab_wait_hours,
    )
    match req.provider:
        case "brevo":
            provider = BrevoProvider(config)
        case _:
            provider = ResendProvider(config)
    await provider.validate()
    return {"success": True, "data": {"provider": req.provider, "valid": True}}


@router.get("/email-provider/lists")
async def api_get_email_provider_lists(request: Request):
    """Fetch subscriber lists from the brand's configured provider."""
    brand_id = _get_brand_id(request)
    from ..services.email_providers import get_email_provider
    provider = await get_email_provider(brand_id)
    lists = await provider.get_lists()
    return {
        "success": True,
        "data": [{"list_id": l.list_id, "name": l.name, "total_subscribers": l.total_subscribers} for l in lists],
    }


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
    platforms: list[str] | None = None

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
    result = await schedule_post(brand_id, req.draft_id, req.scheduled_at, req.platforms)
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
async def api_record_metrics(req: MetricsRequest, request: Request):
    brand_id = _get_brand_id(request)
    # Confirm the draft belongs to this brand before recording metrics, otherwise
    # any authenticated user could overwrite another tenant's metrics row
    # (the feedback loop trains its scoring engine on those numbers).
    db = get_db()
    draft = (
        db.table("content_drafts")
        .select("id")
        .eq("id", req.draft_id)
        .eq("brand_id", brand_id)
        .single()
        .execute()
        .data
    )
    if not draft:
        raise HTTPException(404, "draft not found")
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
    """Trigger full daily research + scoring pipeline across eligible brands."""
    brand_ids = _get_scheduler_brand_ids()
    try:
        results = []
        for brand_id in brand_ids:
            try:
                result = await daily_research_pipeline(brand_id)
                results.append({"brand_id": brand_id, **result})
            except Exception as brand_error:
                results.append({"brand_id": brand_id, "ok": False, "error": str(brand_error)})
        return {"success": True, "data": {"brands_processed": len(results), "results": results}}
    except HTTPException:
        raise
    except Exception as e:
        _logger.error("Daily pipeline failed: %s", e, exc_info=True)
        raise HTTPException(500, "Pipeline execution failed")


@router.post("/scheduler/publish-scheduled", dependencies=[Depends(_require_scheduler_secret)])
async def api_publish_scheduled():
    """Publish all posts past their scheduled_at across eligible brands."""
    brand_ids = _get_scheduler_brand_ids()
    try:
        results = []
        for brand_id in brand_ids:
            try:
                result = await publish_scheduled_posts(brand_id)
                results.append({"brand_id": brand_id, **result})
            except Exception as brand_error:
                results.append({"brand_id": brand_id, "ok": False, "error": str(brand_error)})
        return {"success": True, "data": {"brands_processed": len(results), "results": results}}
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


# ============================================================================
# P2.5 — Memory endpoints
# ============================================================================


class MemoryConsolidateRequest(BaseModel):
    brand_id: str | None = None   # required for scheduler calls; overrides JWT brand
    session_id: str | None = None
    # Optionally pass source texts directly (e.g. from P3 discover wizard)
    source_texts: list[dict] | None = None


@router.post("/memory/consolidate", dependencies=[Depends(_require_scheduler_secret)])
async def api_memory_consolidate(
    payload: MemoryConsolidateRequest,
    request: Request,
):
    """Trigger a memory consolidation run for a brand.

    - Scheduler-secret protected (X-Scheduler-Secret header required).
    - If payload.brand_id is provided it is used (scheduler use-case).
    - If omitted and the request has a JWT brand, that brand is used.
    - source_texts: optional list of {"text", "source_kind", "source_id"} dicts.
      If not provided, the worker fetches recent episodic events automatically.
    """
    from ..memory.consolidation.worker import run_consolidation

    # Resolve brand_id: explicit > JWT middleware > error
    brand_id = payload.brand_id or getattr(request.state, "brand_id", None)
    if not brand_id:
        raise HTTPException(400, "brand_id required (set in payload or authenticate via JWT)")

    report = await run_consolidation(
        brand_id=brand_id,
        session_id=payload.session_id,
        source_texts=payload.source_texts,
    )

    return {
        "success": True,
        "data": {
            "brand_id": brand_id,
            "session_id": payload.session_id,
            "facts_added": len(report.facts_added),
            "facts_rejected_verify": len(report.facts_rejected_verify),
            "facts_rejected_dedup": len(report.facts_rejected_dedup),
            "facts_superseded": len(report.facts_superseded),
            "duration_s": report.duration_s,
            "errors": report.errors,
        },
    }


@router.post("/memory/consolidate-user")
async def api_memory_consolidate_user(
    payload: MemoryConsolidateRequest,
    request: Request,
):
    """User-triggered memory consolidation — JWT auth only (no scheduler secret).

    Identical logic to /memory/consolidate but callable from the dashboard UI.
    The scheduler-protected endpoint remains for cron use.
    """
    from ..memory.consolidation.worker import run_consolidation

    brand_id = payload.brand_id or getattr(request.state, "brand_id", None)
    if not brand_id:
        raise HTTPException(400, "brand_id required (set in payload or authenticate via JWT)")

    report = await run_consolidation(
        brand_id=brand_id,
        session_id=payload.session_id,
        source_texts=payload.source_texts,
    )

    return {
        "success": True,
        "data": {
            "brand_id": brand_id,
            "session_id": payload.session_id,
            "facts_added": len(report.facts_added),
            "facts_rejected_verify": len(report.facts_rejected_verify),
            "facts_rejected_dedup": len(report.facts_rejected_dedup),
            "facts_superseded": len(report.facts_superseded),
            "duration_s": report.duration_s,
            "errors": report.errors,
        },
    }


class MemoryRecallRequest(BaseModel):
    query: str
    kind: str | None = None
    k: int = 5


@router.post("/memory/recall")
async def api_memory_recall(
    payload: MemoryRecallRequest,
    request: Request,
):
    """Retrieve top-k semantic memories for the authenticated brand.

    Requires JWT authentication (uses X-Brand-ID / brand from JWT middleware).
    Uses temporal-weighted composite score: 0.60·cosine + 0.25·decay + 0.15·importance.
    """
    brand_id = _get_brand_id(request)
    from ..memory.retrieval import recall

    facts = await recall(brand_id=brand_id, query=payload.query, kind=payload.kind, k=payload.k)
    return {"success": True, "data": facts}


@router.get("/memory/facts")
async def api_memory_list_facts(
    request: Request,
    kind: str | None = Query(None),
    tier: str | None = Query(None),
    limit: int = Query(100, le=500),
):
    """List semantic memory facts for the authenticated brand (Memory Inspector)."""
    brand_id = _get_brand_id(request)
    from ..memory.stores.semantic import list_facts

    facts = await list_facts(brand_id=brand_id, kind=kind, tier=tier, limit=limit)  # type: ignore[arg-type]
    return {"success": True, "data": facts, "count": len(facts)}


@router.get("/memory/episodic")
async def api_memory_episodic(
    request: Request,
    limit: int = Query(100, le=500),
):
    """Return recent episodic events from vw_memory_episodic (Memory Inspector feed)."""
    brand_id = _get_brand_id(request)
    db = get_db()
    resp = (
        db.table("vw_memory_episodic")
        .select("event_kind,subject_kind,subject_id,summary,payload,occurred_at")
        .eq("brand_id", brand_id)
        .order("occurred_at", desc=True)
        .limit(limit)
        .execute()
    )
    return {"success": True, "data": resp.data or []}


@router.get("/memory/expiring")
async def api_memory_expiring(
    request: Request,
    days: int = Query(7, le=30),
):
    """Return semantic facts expiring within `days` days (Memory Inspector warning widget)."""
    brand_id = _get_brand_id(request)
    from ..memory.decay import expiring_soon

    facts = await expiring_soon(brand_id=brand_id, days=days)
    return {"success": True, "data": facts}


@router.patch("/memory/facts/{fact_id}")
async def api_memory_patch_fact(
    fact_id: str,
    request: Request,
):
    """Partially update a semantic fact (statement, tier, importance) from the Inspector."""
    brand_id = _get_brand_id(request)
    body = await request.json()

    # Only allow these fields to be patched
    allowed = {"statement", "tier", "importance", "metadata"}
    patch = {k: v for k, v in body.items() if k in allowed}
    if not patch:
        raise HTTPException(400, "No patchable fields provided")

    from ..memory.stores.semantic import update_fact, list_facts

    # Verify ownership: fact must belong to this brand
    db = get_db()
    check = (
        db.table("memory_semantic")
        .select("id")
        .eq("id", fact_id)
        .eq("brand_id", brand_id)
        .maybe_single()
        .execute()
    )
    if not check.data:
        raise HTTPException(404, "Fact not found or not in your brand")

    await update_fact(fact_id=fact_id, **patch)
    return {"success": True}


@router.delete("/memory/facts/{fact_id}")
async def api_memory_delete_fact(fact_id: str, request: Request):
    """Hard-delete a semantic fact (use sparingly — prefer supersede)."""
    brand_id = _get_brand_id(request)
    db = get_db()
    check = (
        db.table("memory_semantic")
        .select("id")
        .eq("id", fact_id)
        .eq("brand_id", brand_id)
        .maybe_single()
        .execute()
    )
    if not check.data:
        raise HTTPException(404, "Fact not found or not in your brand")

    from ..memory.stores.semantic import delete_fact

    await delete_fact(fact_id)
    return {"success": True}


@router.post("/memory/facts/{fact_id}/supersede")
async def api_memory_supersede_fact(fact_id: str, request: Request):
    """Supersede a fact with a new statement (temporal arbiter pattern)."""
    brand_id = _get_brand_id(request)
    body = await request.json()
    new_statement = body.get("new_statement", "").strip()
    reason = body.get("reason", "")
    if not new_statement:
        raise HTTPException(400, "new_statement is required")

    db = get_db()
    check = (
        db.table("memory_semantic")
        .select("id")
        .eq("id", fact_id)
        .eq("brand_id", brand_id)
        .maybe_single()
        .execute()
    )
    if not check.data:
        raise HTTPException(404, "Fact not found or not in your brand")

    from ..memory.arbiter import supersede

    new_id = await supersede(
        old_fact_id=fact_id,
        new_statement=new_statement,
        brand_id=brand_id,
        reason=reason,
    )
    return {"success": True, "data": {"new_fact_id": new_id}}


# ============================================================================
# P3.2 — Memory discover (URL preview)
# P3.3 — Memory upload-source (file upload preview)
# ============================================================================


class MemoryDiscoverRequest(BaseModel):
    url: str
    brand_id: str | None = None  # optional override (must be in member_brand_ids)


@router.post("/memory/discover")
async def api_memory_discover(payload: MemoryDiscoverRequest, request: Request):
    """Fetch a URL, extract candidate memory facts, and return them for review.

    This is a preview endpoint — nothing is written to memory_semantic.
    The caller (UI) reviews candidates and calls /memory/consolidate to persist.

    Auth: JWT required. brand_id override accepted only if it belongs to the caller.
    """
    import re as _re

    import httpx

    from ..memory.consolidation.extractor import extract_facts_from_text
    from ..memory.consolidation.verifier import verify
    from ..utils.url_safety import UnsafeURLError, assert_safe_public_url

    # Resolve brand_id: JWT default, or body override validated against membership
    jwt_brand_id = _get_brand_id(request)
    if payload.brand_id and payload.brand_id != jwt_brand_id:
        member_brand_ids = getattr(request.state, "member_brand_ids", [])
        if payload.brand_id not in member_brand_ids:
            raise HTTPException(403, "brand_id override not in your brand memberships")
        brand_id = payload.brand_id
    else:
        brand_id = jwt_brand_id

    url = payload.url.strip()
    try:
        assert_safe_public_url(url, allow_http=True)
    except UnsafeURLError as exc:
        raise HTTPException(400, f"unsafe url: {exc}")

    # Fetch the URL (no redirects: each hop would need re-validation)
    try:
        async with httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=False,
            headers={"User-Agent": "Mozilla/5.0"},
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            raw_html = resp.text
    except httpx.HTTPStatusError as exc:
        raise HTTPException(502, f"URL fetch failed: HTTP {exc.response.status_code}")
    except httpx.RequestError as exc:
        raise HTTPException(502, f"URL fetch error: {exc}")

    # Strip HTML tags, collapse whitespace, cap at 12 000 chars
    text = _re.sub(r"<[^>]+>", " ", raw_html)
    text = _re.sub(r"\s+", " ", text).strip()
    text = text[:12000]

    # Extract candidate facts
    candidates = await extract_facts_from_text(
        text=text,
        brand_id=brand_id,
        source_kind="url",
        source_id=url,
    )

    # Run verifier (mark each fact, include all)
    for fact in candidates:
        result = verify(fact["statement"])
        fact["verified"] = result.passed
        fact["verification_failures"] = result.failures

    return {
        "success": True,
        "data": {
            "url": url,
            "candidates": candidates,
            "count": len(candidates),
        },
    }


@router.post("/memory/upload-source")
async def api_memory_upload_source(request: Request):
    """Upload a document file and extract candidate memory facts for review.

    Accepts: .txt, .md, .pdf, .docx  (multipart/form-data with `file` field).
    Optional form field: `brand_id` (override, must be in member_brand_ids).

    This is a preview endpoint — nothing is written to memory_semantic.
    """
    import io

    from fastapi import UploadFile
    from fastapi.datastructures import FormData

    from ..memory.consolidation.extractor import extract_facts_from_text
    from ..memory.consolidation.verifier import verify

    # Parse multipart form
    form: FormData = await request.form()
    file_field = form.get("file")
    if file_field is None or not isinstance(file_field, UploadFile):
        raise HTTPException(400, "Missing `file` field in multipart form")

    upload: UploadFile = file_field
    filename: str = upload.filename or "unknown"

    # Resolve brand_id
    jwt_brand_id = _get_brand_id(request)
    form_brand_id = form.get("brand_id")
    if form_brand_id and form_brand_id != jwt_brand_id:
        member_brand_ids = getattr(request.state, "member_brand_ids", [])
        if form_brand_id not in member_brand_ids:
            raise HTTPException(403, "brand_id override not in your brand memberships")
        brand_id = form_brand_id
    else:
        brand_id = jwt_brand_id

    # Determine file type by extension
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    raw_bytes = await upload.read()

    if ext in ("txt", "md"):
        text = raw_bytes.decode("utf-8", errors="replace")

    elif ext == "pdf":
        try:
            from pypdf import PdfReader
        except ImportError:
            raise HTTPException(500, "pypdf is not installed — PDF uploads unavailable")
        reader = PdfReader(io.BytesIO(raw_bytes))
        pages_text = []
        for page in reader.pages:
            pages_text.append(page.extract_text() or "")
        text = "\n".join(pages_text)

    elif ext == "docx":
        try:
            from docx import Document
        except ImportError:
            raise HTTPException(500, "python-docx is not installed — DOCX uploads unavailable")
        doc = Document(io.BytesIO(raw_bytes))
        text = "\n".join(p.text for p in doc.paragraphs)

    else:
        raise HTTPException(
            400,
            f"Unsupported file type '.{ext}'. Supported: .txt, .md, .pdf, .docx",
        )

    # Extract and verify
    candidates = await extract_facts_from_text(
        text=text,
        brand_id=brand_id,
        source_kind="upload",
        source_id=filename,
    )

    for fact in candidates:
        result = verify(fact["statement"])
        fact["verified"] = result.passed
        fact["verification_failures"] = result.failures

    return {
        "success": True,
        "data": {
            "filename": filename,
            "candidates": candidates,
            "count": len(candidates),
        },
    }


# ── Credential Vault ──────────────────────────────────────────────────────────

_ALLOWED_SERVICES = {
    "postiz", "serper", "tavily", "youtube", "firecrawl",
    "x", "resend", "openrouter", "brevo",
}


class CredentialPayload(BaseModel):
    credentials: dict


@router.get("/brands/credentials")
async def api_list_credentials(request: Request):
    """List service names with credentials configured for the authenticated brand."""
    brand_id = _get_brand_id(request)
    services = await list_configured_services(brand_id)
    return {"brand_id": brand_id, "configured_services": services}


@router.put("/brands/credentials/{service_name}")
async def api_set_credentials(service_name: str, payload: CredentialPayload, request: Request):
    """Store (or update) encrypted credentials for a service.

    The credential dict format per service:
        postiz:    {"api_key": "...", "base_url": "http://..."}
        serper:    {"api_key": "..."}
        tavily:    {"api_key": "..."}
        youtube:   {"api_key": "..."}
        firecrawl: {"api_key": "..."}
        x:         {"bearer_token": "..."}
        resend:    {"api_key": "..."}
        openrouter: {"api_key": "..."}
    """
    if service_name not in _ALLOWED_SERVICES:
        raise HTTPException(400, f"Unknown service '{service_name}'. Allowed: {sorted(_ALLOWED_SERVICES)}")
    brand_id = _get_brand_id(request)
    await set_credentials(brand_id, service_name, payload.credentials)
    return {"ok": True, "service": service_name}


@router.delete("/brands/credentials/{service_name}")
async def api_delete_credentials(service_name: str, request: Request):
    """Delete credentials for a service from the vault."""
    brand_id = _get_brand_id(request)
    await delete_credentials(brand_id, service_name)
    return {"ok": True, "service": service_name}


@router.get("/brands/credentials/{service_name}/status")
async def api_credential_status(service_name: str, request: Request):
    """Check whether credentials exist for a service (does NOT return the values)."""
    brand_id = _get_brand_id(request)
    creds = await get_credentials(brand_id, service_name)
    return {
        "service": service_name,
        "configured": creds is not None,
        "fields": list(creds.keys()) if creds else [],
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
