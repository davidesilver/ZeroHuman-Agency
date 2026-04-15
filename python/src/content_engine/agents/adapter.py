"""Adapter Agent — adapts content for different platforms."""

from __future__ import annotations

import json

from ..utils.llm_client import call_llm
from ..db import get_db
from .agent_loader import get_agent_identity  # Fase 1: Use DB-based identity loader

# Base prompt template without identity section (identity will be loaded dynamically)
ADAPTER_PROMPT_BASE = """<context>
Original Platform: {source_platform}
Target Platform: {target_platform}
Required Tone: {tone_hint}

Original Content:
Title: {title}
{body}
</context>

<instructions>
1. Analyze original content to extract core insight and message.
2. Completely adapt and rewrite content for {target_platform}.
3. Apply to {target_platform} rules flawlessly.
4. Output rewritten text in Italian.
</instructions>

<guidelines>
- Preserve of core insight and value of original message.
- Drastically change to format, flow, and structure to match to {target_platform}.
- Maintain of {tone_hint} voice.
- Output to content body in Italian.
</guidelines>

<verification>
Check yourself before outputting:
- Does this text look like a native post on {target_platform}?
- Does it strictly obey to provided rules: "{platform_rules}"?
- If original context is empty, write "Original content is missing." in body.
</verification>

<output_format>
Return ONLY a valid JSON object matching this schema. Do not include markdown codeblocks outside of JSON.
{
  "title": "Adapted title",
  "body": "The complete adapted content body, properly formatted for target platform",
  "hashtags": ["tag1", "tag2"]
}

<example>
{
  "title": "Il lavoro da remoto non è vacanza",
  "body": "Il lavoro da remoto non è vacanza. È un'opportunità che richiede fiducia, comunicazione chiara e strumenti giusti.\\n\\nEcco 3 strumenti che ogni smart worker deve avere:\\n1. Zoom/Meet per meeting chiari\\n2. Slack/Teams per async chat\\n3. Notion/Trello per task tracking.\\n\\nSenza questi, il lavoro remoto diventa un incubo di incomprensioni.",
  "hashtags": ["#SmartWorking", "#RemoteWork", "#Produttivita"]
}
</example>
</output_format>
"""

PLATFORM_RULES = {
    "linkedin": "Max 3000 char (ideale 1200-1500). Line break frequenti. Tono professionale ma accessibile. Hook forte in prima riga (pre-\"vedi altro\"). Emoji moderate.",
    "x": "Max 280 char per tweet. Thread se necessario (max 10). Primo tweet deve funzionare standalone. Tono diretto e pungente. Emoji come \"bullet point\". Retweet-friendly frasi. Max 2 hashtag.",
    "instagram": "Caption max 2200 char. Caption + suggerimento immagine/carousel. Hashtag nel primo commento, non nella caption. 15-20 hashtag misti (5 ampi, 10 di nicchia, 5 branded). Suggerisci \"salva questo post\" per metriche.",
    "facebook": "Ideale 100-250 char. Breve e conversazionale. Domanda finale per stimolare commenti. Nessun hashtag o massimo 1-2. Adatto a condivisione.",
    "tiktok": "Caption 2200 char. Script video + caption. Hook nei primi 3 secondi. Tono energico e visuale. Hashtag nel caption (3-5). Trending sounds.",
    "blog": "1500-3000 parole. Strutturato con H2/H3. SEO-friendly. Intro con hook, conclusione con CTA. Internal linking. Immagini inline o in blocco.",
    "email": "600-800 parole. Sezione newsletter. Apri con insight, chiudi con action. Preview text. Unsubscribe link fisso. Personalizzazione {name}.",
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

    # Fase 1: Load agent identity from DB (or fallback hardcoded)
    identity = await get_agent_identity(brand_id, "adapter")

    # Build complete prompt with identity
    full_prompt = f"""<identity>
{identity}
</identity>

{ADAPTER_PROMPT_BASE}
"""

    results = []
    for target in target_platforms:
        if target == draft_data.get("platform"):
            continue

        prompt = full_prompt.format(
            brand_name=brand_data.get("name", ""),
            source_platform=draft_data.get("platform", ""),
            target_platform=target,
            tone_hint=tone_hint,
            # H-07: draft fields may contain web-scraped content — sanitize before LLM injection
            title=draft_data.get("title", ""),
            body=draft_data.get("body", ""),
            platform_rules=PLATFORM_RULES.get(target, ""),
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
