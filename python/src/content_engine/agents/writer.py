"""Writer Agent — generates content from approved research items using Claude Opus."""

from __future__ import annotations

import json

from ..scoring.engine import _call_llm
from ..db import get_db
from ..utils.cost_tracker import track_cost

WRITER_PROMPT = """Sei un content writer esperto per il brand "{brand_name}".

## Tono di voce
{tone_rules}

## Principi del founder
{principles}

## Contenuto sorgente
Titolo: {title}
Fonte: {source_name}
Summary: {summary}

## Istruzioni
Scrivi un contenuto originale in italiano per la piattaforma {platform} (tipo: {content_type}).
NON copiare dal sorgente. Rielabora completamente.

Regole:
- Apri con un hook forte che cattura l'attenzione
- Usa dati concreti quando disponibili
- Chiudi con un invito all'azione
- Lunghezza adatta alla piattaforma: {length_hint}
- Lingua: italiano

Rispondi SOLO in JSON:
{{
  "title": "titolo accattivante",
  "body": "contenuto completo formattato",
  "hooks": ["hook alternativo 1", "hook alternativo 2"],
  "cta": "call to action finale",
  "hashtags": ["hashtag1", "hashtag2", "hashtag3"]
}}
"""

PLATFORM_LENGTH = {
    "linkedin": "1200-1500 caratteri, line break frequenti",
    "x": "280 caratteri max (thread se necessario)",
    "instagram": "caption 500-800 caratteri + suggerimento visuale",
    "facebook": "100-250 caratteri, conversazionale",
    "tiktok": "script video 30-60 secondi",
    "blog": "1500-3000 parole, strutturato con H2/H3",
    "email": "600-800 parole per sezione newsletter",
}


async def generate_draft(
    brand_id: str,
    research_item_id: str,
    platform: str = "linkedin",
    content_type: str = "post",
) -> dict:
    db = get_db()

    brand = db.table("brands").select("*").eq("id", brand_id).single().execute()
    brand_data = brand.data

    item = db.table("research_items").select("*").eq("id", research_item_id).single().execute()
    item_data = item.data

    tone = brand_data.get("tone_of_voice") or {}
    tone_rules = "\n".join(f"- {r}" for r in (tone.get("rules") or []))
    principles = (brand_data.get("scoring_weights") or {}).get("founder_principles", [])

    prompt = WRITER_PROMPT.format(
        brand_name=brand_data.get("name", ""),
        tone_rules=tone_rules or "Diretto, pratico, entusiasta",
        principles="\n".join(f"- {p}" for p in principles),
        title=item_data.get("title", ""),
        source_name=item_data.get("source_name", ""),
        summary=item_data.get("summary", ""),
        platform=platform,
        content_type=content_type,
        length_hint=PLATFORM_LENGTH.get(platform, "medio"),
    )

    raw = await _call_llm(prompt)
    await track_cost(brand_id, "opus_writer", "claude-opus-4-20250514", "generate_draft", len(prompt), len(raw))

    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        text = text.rsplit("```", 1)[0]
    parsed = json.loads(text)

    draft_row = db.table("content_drafts").insert({
        "brand_id": brand_id,
        "research_item_id": research_item_id,
        "content_type": content_type,
        "platform": platform,
        "title": parsed.get("title", ""),
        "body": parsed.get("body", ""),
        "status": "draft",
        "version": 1,
    }).execute()

    return {
        "draft": draft_row.data[0],
        "hooks": parsed.get("hooks", []),
        "cta": parsed.get("cta", ""),
        "hashtags": parsed.get("hashtags", []),
    }
