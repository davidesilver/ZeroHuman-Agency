"""Brevo email campaigns API (Phase 5).

Endpoints:
  POST /email-marketing/campaigns         — create + schedule a Brevo campaign from a draft
  GET  /email-marketing/campaigns         — list campaigns for active brand
  GET  /email-marketing/campaigns/metrics — aggregate open/click rates
  POST /email-marketing/campaigns/webhook — Brevo event webhook (no auth required)
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..services.brevo_client import BrevoError, get_brevo_client
from ..db import get_db

_logger = logging.getLogger("content_engine.campaigns")

router = APIRouter(prefix="/email-marketing/campaigns", tags=["campaigns"])
webhook_router = APIRouter(tags=["campaigns-webhook"])

BREVO_WEBHOOK_SECRET = os.environ.get("BREVO_WEBHOOK_SECRET", "")


def _brand_id(request: Request) -> str:
    brand_id = getattr(request.state, "brand_id", None)
    if not brand_id:
        raise HTTPException(401, "Not authenticated")
    return brand_id


class CreateCampaignRequest(BaseModel):
    name: str
    subject: str
    draft_id: Optional[str] = None
    html_content: Optional[str] = None  # falls back to draft body if None
    list_id: Optional[int] = None
    scheduled_at: Optional[str] = None  # ISO 8601, None = send immediately


@router.post("", status_code=201)
async def create_campaign(body: CreateCampaignRequest, request: Request):
    """Create a Brevo campaign (and optionally schedule it)."""
    brand_id = _brand_id(request)
    if not body.name.strip():
        raise HTTPException(400, "name is required")

    html_content = body.html_content
    draft_id = body.draft_id

    # Fetch draft body if html_content not provided
    if not html_content and draft_id:
        res = (
            get_db()
            .from_("content_drafts")
            .select("body, title")
            .eq("id", draft_id)
            .eq("brand_id", brand_id)
            .maybe_single()
            .execute()
        )
        if res.data:
            body_text = res.data.get("body", "")
            # Minimal HTML wrapping — Brevo requires HTML
            html_content = f"<html><body><p>{body_text.replace(chr(10), '</p><p>')}</p></body></html>"

    if not html_content:
        raise HTTPException(400, "html_content or draft_id with body is required")

    brevo = get_brevo_client(brand_id)

    try:
        campaign_data: dict = {
            "name": body.name.strip(),
            "subject": body.subject.strip(),
            "sender": {"name": "Content Engine", "email": "noreply@example.com"},
            "type": "classic",
            "htmlContent": html_content,
        }
        if body.list_id:
            campaign_data["recipients"] = {"listIds": [body.list_id]}

        resp_data = brevo._request("POST", "/emailCampaigns", json=campaign_data)
        brevo_campaign_id = resp_data.get("id")
    except BrevoError as exc:
        raise HTTPException(422, str(exc))
    except Exception as exc:
        raise HTTPException(502, f"Brevo API error: {exc}")

    # Schedule if requested
    if body.scheduled_at and brevo_campaign_id:
        try:
            brevo._request(
                "PUT",
                f"/emailCampaigns/{brevo_campaign_id}/sendAtBestTime",
                json={"scheduledAt": body.scheduled_at},
            )
        except Exception:
            pass  # schedule is best-effort

    # Mirror in local DB
    insert_res = get_db().from_("brevo_campaigns").insert({
        "brand_id": brand_id,
        "draft_id": draft_id,
        "brevo_campaign_id": brevo_campaign_id,
        "name": body.name.strip(),
        "subject": body.subject.strip(),
        "status": "scheduled" if body.scheduled_at else "draft",
        "scheduled_at": body.scheduled_at,
    }).execute()

    return insert_res.data[0] if insert_res.data else {"brevo_campaign_id": brevo_campaign_id}


@router.get("")
async def list_campaigns(request: Request):
    brand_id = _brand_id(request)
    result = (
        get_db()
        .from_("brevo_campaigns")
        .select("id, name, subject, status, scheduled_at, sent_at, recipient_count, metrics, created_at, brevo_campaign_id, draft_id")
        .eq("brand_id", brand_id)
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )
    return result.data or []


@router.get("/metrics")
async def campaign_metrics(request: Request):
    """Aggregate open/click rates across all sent campaigns."""
    brand_id = _brand_id(request)
    result = (
        get_db()
        .from_("brevo_campaigns")
        .select("metrics, recipient_count")
        .eq("brand_id", brand_id)
        .eq("status", "sent")
        .execute()
    )
    rows = result.data or []
    total_sent = sum(r.get("recipient_count") or 0 for r in rows)
    total_opens = sum((r.get("metrics") or {}).get("openCount", 0) for r in rows)
    total_clicks = sum((r.get("metrics") or {}).get("clickCount", 0) for r in rows)
    return {
        "campaigns": len(rows),
        "total_sent": total_sent,
        "avg_open_rate": round(total_opens / total_sent * 100, 1) if total_sent else 0,
        "avg_click_rate": round(total_clicks / total_sent * 100, 1) if total_sent else 0,
    }


@webhook_router.post("/email-marketing/campaigns/webhook")
async def brevo_webhook(request: Request):
    """Receive Brevo event webhooks and update campaign metrics."""
    if BREVO_WEBHOOK_SECRET:
        sig = request.headers.get("X-Brevo-Signature", "")
        body_bytes = await request.body()
        expected = hmac.new(  # type: ignore[attr-defined]
            BREVO_WEBHOOK_SECRET.encode(),
            body_bytes,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(sig, expected):
            raise HTTPException(401, "Invalid webhook signature")
        import json as _json
        payload = _json.loads(body_bytes)
    else:
        payload = await request.json()

    event = payload.get("event", "")
    brevo_campaign_id = payload.get("campaignId")

    if not brevo_campaign_id:
        return {"ok": True}

    metric_map = {
        "opened": "openCount",
        "click": "clickCount",
        "hardBounce": "hardBounceCount",
        "softBounce": "softBounceCount",
        "unsubscribed": "unsubscribeCount",
        "delivered": "deliveredCount",
    }

    metric_key = metric_map.get(event)
    if not metric_key:
        return {"ok": True, "ignored_event": event}

    # Fetch current metrics and increment
    res = (
        get_db()
        .from_("brevo_campaigns")
        .select("id, metrics")
        .eq("brevo_campaign_id", brevo_campaign_id)
        .maybe_single()
        .execute()
    )
    if res.data:
        metrics = res.data.get("metrics") or {}
        metrics[metric_key] = metrics.get(metric_key, 0) + 1
        get_db().from_("brevo_campaigns").update({
            "metrics": metrics,
            "status": "sent",
        }).eq("id", res.data["id"]).execute()

    return {"ok": True}
