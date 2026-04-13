"""Adapter Agent — adapts content for different platforms."""

from __future__ import annotations

import json

from ..utils.llm_client import call_llm
from ..db import get_db

ADAPTER_PROMPT = """<identity>
You are the Platform Adapter for the brand — a specialist in native platform language.
You deeply understand the rhythm, structure, and implicit rules of {target_platform}.
Your goal is to completely rewrite content so it feels natively born on {target_platform}, not just resized or copy-pasted.
</identity>

<context>
Original Platform: {source_platform}
Target Platform: {target_platform}
Required Tone: {tone_hint}

Platform Rules for {target_platform}:
{platform_rules}

Original Content:
Title: {title}
{body}
</context>

<instructions>
1. Analyze the original content to extract the core insight and message.
2. Completely adapt and rewrite the content for {target_platform}.
3. Apply the {target_platform} rules flawlessly.
4. Output the rewritten text in Italian.
</instructions>

<guidelines>
- Preserve the core insight and value of the original message.
- Drastically change the format, flow, and structure to match the {target_platform} expectations.
- Maintain the {tone_hint} voice.
- Output the content body in Italian.
</guidelines>

<verification>
Check yourself before outputting:
- Does this text look like a native post on {target_platform}?
- Does it strictly obey the provided rules: "{platform_rules}"?
- If the original context is empty, write "Original content is missing." in the body.
</verification>

<output_format>
Return ONLY a valid JSON object matching this schema. Do not include markdown codeblocks outside the JSON.
{{
  "title": "Adapted title",
  "body": "The complete adapted content body, properly formatted for the target platform",
  "hashtags": ["tag1", "tag2"]
}}

<example>
{{
  "title": "Thread: 3 rules for remote work",
  "body": "Il lavoro da remoto non è una vacanza.\\n\\nÈ una disciplina.\\n\\nEcco la mia routine in 3 step per non impazzire (e fatturare). 🧵👇\\n\\n1. Vestiti come se dovessi uscire. Niente pigiama. Il cervello ha bisogno di interruttori.\\n\\n2. Blocca il calendario. 90 minuti di deep work > 8 ore di distrazioni.\\n\\n3. Spegni le notifiche. Il mondo non esplode se rispondi 2 ore dopo.\\n\\nTu che regole hai per sopravvivere allo smart working? Dimmelo sotto.",
  "hashtags": ["#SmartWorking", "#Produttivita", "#Remote"]
}}
</example>
</output_format>
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
