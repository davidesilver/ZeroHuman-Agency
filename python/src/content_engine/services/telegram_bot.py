"""Telegram bot command handler.

Receives webhook POST from Telegram Bot API, validates sender auth,
parses commands, executes actions against the database, and replies.

Supported commands:
  /approve <draft_id>     — set content_draft status → approved
  /send <newsletter_id>   — trigger newsletter send pipeline
  /skip <item_id>         — set research_item status → skipped
  /discard <draft_id>     — set content_draft status → discarded
  /status                 — summary of all brands pipeline state
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any

import httpx

from ..config import settings
from ..db import get_db

logger = logging.getLogger(__name__)


async def _reply(chat_id: int | str, text: str) -> None:
    bot_token = settings.telegram_bot_token
    if not bot_token:
        return
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
    except Exception as exc:
        logger.error("Bot reply failed: %s", exc)


def _verify_secret(header_secret: str | None) -> bool:
    expected = settings.telegram_webhook_secret
    if not expected:
        return True  # Not configured — allow (warn in logs)
    if not header_secret:
        return False
    return hmac.compare_digest(
        hashlib.sha256(header_secret.encode()).hexdigest(),
        hashlib.sha256(expected.encode()).hexdigest(),
    )


def _authorized_chat(chat_id: int | str) -> bool:
    configured = settings.telegram_chat_id
    if not configured:
        return True
    return str(chat_id) == str(configured)


async def _cmd_approve(draft_id: str, brand_id: str) -> str:
    db = get_db()
    row = db.table("content_drafts").select("id, status").eq("id", draft_id).eq("brand_id", brand_id).maybe_single().execute().data
    if not row:
        return f"❌ Draft `{draft_id[:8]}` not found."
    db.table("content_drafts").update({"status": "approved"}).eq("id", draft_id).execute()
    return f"✅ Draft `{draft_id[:8]}` approved."


async def _cmd_discard(draft_id: str, brand_id: str) -> str:
    db = get_db()
    row = db.table("content_drafts").select("id, status").eq("id", draft_id).eq("brand_id", brand_id).maybe_single().execute().data
    if not row:
        return f"❌ Draft `{draft_id[:8]}` not found."
    db.table("content_drafts").update({"status": "discarded"}).eq("id", draft_id).execute()
    return f"🗑 Draft `{draft_id[:8]}` discarded."


async def _cmd_skip(item_id: str, brand_id: str) -> str:
    db = get_db()
    row = db.table("research_items").select("id").eq("id", item_id).eq("brand_id", brand_id).maybe_single().execute().data
    if not row:
        return f"❌ Research item `{item_id[:8]}` not found."
    db.table("research_items").update({"status": "skipped"}).eq("id", item_id).execute()
    return f"⏭ Research item `{item_id[:8]}` skipped."


async def _cmd_send(newsletter_id: str, brand_id: str) -> str:
    db = get_db()
    row = db.table("newsletters").select("id, status, title").eq("id", newsletter_id).eq("brand_id", brand_id).maybe_single().execute().data
    if not row:
        return f"❌ Newsletter `{newsletter_id[:8]}` not found."
    if row.get("status") == "sent":
        return f"ℹ️ Newsletter `{newsletter_id[:8]}` already sent."

    # Fetch recipients from email provider config
    try:
        from .email_providers import get_email_provider
        from .newsletter_delivery import send_newsletter
        provider = await get_email_provider(brand_id)
        recipients = [provider.config.list_id] if provider.config.list_id else []
        if not recipients:
            return "❌ No recipient list configured for this brand."
        result = await send_newsletter(brand_id, newsletter_id, recipients)
        return f"📧 Newsletter `{newsletter_id[:8]}` sent to {result['recipients']} recipients via {result['provider']}."
    except Exception as exc:
        return f"❌ Send failed: {str(exc)[:120]}"


async def _cmd_status() -> str:
    db = get_db()
    try:
        brands = db.table("brands").select("id, name").execute().data or []
        lines = ["📊 *System Status*\n"]
        for brand in brands[:5]:
            bid = brand["id"]
            bname = brand.get("name", bid[:8])

            # Last pipeline run
            last_event = (
                db.table("notification_events")
                .select("created_at, event_type")
                .eq("brand_id", bid)
                .eq("event_type", "daily_digest_sent")
                .order("created_at", desc=True)
                .limit(1)
                .execute()
                .data
            )
            last_run = last_event[0]["created_at"][:16] if last_event else "never"

            # Pending drafts
            pending = db.table("content_drafts").select("id", count="exact").eq("brand_id", bid).eq("status", "draft").execute().count or 0

            # Scheduled newsletters
            scheduled = db.table("newsletters").select("id", count="exact").eq("brand_id", bid).eq("status", "scheduled").execute().count or 0

            lines.append(
                f"*{bname}*\n"
                f"  • Last run: `{last_run}`\n"
                f"  • Pending drafts: {pending}\n"
                f"  • Scheduled newsletters: {scheduled}"
            )
        return "\n\n".join(lines) if len(lines) > 1 else "No brands found."
    except Exception as exc:
        return f"❌ Status check failed: {str(exc)[:120]}"


_HELP_TEXT = (
    "*Available commands:*\n\n"
    "`/approve <id>` — approve a content draft\n"
    "`/send <id>` — send a newsletter\n"
    "`/skip <id>` — skip a research item\n"
    "`/discard <id>` — discard a draft\n"
    "`/status` — pipeline status for all brands"
)


async def handle_update(payload: dict[str, Any]) -> dict:
    """Process a Telegram webhook update payload.

    Returns {"ok": True} in all cases — errors are replied to the user,
    never raised to the caller (Telegram expects 200 for all updates).
    """
    message = payload.get("message") or payload.get("edited_message")
    if not message:
        return {"ok": True}

    chat_id = message.get("chat", {}).get("id")
    text: str = (message.get("text") or "").strip()

    if not chat_id or not text or not text.startswith("/"):
        return {"ok": True}

    if not _authorized_chat(chat_id):
        logger.warning("Rejected command from unauthorized chat_id %s", chat_id)
        return {"ok": True}

    parts = text.split(maxsplit=2)
    command = parts[0].lower().split("@")[0]  # strip @botname suffix
    arg = parts[1] if len(parts) > 1 else ""

    # Resolve brand_id from chat context — use first brand for now
    # (single-brand setup; multi-brand would require per-brand bot or inline selection)
    db = get_db()
    brand_row = db.table("brands").select("id").order("created_at").limit(1).execute().data
    brand_id = brand_row[0]["id"] if brand_row else ""

    if command == "/status":
        reply = await _cmd_status()
    elif command == "/approve":
        if not arg:
            reply = "Usage: `/approve <draft_id>`"
        elif not brand_id:
            reply = "❌ No brand configured."
        else:
            reply = await _cmd_approve(arg.strip(), brand_id)
    elif command == "/send":
        if not arg:
            reply = "Usage: `/send <newsletter_id>`"
        elif not brand_id:
            reply = "❌ No brand configured."
        else:
            reply = await _cmd_send(arg.strip(), brand_id)
    elif command == "/skip":
        if not arg:
            reply = "Usage: `/skip <item_id>`"
        elif not brand_id:
            reply = "❌ No brand configured."
        else:
            reply = await _cmd_skip(arg.strip(), brand_id)
    elif command == "/discard":
        if not arg:
            reply = "Usage: `/discard <draft_id>`"
        elif not brand_id:
            reply = "❌ No brand configured."
        else:
            reply = await _cmd_discard(arg.strip(), brand_id)
    else:
        reply = _HELP_TEXT

    await _reply(chat_id, reply)
    return {"ok": True}
