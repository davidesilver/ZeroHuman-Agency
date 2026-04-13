"""Editor Agent — reviews and improves drafts."""

from __future__ import annotations

import json

from ..db import get_db
from ..utils.cost_tracker import track_cost
from ..utils.llm_client import call_llm
from ..utils.security_utils import sanitize_for_prompt         # H-07

EDITOR_PROMPT = """Sei un editor professionista per il brand "{brand_name}".

## Draft da revisionare
Titolo: {title}
Piattaforma: {platform}
Contenuto:
{body}

## Istruzioni
Migliora questo draft:
1. Correggi errori grammaticali e stilistici
2. Migliora il flusso narrativo
3. Rafforza hook e call-to-action
4. Riduci ridondanze
5. Mantieni il tono: {tone_hint}

Rispondi SOLO in JSON:
{{
  "title": "titolo migliorato (o originale se ok)",
  "body": "contenuto completo rivisto",
  "changes_summary": "breve sommario delle modifiche fatte",
  "changes_count": <numero modifiche>
}}
"""


async def edit_draft(brand_id: str, draft_id: str) -> dict:
    db = get_db()

    draft = db.table("content_drafts").select("*").eq("id", draft_id).single().execute()
    draft_data = draft.data

    brand = db.table("brands").select("*").eq("id", brand_id).single().execute()
    brand_data = brand.data


    tone = brand_data.get("tone_of_voice") or {}
    tone_hint = ", ".join(tone.get("personality") or ["diretto", "pratico"])

    prompt = EDITOR_PROMPT.format(
        brand_name=brand_data.get("name", ""),
        # H-07: draft fields may contain web-scraped content — sanitize before LLM injection
        title=sanitize_for_prompt(draft_data.get("title", ""), context="draft.title"),
        platform=draft_data.get("platform", ""),
        body=sanitize_for_prompt(draft_data.get("body", ""), context="draft.body"),
        tone_hint=tone_hint,
    )

    raw_res = await call_llm(
        prompt=prompt,
        brand_id=brand_id,
        context="editor_agent",
        action="edit_draft",
        task_type="creative"
    )
    raw = raw_res.content

    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        text = text.rsplit("```", 1)[0]
    parsed = json.loads(text)

    new_version = (draft_data.get("version") or 1) + 1
    db.table("content_drafts").update({
        "title": parsed.get("title", draft_data["title"]),
        "body": parsed.get("body", draft_data["body"]),
        "version": new_version,
        "status": "in_review",
    }).eq("id", draft_id).execute()

    return {
        "draft_id": draft_id,
        "version": new_version,
        "changes_summary": parsed.get("changes_summary", ""),
        "changes_count": parsed.get("changes_count", 0),
    }

