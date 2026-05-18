"""Newsletter delivery — routes through the configured EmailProvider adapter."""

from __future__ import annotations
import html as html_lib
import logging

from ..db import get_db
from ..utils.audit_trail import log_publish_event
from .email_providers import get_email_provider, SenderInfo
from .notification import emit_event

log = logging.getLogger(__name__)

NEWSLETTER_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 0; background: #f5f5f5; }}
    .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; }}
    .header {{ background: #1a1a1a; padding: 24px; text-align: center; }}
    .header h1 {{ color: #ffffff; font-size: 20px; margin: 0; }}
    .header .edition {{ color: #888; font-size: 12px; margin-top: 4px; }}
    .content {{ padding: 24px; }}
    .section {{ margin-bottom: 24px; border-bottom: 1px solid #eee; padding-bottom: 24px; }}
    .section:last-child {{ border-bottom: none; }}
    .section-label {{ display: inline-block; background: #e8f5e9; color: #2e7d32; font-size: 10px; font-weight: 600; padding: 2px 8px; border-radius: 4px; text-transform: uppercase; margin-bottom: 8px; }}
    .section h2 {{ font-size: 18px; margin: 0 0 8px 0; color: #1a1a1a; }}
    .section p {{ font-size: 14px; line-height: 1.6; color: #444; margin: 0; }}
    .footer {{ background: #f5f5f5; padding: 16px 24px; text-align: center; font-size: 11px; color: #999; }}
    .footer a {{ color: #666; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>{brand_name}</h1>
      <div class="edition">Edition #{edition_number}</div>
    </div>
    <div class="content">
      {sections_html}
    </div>
    <div class="footer">
      <p>You received this because you subscribed to {brand_name}.</p>
      <p><a href="{{{{unsubscribe_url}}}}">Unsubscribe</a></p>
    </div>
  </div>
</body>
</html>"""

SECTION_TEMPLATE = """<div class="section">
  <span class="section-label">{label}</span>
  <h2>{title}</h2>
  <p>{body}</p>
</div>"""


def _build_html(brand_name: str, edition_number: int, sections: list[dict]) -> str:
    """Build newsletter HTML from sections.

    All user-controlled fields are HTML-escaped to prevent XSS (C-04).
    Phase 2 will replace this with React Email rendering.
    """
    sections_html = ""
    for section in sections:
        sections_html += SECTION_TEMPLATE.format(
            label=html_lib.escape(section.get("label", "")),
            title=html_lib.escape(section.get("title", "")),
            body=html_lib.escape(section.get("body", "")).replace("\n", "<br>"),
        )
    return NEWSLETTER_TEMPLATE.format(
        brand_name=html_lib.escape(brand_name),
        edition_number=int(edition_number),
        sections_html=sections_html,
    )


async def generate_newsletter_html(brand_id: str, newsletter_id: str) -> str:
    """Generate HTML for a newsletter from its candidate slots."""
    db = get_db()

    newsletter = db.table("newsletters").select("*").eq("id", newsletter_id).single().execute().data
    brand = db.table("brands").select("name").eq("id", brand_id).single().execute().data

    sections = []
    slot_map = {
        "slot_sistema_id": "SYSTEM",
        "slot_strumento_id": "TOOL",
        "slot_mossa_id": "MOVE",
    }

    for slot_key, label in slot_map.items():
        draft_id = newsletter.get(slot_key)
        if draft_id:
            draft = db.table("content_drafts").select("title, body").eq("id", draft_id).single().execute().data
            if draft:
                sections.append({
                    "label": label,
                    "title": draft.get("title", ""),
                    "body": draft.get("body", ""),
                })

    html = _build_html(
        brand_name=brand.get("name", "Newsletter") if brand else "Newsletter",
        edition_number=newsletter.get("edition_number", 1),
        sections=sections,
    )

    db.table("newsletters").update({"html_body": html}).eq("id", newsletter_id).execute()
    return html


def _make_resend_fallback(recipients: list[str]):
    from .email_providers import ResendProvider, ProviderConfig
    from ..config import settings as s
    return ResendProvider(ProviderConfig(
        provider="resend",
        api_key=s.resend_api_key,
        sender_name=s.newsletter_from_name,
        sender_email=s.newsletter_from_email,
        list_id=",".join(recipients),
        webhook_secret="",
        ab_split_pct=20,
        ab_wait_hours=4,
    ))


async def send_newsletter(brand_id: str, newsletter_id: str, recipients: list[str]) -> dict:
    """Send a newsletter via the brand's configured email provider.

    Uses A/B campaign if subject variants exist, regular campaign otherwise.
    Falls back to Resend on primary provider failure.
    """
    db = get_db()

    newsletter = db.table("newsletters").select("*").eq("id", newsletter_id).single().execute().data
    if not newsletter:
        raise ValueError("Newsletter not found")

    html = newsletter.get("html_body")
    if not html:
        html = await generate_newsletter_html(brand_id, newsletter_id)

    title = newsletter.get("title", "Newsletter")
    subject_a: str = newsletter.get("subject_variant_a") or title
    subject_b: str | None = newsletter.get("subject_variant_b")

    provider = await get_email_provider(brand_id)
    list_id = provider.config.list_id or (recipients[0] if recipients else "")
    sender = SenderInfo(name=provider.config.sender_name, email=provider.config.sender_email)
    used_provider = provider.config.provider
    ab_used = False

    try:
        if subject_b and list_id and provider.config.provider != "resend":
            # Check if provider has sent at least one campaign before (Brevo A/B requirement)
            prior = (
                db.table("newsletters")
                .select("id")
                .eq("brand_id", brand_id)
                .eq("status", "sent")
                .neq("id", newsletter_id)
                .limit(1)
                .execute()
                .data
            )
            if prior:
                campaign_ref = await provider.create_ab_campaign(
                    list_id=list_id,
                    subjects=[subject_a, subject_b],
                    html=html,
                    sender=sender,
                )
                ab_used = True
            else:
                # First campaign — regular send to satisfy Brevo prerequisite
                log.info("First campaign for brand %s — sending regular (not A/B)", brand_id)
                campaign_ref = await provider.create_campaign(list_id=list_id, subject=subject_a, html=html, sender=sender)
        else:
            campaign_ref = await provider.create_campaign(list_id=list_id, subject=subject_a, html=html, sender=sender)

        result = await provider.send_campaign(campaign_ref)

    except Exception as exc:
        log.error("Primary provider %s failed: %s — falling back to Resend", provider.config.provider, exc)
        # Emit provider failure alert before fallback
        try:
            await emit_event(
                event_type="campaign_send_failed",
                title=f"Campaign send failed — {provider.config.provider}",
                severity="error",
                brand_id=brand_id,
                detail={"provider": provider.config.provider, "error": str(exc), "newsletter_id": newsletter_id},
                entity_type="newsletter",
                entity_id=newsletter_id,
            )
        except Exception:
            pass
        used_provider = "resend"
        fallback = _make_resend_fallback(recipients)
        fb_campaign = await fallback.create_campaign(
            list_id=",".join(recipients), subject=subject_a, html=html,
        )
        result = await fallback.send_campaign(fb_campaign)
        campaign_ref = result.campaign_ref

    update_payload: dict = {
        "status": "sent",
        "sent_at": "now()",
        "recipients_count": len(recipients),
        "provider_campaign_id": campaign_ref.campaign_id,
    }
    db.table("newsletters").update(update_payload).eq("id", newsletter_id).execute()

    await log_publish_event(
        brand_id, newsletter_id,
        action="newsletter_send",
        platform=used_provider,
        status="success",
        details={
            "provider_send_id": result.provider_send_id,
            "recipients": len(recipients),
            "ab_used": ab_used,
        },
    )

    # Lifecycle alert: campaign sent
    try:
        await emit_event(
            event_type="campaign_sent",
            title=f"Newsletter #{newsletter.get('edition_number', '?')} sent",
            severity="success",
            brand_id=brand_id,
            detail={
                "provider": used_provider,
                "recipients": len(recipients),
                "subject_a": subject_a,
                "subject_b": subject_b or "",
                "ab_used": ab_used,
            },
            entity_type="newsletter",
            entity_id=newsletter_id,
        )
    except Exception:
        pass

    return {
        "newsletter_id": newsletter_id,
        "provider": used_provider,
        "provider_send_id": result.provider_send_id,
        "ab_used": ab_used,
        "recipients": len(recipients),
        "status": "sent",
    }


async def get_newsletter_report(brand_id: str, newsletter_id: str) -> dict:
    """Fetch campaign analytics from the email provider."""
    db = get_db()
    newsletter = db.table("newsletters").select("provider_campaign_id").eq("id", newsletter_id).maybe_single().execute().data
    if not newsletter or not newsletter.get("provider_campaign_id"):
        return {"error": "No provider campaign ID — newsletter not yet sent via provider"}

    from .email_providers import CampaignRef
    provider = await get_email_provider(brand_id)
    campaign_ref = CampaignRef(
        provider=provider.config.provider,
        campaign_id=newsletter.get("provider_campaign_id", ""),
    )
    report = await provider.get_report(campaign_ref)
    return {
        "sent": report.sent,
        "delivered": report.delivered,
        "opens": report.opens,
        "unique_opens": report.unique_opens,
        "clicks": report.clicks,
        "unique_clicks": report.unique_clicks,
        "unsubscribes": report.unsubscribes,
        "bounces": report.bounces,
        "open_rate": report.open_rate,
        "click_rate": report.click_rate,
        "click_to_open": report.click_to_open,
    }


async def preview_newsletter(brand_id: str, newsletter_id: str) -> str:
    """Generate and return newsletter HTML for preview."""
    return await generate_newsletter_html(brand_id, newsletter_id)
