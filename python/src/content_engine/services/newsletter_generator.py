"""Newsletter generator — 4-pass multi-step pipeline.

Pass 1 (Selection + Layout): selects research items, picks layout, groups sections
Pass 2 (Draft):              writes full copy for each section
Pass 3 (Refinement):         self-critiques and improves draft copy
Pass 4 (Subject Variants):   generates 2 A/B subject line alternatives

Budget target: ~$0.05/newsletter across all passes.
Falls back gracefully: Pass 3 failure → Pass 2 output; Pass 4 failure → single subject.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from ..config import settings
from ..db import get_db
from ..utils.llm_client import call_llm_with_json, call_llm
from ..memory.retrieval import recall as memory_recall
from ..services.notification import emit_event

logger = logging.getLogger("content_engine.newsletter_generator")


# ── Prompts ───────────────────────────────────────────────────────────────────

_P1_SYSTEM = """You are the editorial director for {brand_name}.
Tone rules: {tone_rules}
Today's date: {today}"""

_P1_USER = """Below are {n} approved research items (ranked by editorial score).

{items}

Task — respond with ONLY valid JSON (no markdown):
{{
  "layout": "digest" | "single_story" | "announcement",
  "layout_rationale": "1-sentence reason",
  "selected_item_ids": ["uuid1", ...],
  "sections": [
    {{
      "label": "LABEL (1-3 words, ALL CAPS)",
      "title": "Section headline",
      "item_ids": ["uuid"],
      "angle": "Editorial angle in 1 sentence"
    }}
  ],
  "intro_angle": "2-sentence editorial frame for the whole newsletter",
  "closing_angle": "1-sentence closing thought"
}}

Layout guide:
- digest: 3-6 items, multiple sections, scan-friendly
- single_story: 1 dominant story with supporting context
- announcement: urgent/important single message with strong CTA"""


_P2_SYSTEM = """You are a newsletter writer for {brand_name}.
Tone rules: {tone_rules}
Write in a clear, engaging, brand-consistent voice."""

_P2_USER = """Write the full newsletter copy for this structure:

Layout: {layout}
Sections: {sections_json}
Intro angle: {intro_angle}
Closing angle: {closing_angle}

Respond with ONLY valid JSON:
{{
  "title": "Newsletter title (max 60 chars)",
  "intro": "2-sentence editorial intro",
  "sections": [
    {{
      "label": "LABEL",
      "title": "Section headline",
      "body": "60-100 word editorial body (bridge source to brand perspective)"
    }}
  ],
  "closing": "1-sentence closing"
}}"""


_P3_SYSTEM = """You are a senior editor reviewing newsletter copy for {brand_name}.
Apply these tone rules strictly: {tone_rules}"""

_P3_USER = """Review and improve this newsletter draft:

{draft_json}

Check each section for: tone alignment, hook quality (first sentence), readability, length (60-100 words/section).
Make targeted improvements — do NOT change structure or layout.

Respond with the SAME JSON structure with improved copy:
{{
  "title": "...",
  "intro": "...",
  "sections": [{{"label": "...", "title": "...", "body": "..."}}],
  "closing": "..."
}}"""


_P4_SYSTEM = "You are a conversion-focused email subject line specialist."

