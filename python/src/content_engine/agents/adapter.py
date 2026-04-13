"""Adapter Agent — adapts content for different platforms."""

from __future__ import annotations

import json

from ..utils.llm_client import call_llm
from ..db import get_db

ADAPTER_PROMPT = """Adatta il seguente contenuto per la piattaforma {target_platform}.

## Contenuto originale (piattaforma: {source_platform})
Titolo: {title}
{body}

## Regole piattaforma {target_platform}
{platform_rules}

## Tono di voce
{tone_hint}

Rispondi SOLO in JSON:
{{
  "title": "titolo adattato",
  "body": "contenuto adattato per {target_platform}",
  "hashtags": ["tag1", "tag2"]
}}
"""

PLATFORM_RULES = {
    "linkedin": "Max 3000 char (ideale 1200-1500). Line break frequenti. Tono professionale ma accessibile. Hook forte in prima riga. Emoji moderate.",
    "x": "Max 280 char per tweet. Thread se necessario (max 10). Primo tweet deve funzionare standalone. Tono diretto e incisivo.",
    "instagram": "Caption max 2200 char (ideale 500-800). Hashtag nel primo commento, non nella caption. Suggerisci tipo di immagine.",
    "facebook": "Ideale 100-250 char. Breve e conversazionale. Chiudi con domanda per engagement.",
    "tiktok": "Script video 30-60 sec. Hook nei primi 3 secondi. Tono energico e diretto.",
    "blog": "1500-3000 parole. Struttura con H2/H3. SEO-friendly. Intro con hook, conclusione con CTA.",
    "email": "600-800 parole. Sezione newsletter. Apri con insight, chiudi con takeaway pratico.",
}


async def adapt_content(
    brand_id: str,
    draft_id: str,
    target_platforms: list[str],
) -> list[dict]:
    db = get_db()

    draft = db.table("content_drafts").select("*").eq("id", draft_id).single().execute()
    draft_data = draft.data

    brand = db.table("brands").select("*").eq("id", brand_id).single().execute()
    brand_data = brand.data

    tone = brand_data.get("tone_of_voice") or {}
    tone_hint = ", ".join(tone.get("personality") or ["diretto", "pratico"])

    results = []
    for target in target_platforms:
        if target == draft_data.get("platform"):
            continue

        prompt = ADAPTER_PROMPT.format(
            target_platform=target,
            source_platform=draft_data.get("platform", ""),
            title=draft_data.get("title", ""),
            body=draft_data.get("body", ""),
            platform_rules=PLATFORM_RULES.get(target, ""),
            tone_hint=tone_hint,
        )

        raw_res = await call_llm(
            prompt=prompt,
            brand_id=brand_id,
            context="content_adapter",
            action="adapt_content",
            task_type="language"
        )
        raw = raw_res.content
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            text = text.rsplit("```", 1)[0]
        parsed = json.loads(text)

        adapted = db.table("content_drafts").insert({
            "brand_id": brand_id,
            "research_item_id": draft_data.get("research_item_id"),
            "content_type": draft_data.get("content_type", "post"),
            "platform": target,
            "title": parsed.get("title", ""),
            "body": parsed.get("body", ""),
            "parent_draft_id": draft_id,
            "status": "draft",
            "version": 1,
        }).execute()

        results.append(adapted.data[0])

    return results
