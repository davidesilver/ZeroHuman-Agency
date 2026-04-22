"""Newsletter generator service — builds a draft newsletter from approved research items.

P4.1–P4.4: Memory-native newsletter generation pipeline.

Q2 confirmed: no engagement weighting — editorial merit only, not follower growth metrics
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

from ..db import get_db
from ..utils.llm_client import call_llm
from ..memory.retrieval import recall as memory_recall
from ..services.alerting import send_telegram_alert
from ..services.newsletter_delivery import _build_html, SECTION_TEMPLATE

logger = logging.getLogger("content_engine.newsletter_generator")

_NEWSLETTER_SYSTEM_PROMPT = """You are an editorial newsletter writer for {brand_name}.
Your voice rules: {tone_rules_text}
Write in English."""

_NEWSLETTER_USER_PROMPT = """Here are {n} approved research items from the last 7 days, ranked by editorial score:

{items_text}

Task:
1. Select the 3–6 best items that form a coherent newsletter
2. Group them into 2–4 thematic sections
3. Write: newsletter title, 2-sentence intro, each section (label 1-3 words, title, body 60-100 words bridging the item to the brand's perspective), 1-sentence closing

Return ONLY valid JSON (no markdown):
{{
  "title": "Newsletter title (max 60 chars)",
  "intro": "2-sentence editorial intro connecting the themes",
  "sections": [
    {{"label": "SHORT LABEL", "title": "Section title", "body": "60-100 word editorial body", "source_url": "url of source item"}},
    ...
  ],
  "closing": "1-sentence closing thought",
  "selected_item_ids": ["uuid1", "uuid2", ...]
}}"""


async def generate_newsletter(brand_id: str) -> dict:
    """Generate a newsletter draft from approved research items for the given brand.

    Steps:
    1. Fetch approved research_items created in last 7 days, ordered by score DESC, limit 20
    2. If < 3 items: return early with insufficient_items reason
    3. Get brand name from DB
    4. Get tone rules from memory
    5. Call LLM (Sonnet) to generate newsletter structure (JSON)
    6. Parse result → build sections list
    7. Render HTML via _build_html
    8. Compute next edition_number
    9. INSERT into newsletters
    10. INSERT newsletter_candidates for each selected item
    11. Log memory_event "newsletter_generated"
    12. Send Telegram alert
    13. Return result dict

    Q2 confirmed: no engagement weighting — editorial merit only, not follower growth metrics
    """
    db = get_db()

    # 1. Fetch approved research items from last 7 days, by score DESC
    since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    items_resp = (
        db.table("research_items")
        .select("id, title, summary, url, scores(*)")
        .eq("brand_id", brand_id)
        .eq("status", "approved")
        .gte("created_at", since)
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    )
    items = items_resp.data or []

    # Sort by score DESC — scores is a related table, extract composite score
    def _extract_score(item: dict) -> float:
        scores = item.get("scores") or []
        if isinstance(scores, list) and scores:
            return float(scores[0].get("composite_score", 0) or 0)
        if isinstance(scores, dict):
            return float(scores.get("composite_score", 0) or 0)
        return 0.0

    items.sort(key=_extract_score, reverse=True)
    items = items[:20]

    # 2. Check minimum items threshold
    if len(items) < 3:
        logger.info(
            "Newsletter generation skipped for brand %s: only %d approved items (need 3)",
            brand_id, len(items),
        )
        return {"ok": False, "reason": "insufficient_items", "count": len(items)}

    # 3. Get brand name
    brand_resp = db.table("brands").select("name").eq("id", brand_id).single().execute()
    brand_name = (brand_resp.data or {}).get("name", "Newsletter")

    # 4. Get tone rules from memory
    tone_facts = await memory_recall(brand_id, "tone of voice rules", kind="tone_rule", k=5)
    if tone_facts:
        tone_rules_text = "\n".join(
            f"- {f.get('statement', '')}" for f in tone_facts if f.get("statement")
        )
    else:
        tone_rules_text = "Direct, practical, insightful"

    # 5. Build LLM prompts and call Sonnet
    items_text_parts = []
    for i, item in enumerate(items, start=1):
        score = _extract_score(item)
        title = item.get("title") or "(no title)"
        summary = item.get("summary") or ""
        url = item.get("url") or ""
        items_text_parts.append(
            f"{i}. [{score:.2f}] {title}\n{summary}\nSource: {url}"
        )
    items_text = "\n\n".join(items_text_parts)

    system_prompt = _NEWSLETTER_SYSTEM_PROMPT.format(
        brand_name=brand_name,
        tone_rules_text=tone_rules_text,
    )
    user_prompt = _NEWSLETTER_USER_PROMPT.format(
        n=len(items),
        items_text=items_text,
    )

    resp = await call_llm(
        prompt=user_prompt,
        brand_id=brand_id,
        context="newsletter_generation",
        action="generate_newsletter",
        system_prompt=system_prompt,
        task_type="creative",
        temperature=0.7,
    )

    # 6. Parse LLM result
    raw = resp.content.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(
            line for line in lines
            if not line.strip().startswith("```")
        ).strip()

    try:
        newsletter_data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse newsletter JSON from LLM: %s — raw: %s", exc, raw[:400])
        return {"ok": False, "reason": "llm_parse_error", "detail": str(exc)}

    nl_title = newsletter_data.get("title", f"{brand_name} Weekly")
    nl_intro = newsletter_data.get("intro", "")
    nl_sections_raw = newsletter_data.get("sections", [])
    nl_closing = newsletter_data.get("closing", "")
    selected_item_ids: list[str] = newsletter_data.get("selected_item_ids", [])

    # Build sections list for HTML rendering
    sections: list[dict] = []
    # Prepend intro as a lead section if present
    if nl_intro:
        sections.append({"label": "THIS WEEK", "title": nl_title, "body": nl_intro})

    for sec in nl_sections_raw:
        sections.append({
            "label": sec.get("label", ""),
            "title": sec.get("title", ""),
            "body": sec.get("body", ""),
        })

    # Append closing as a final section
    if nl_closing:
        sections.append({"label": "CLOSING", "title": "", "body": nl_closing})

    # 7. Render HTML
    # Compute edition_number first (needed for _build_html)
    edition_resp = (
        db.table("newsletters")
        .select("edition_number")
        .eq("brand_id", brand_id)
        .order("edition_number", desc=True)
        .limit(1)
        .execute()
    )
    edition_rows = edition_resp.data or []
    if edition_rows and edition_rows[0].get("edition_number") is not None:
        edition_number = int(edition_rows[0]["edition_number"]) + 1
    else:
        edition_number = 1

    html_body = _build_html(
        brand_name=brand_name,
        edition_number=edition_number,
        sections=sections,
    )

    # 9. INSERT into newsletters
    insert_resp = (
        db.table("newsletters")
        .insert({
            "brand_id": brand_id,
            "title": nl_title,
            "edition_number": edition_number,
            "html_body": html_body,
            "status": "draft",
        })
        .execute()
    )
    newsletter_row = (insert_resp.data or [{}])[0]
    newsletter_id = newsletter_row.get("id")

    if not newsletter_id:
        logger.error("Newsletter INSERT did not return an id for brand %s", brand_id)
        return {"ok": False, "reason": "db_insert_failed"}

    # 10. INSERT newsletter_candidates for each selected item
    # Fall back to all items if LLM didn't return selected_item_ids
    if not selected_item_ids:
        # Use items matching the sections by best-effort (all fetched items)
        selected_item_ids = [item["id"] for item in items if item.get("id")]

    if selected_item_ids:
        candidates_payload = [
            {
                "newsletter_id": newsletter_id,
                "research_item_id": item_id,
                "slot_type": "editorial",
                "is_selected": True,
            }
            for item_id in selected_item_ids
        ]
        db.table("newsletter_candidates").insert(candidates_payload).execute()

    # 11. Log memory_event "newsletter_generated"
    try:
        db.table("memory_events").insert({
            "brand_id": brand_id,
            "event_kind": "newsletter_generated",
            "subject_kind": "newsletter",
            "subject_id": newsletter_id,
            "summary": f"Newsletter draft #{edition_number} generated: {nl_title}",
            "payload": {
                "edition_number": edition_number,
                "sections_count": len(nl_sections_raw),
                "selected_items": len(selected_item_ids),
            },
        }).execute()
    except Exception as exc:
        logger.warning("Failed to log memory_event for newsletter %s: %s", newsletter_id, exc)

    # 12. Send Telegram alert (P4.T hook)
    total_tokens = resp.tokens_prompt + resp.tokens_completion
    topics = ", ".join(
        sec.get("label", "") for sec in nl_sections_raw if sec.get("label")
    )
    alert_msg = (
        f"*Newsletter Draft Generated*\n\n"
        f"*Title:* {nl_title}\n"
        f"*Edition:* #{edition_number}\n"
        f"*Brand:* {brand_name}\n"
        f"*Sections:* {len(nl_sections_raw)}\n"
        f"*Topics:* {topics or 'n/a'}\n"
        f"*Tokens:* {total_tokens}\n"
        f"*Status:* draft — review at /newsletter/{newsletter_id}"
    )
    try:
        await send_telegram_alert(alert_msg)
    except Exception as exc:
        logger.warning("Telegram alert failed for newsletter %s: %s", newsletter_id, exc)

    # 13. Return result
    return {
        "ok": True,
        "newsletter_id": newsletter_id,
        "edition_number": edition_number,
        "title": nl_title,
        "sections_count": len(nl_sections_raw),
    }