_P4_USER = """Generate 2 compelling subject line variants for this newsletter:

Newsletter title: {title}
Section topics: {topics}
Brand: {brand_name}
{past_performance_block}
Rules:
- Max 50 chars each
- Different angles (one curiosity, one direct)
- No clickbait, no all-caps, no excessive punctuation

Respond with ONLY valid JSON:
{{"subject_a": "...", "subject_b": "..."}}"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_score(item: dict) -> float:
    scores = item.get("scores") or []
    if isinstance(scores, list) and scores:
        return float(scores[0].get("composite_score", 0) or 0)
    if isinstance(scores, dict):
        return float(scores.get("composite_score", 0) or 0)
    return 0.0


def _build_past_performance_block(db: Any, brand_id: str) -> str:
    """Build a past subject-line performance hint for Pass 4.

    Queries the last 10 sent newsletters and surfaces the top-3 by open_rate
    so the LLM can mimic high-performing patterns.
    """
    try:
        rows = (
            db.table("newsletters")
            .select("subject_variant_a, subject_variant_b, ab_winner, open_rate")
            .eq("brand_id", brand_id)
            .eq("status", "sent")
            .not_.is_("open_rate", "null")
            .order("open_rate", desc=True)
            .limit(10)
            .execute()
            .data
        ) or []

        if not rows:
            return ""

        top = rows[:3]
        lines = []
        for r in top:
            winner = r.get("ab_winner")
            subject = (
                r.get("subject_variant_b") if winner == "b"
                else r.get("subject_variant_a")
            ) or r.get("subject_variant_a") or ""
            rate = float(r.get("open_rate") or 0)
            if subject:
                lines.append(f"  - \"{subject}\" → {rate * 100:.1f}% open rate")

        if not lines:
            return ""

        return "Past high-performing subject lines for this brand (use as stylistic reference only):\n" + "\n".join(lines) + "\n"
    except Exception as exc:
        logger.debug("Could not load past performance for Pass 4: %s", exc)
        return ""


async def _render_html(
    layout: str,
    content: dict,
    brand_theme: dict,
) -> str | None:
    """Call Next.js render endpoint to get branded HTML. Returns None on failure."""
    nextjs_url = settings.nextjs_url
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{nextjs_url}/api/newsletter/render",
                json={"layout": layout, "content": content, "brand_theme": brand_theme},
            )
            resp.raise_for_status()
            return resp.json().get("html")
    except Exception as exc:
        logger.warning("React Email render failed (%s), falling back to _build_html", exc)
        return None


def _build_html_fallback(brand_name: str, edition_number: int, content: dict) -> str:
    """Minimal HTML fallback if React Email render endpoint is unavailable."""
    import html as html_lib
    sections_html = ""
    for sec in content.get("sections", []):
        label = html_lib.escape(sec.get("label", ""))
        title = html_lib.escape(sec.get("title", ""))
        body = html_lib.escape(sec.get("body", "")).replace("\n", "<br>")
        sections_html += f"""<div style="margin-bottom:24px;padding-bottom:24px;border-bottom:1px solid #eee">
  <span style="font-size:10px;font-weight:600;text-transform:uppercase;color:#2e7d32">{label}</span>
  <h2 style="font-size:18px;margin:8px 0;color:#1a1a1a">{title}</h2>
  <p style="font-size:14px;line-height:1.6;color:#444;margin:0">{body}</p>
</div>"""
    intro_html = f'<p style="font-size:15px;line-height:1.7;color:#555;margin:0 0 24px">{html_lib.escape(content.get("intro",""))}</p>' if content.get("intro") else ""
    closing_html = f'<p style="font-size:14px;color:#666;font-style:italic;margin:16px 0 0">{html_lib.escape(content.get("closing",""))}</p>' if content.get("closing") else ""
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"></head><body style="margin:0;background:#f5f5f5">
<div style="max-width:600px;margin:0 auto;background:#fff">
  <div style="background:#1a1a1a;padding:24px;text-align:center">
    <h1 style="color:#fff;font-size:20px;margin:0">{html_lib.escape(brand_name)}</h1>
    <div style="color:#888;font-size:12px;margin-top:4px">Edition #{edition_number}</div>
  </div>
  <div style="padding:24px">{intro_html}{sections_html}{closing_html}</div>
  <div style="background:#f5f5f5;padding:16px;text-align:center;font-size:11px;color:#999">
    <a href="#unsubscribe" style="color:#666">Unsubscribe</a>
  </div>
</div></body></html>"""


# ── Main pipeline ─────────────────────────────────────────────────────────────

