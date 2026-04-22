"""Writer Agent — generates content from approved research items using Claude Opus."""

from __future__ import annotations

import json

from ..db import get_db
from ..memory.retrieval import recall as memory_recall
from ..utils.cost_tracker import track_cost
from ..utils.llm_client import call_llm
from ..utils.security_utils import sanitize_for_prompt  # H-07: prompt injection guard
from .agent_loader import get_agent_identity  # Fase 1: Use DB-based identity loader

# Base prompt template without identity section (identity will be loaded dynamically)
WRITER_PROMPT_BASE = """<context>
Target Platform: {platform}
Content Type: {content_type}
Length Guideline: {length_hint}

Content Data:
Title: {title}
Original Source: {source_name}
Key Insight: {summary}
</context>

<instructions>
1. Analyze Context data perfectly.
2. Draft an original piece of content based exclusively on Key Insight.
3. Write entirely in Italian (it's crucial for Italian audience).
4. Apply brand's tone of voice and principles perfectly.
</instructions>

<guidelines>
- Tone of Voice:
{tone_rules}
- Brand Principles:
{principles}
- Standards:
  - Create a magnetic hook in first sentence to grab attention.
  - Ensure every sentence adds tangible value.
  - Prioritize concrete data over vague opinions.
  - End with a clear and actionable call to action (CTA).
  - Language: Italian ONLY.
</guidelines>

<verification>
Check yourself before outputting:
- Is language strictly Italian?
- Is content completely original and not just a recycled summary?
- Does it strictly adhere to {length_hint} guideline for {platform}?
If you cannot fulfill request due to missing insight, output "I do not have enough context to write this." in body.
</verification>

<output_format>
Return ONLY a valid JSON object matching this schema. Do not include markdown codeblocks outside of JSON.
{{
  "title": "A captivating title",
  "body": "The complete formatted content with paragraphs and line breaks",
  "hooks": ["Alternative hook 1", "Alternative hook 2"],
  "cta": "The final call to action",
  "hashtags": ["hashtag1", "hashtag2", "hashtag3"]
}}
</output_format>

<example>
{{
  "title": "Perché le metriche vanity stanno uccidendo la tua azienda",
  "body": "Tutti festeggiano i follower. Nessuno festeggia il fatturato.\\n\\nHo visto startup chiudere con 100k follower su Instagram. Il motivo? Non avevano costruito un modello di business, avevano costruito una tribù digitale.\\n\\nEcco i 3 KPI che devi guardare oggi:\\n1. CAC (Cost of Customer Acquisition)\\n2. LTV (Life Time Value)\\n3. Churn Rate\\n\\nLascia i like agli influencer. Costruisci un'azienda vera.",
  "hooks": ["Hai 100k follower. E stai per fallire.", "Smettila di esultare per i like. Guarda il CAC."],
  "cta": "Iscriviti alla newsletter per altre analisi.",
  "hashtags": ["#startup", "#kpi", "#marketing"]
}}
</example>
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

    # P3.7: prefer memory-native facts over static JSON columns; fall back if empty
    tone_facts = await memory_recall(brand_id, "tone of voice writing rules style", kind="tone_rule", k=5)
    if tone_facts:
        tone_rules = "\n".join(f"- {f['statement']}" for f in tone_facts)
    else:
        tone = brand_data.get("tone_of_voice") or {}
        tone_rules = "\n".join(f"- {r}" for r in (tone.get("rules") or []))

    principle_facts = await memory_recall(brand_id, "brand founding principles values mission", kind="principle", k=5)
    if principle_facts:
        principles = [f["statement"] for f in principle_facts]
    else:
        principles = (brand_data.get("scoring_weights") or {}).get("founder_principles", [])

    # Fase 1: Load agent identity from DB (or fallback hardcoded)
    identity = await get_agent_identity(brand_id, "writer")

    # Build complete prompt with identity
    full_prompt = f"""<identity>
{identity}
</identity>

{WRITER_PROMPT_BASE}
"""

    prompt = full_prompt.format(
        brand_name=brand_data.get("name", ""),
        tone_rules=tone_rules or "Diretto, pratico, entusiast",
        principles="\n".join(f"- {p}" for p in principles),
        # H-07: sanitize web-scraped fields before inserting into LLM prompt
        title=sanitize_for_prompt(item_data.get("title", ""), context="research_item.title"),
        source_name=sanitize_for_prompt(item_data.get("source_name", ""), context="research_item.source_name"),
        summary=sanitize_for_prompt(item_data.get("summary", ""), context="research_item.summary"),
        platform=platform,
        content_type=content_type,
        length_hint=PLATFORM_LENGTH.get(platform, "medio"),
    )

    raw_res = await call_llm(
        prompt=prompt,
        brand_id=brand_id,
        context="writer_agent",
        action="generate_draft",
        task_type="creative"
    )
    raw = raw_res.content

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


# Bug 0.2 Fix: Export for auto-optimizer
__all__ = ["WRITER_PROMPT_BASE", "generate_draft"]
