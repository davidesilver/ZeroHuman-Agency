"""Newsletter delivery via Resend API."""

from __future__ import annotations
import html as html_lib

import resend

from ..config import settings
from ..db import get_db
from ..utils.audit_trail import log_publish_event

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

    # Save HTML to newsletter
    db.table("newsletters").update({"html_body": html}).eq("id", newsletter_id).execute()

    return html


async def send_newsletter(brand_id: str, newsletter_id: str, recipients: list[str]) -> dict:
    """Send a newsletter via Resend."""
    if not settings.resend_api_key:
        raise RuntimeError("RESEND_API_KEY not configured")

    resend.api_key = settings.resend_api_key
    db = get_db()

    newsletter = db.table("newsletters").select("*").eq("id", newsletter_id).single().execute().data
    if not newsletter:
        raise ValueError("Newsletter not found")

    html = newsletter.get("html_body")
    if not html:
        html = await generate_newsletter_html(brand_id, newsletter_id)

    title = newsletter.get("title", "Newsletter")

    # Send via Resend
    result = resend.Emails.send({
        "from": f"{settings.newsletter_from_name} <{settings.newsletter_from_email}>",
        "to": recipients,
        "subject": title,
        "html": html,
    })

    resend_id = result.get("id") if isinstance(result, dict) else str(result)

    # Update newsletter record
    db.table("newsletters").update({
        "status": "sent",
        "sent_at": "now()",
        "recipients_count": len(recipients),
    }).eq("id", newsletter_id).execute()

    await log_publish_event(
        brand_id, newsletter_id,
        action="newsletter_send",
        platform="email",
        status="success",
        details={"resend_id": resend_id, "recipients": len(recipients)},
    )

    return {
        "newsletter_id": newsletter_id,
        "resend_id": resend_id,
        "recipients": len(recipients),
        "status": "sent",
    }


async def preview_newsletter(brand_id: str, newsletter_id: str) -> str:
    """Generate and return newsletter HTML for preview."""
    return await generate_newsletter_html(brand_id, newsletter_id)