async def generate_newsletter(brand_id: str) -> dict:
    """4-pass newsletter generation pipeline.

    Returns a result dict with ok, newsletter_id, edition_number, title,
    layout, subject_a, subject_b, sections_count.
    """
    db = get_db()

    # ── Fetch data ────────────────────────────────────────────────────────────
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
    items: list[dict] = items_resp.data or []
    items.sort(key=_extract_score, reverse=True)

    if len(items) < 3:
        logger.info("Skipped newsletter for brand %s: %d items (need ≥3)", brand_id, len(items))
        return {"ok": False, "reason": "insufficient_items", "count": len(items)}

    brand_resp = db.table("brands").select("name, primary_color, logo_url").eq("id", brand_id).maybe_single().execute()
    brand_row: dict = brand_resp.data or {}
    brand_name = brand_row.get("name", "Newsletter")

    tone_facts = await memory_recall(brand_id, "tone of voice rules", kind="tone_rule", k=5)
    tone_rules = "\n".join(f"- {f.get('statement','')}" for f in tone_facts if f.get("statement")) or "Direct, practical, insightful"

    # Build brand theme for React Email
    brand_theme = {
        "brandName": brand_name,
        "primaryColor": brand_row.get("primary_color") or "#1a1a1a",
        "accentColor": "#2563eb",
    }

    # Compute edition number (needed for render)
    edition_resp = (
        db.table("newsletters")
        .select("edition_number")
        .eq("brand_id", brand_id)
        .order("edition_number", desc=True)
        .limit(1)
        .execute()
    )
    edition_rows = edition_resp.data or []
    edition_number = (int(edition_rows[0]["edition_number"]) + 1) if edition_rows and edition_rows[0].get("edition_number") is not None else 1

    # Format items for prompts
    items_text = "\n\n".join(
        f"{i}. [{_extract_score(it):.2f}] {it.get('title','')}\n{it.get('summary','')[:200]}\nID: {it.get('id')}"
        for i, it in enumerate(items, 1)
    )
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # ── Pass 1: Selection + Layout ────────────────────────────────────────────
    logger.info("[Pass 1] Selecting items and layout for brand %s", brand_id)
    p1_result = await call_llm_with_json(
        prompt=_P1_USER.format(n=len(items), items=items_text),
        brand_id=brand_id,
        context="newsletter_p1_selection",
        action="newsletter_select_layout",
        system_prompt=_P1_SYSTEM.format(brand_name=brand_name, tone_rules=tone_rules, today=today),
        task_type="creative",
        temperature=0.6,
    )

    layout: str = p1_result.get("layout", "digest")
    if layout not in ("digest", "single_story", "announcement"):
        layout = "digest"
    layout_rationale: str = p1_result.get("layout_rationale", "")
    selected_item_ids: list[str] = p1_result.get("selected_item_ids", [it["id"] for it in items[:6]])
    p1_sections: list[dict] = p1_result.get("sections", [])
    intro_angle: str = p1_result.get("intro_angle", "")
    closing_angle: str = p1_result.get("closing_angle", "")

    # ── Pass 2: Draft ─────────────────────────────────────────────────────────
    logger.info("[Pass 2] Writing draft copy (layout=%s)", layout)
    p2_result = await call_llm_with_json(
        prompt=_P2_USER.format(
            layout=layout,
            sections_json=json.dumps(p1_sections, ensure_ascii=False),
            intro_angle=intro_angle,
            closing_angle=closing_angle,
        ),
        brand_id=brand_id,
        context="newsletter_p2_draft",
        action="newsletter_draft",
        system_prompt=_P2_SYSTEM.format(brand_name=brand_name, tone_rules=tone_rules),
        task_type="creative",
        temperature=0.75,
    )

    nl_title: str = p2_result.get("title", f"{brand_name} Weekly")

    # ── Pass 3: Refinement ────────────────────────────────────────────────────
    logger.info("[Pass 3] Refining copy")
    try:
        p3_result = await call_llm_with_json(
            prompt=_P3_USER.format(draft_json=json.dumps(p2_result, ensure_ascii=False)),
            brand_id=brand_id,
            context="newsletter_p3_refine",
            action="newsletter_refine",
            system_prompt=_P3_SYSTEM.format(brand_name=brand_name, tone_rules=tone_rules),
            task_type="creative",
            temperature=0.5,
        )
        refined = p3_result
    except Exception as exc:
        logger.warning("[Pass 3] Refinement failed (%s) — using Pass 2 output", exc)
        refined = p2_result

    nl_title = refined.get("title", nl_title)
    nl_intro: str = refined.get("intro", "")
    nl_sections: list[dict] = refined.get("sections", [])
    nl_closing: str = refined.get("closing", "")

    # ── Pass 4: Subject variants ──────────────────────────────────────────────
    logger.info("[Pass 4] Generating A/B subject lines")
    topics = ", ".join(s.get("label", "") for s in nl_sections if s.get("label"))
    subject_a = nl_title
    subject_b: str | None = None
    past_perf = _build_past_performance_block(db, brand_id)
    try:
        p4_result = await call_llm_with_json(
            prompt=_P4_USER.format(
                title=nl_title,
                topics=topics,
                brand_name=brand_name,
                past_performance_block=past_perf,
            ),
            brand_id=brand_id,
            context="newsletter_p4_subjects",
            action="newsletter_subjects",
            system_prompt=_P4_SYSTEM,
            task_type="creative",
            temperature=0.8,
        )
        subject_a = p4_result.get("subject_a") or nl_title
        subject_b = p4_result.get("subject_b") or None
    except Exception as exc:
        logger.warning("[Pass 4] Subject generation failed (%s)", exc)

    # ── Render HTML via React Email ────────────────────────────────────────────
    email_content = {
        "title": nl_title,
        "intro": nl_intro,
        "sections": nl_sections,
        "closing": nl_closing,
        "editionNumber": edition_number,
    }
    brand_theme["brandName"] = brand_name
    html_body = await _render_html(layout, email_content, brand_theme)
    if not html_body:
        html_body = _build_html_fallback(brand_name, edition_number, email_content)

    # ── Persist ────────────────────────────────────────────────────────────────
    insert_payload: dict[str, Any] = {
        "brand_id": brand_id,
        "title": nl_title,
        "edition_number": edition_number,
        "html_body": html_body,
        "status": "draft",
        "layout_type": layout,
        "subject_variant_a": subject_a,
        "subject_variant_b": subject_b,
    }
    insert_resp = db.table("newsletters").insert(insert_payload).execute()
    newsletter_row = (insert_resp.data or [{}])[0]
    newsletter_id = newsletter_row.get("id")

    if not newsletter_id:
        logger.error("Newsletter INSERT did not return id for brand %s", brand_id)
        return {"ok": False, "reason": "db_insert_failed"}

    # Candidates
    if selected_item_ids:
        db.table("newsletter_candidates").insert([
            {"newsletter_id": newsletter_id, "research_item_id": iid, "slot_type": "editorial", "selected": True}
            for iid in selected_item_ids
        ]).execute()

    # Memory event
    try:
        db.table("memory_events").insert({
            "brand_id": brand_id,
            "event_kind": "newsletter_generated",
            "subject_kind": "newsletter",
            "subject_id": newsletter_id,
            "summary": f"Newsletter draft #{edition_number} generated: {nl_title}",
            "payload": {
                "edition_number": edition_number,
                "layout": layout,
                "layout_rationale": layout_rationale,
                "sections_count": len(nl_sections),
                "selected_items": len(selected_item_ids),
                "subject_a": subject_a,
                "subject_b": subject_b,
            },
        }).execute()
    except Exception as exc:
        logger.warning("Failed to log memory_event for newsletter %s: %s", newsletter_id, exc)

    try:
        await emit_event(
            event_type="newsletter_draft_generated",
            title=f"Newsletter Draft: {nl_title}",
            severity="info",
            brand_id=brand_id,
            detail={
                "edition": edition_number,
                "layout": layout,
                "sections": len(nl_sections),
                "subject_a": subject_a,
                "subject_b": subject_b or "",
            },
            entity_type="newsletter",
            entity_id=newsletter_id,
        )
    except Exception:
        pass

    return {
        "ok": True,
        "newsletter_id": newsletter_id,
        "edition_number": edition_number,
        "title": nl_title,
        "layout": layout,
        "layout_rationale": layout_rationale,
        "subject_a": subject_a,
        "subject_b": subject_b,
        "sections_count": len(nl_sections),
    }
