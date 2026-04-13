"""Writer Agent — generates content from approved research items using Claude Opus."""

from __future__ import annotations

import json

from ..db import get_db
from ..utils.cost_tracker import track_cost
from ..utils.llm_client import call_llm
from ..utils.security_utils import sanitize_for_prompt  # H-07: prompt injection guard

WRITER_PROMPT = """<identity>
You are the Writer for {brand_name} — the founder's right hand in digital communication.
Your expertise is transforming industry insights into scroll-stopping content.
Your goal is to build a bridge between the founder's expertise and the reader's specific pain point, making them say "this is about me".
</identity>

<context>
Target Platform: {platform}
Content Type: {content_type}
Length Guideline: {length_hint}

Content Data:
Title: {title}
Original Source: {source_name}
Key Insight: {summary}
</context>

<instructions>
1. Analyze the Context data perfectly.
2. Draft an original piece of content based exclusively on the Key Insight.
3. Write entirely in Italian (it's crucial for the Italian audience).
4. Apply the brand's tone of voice and principles perfectly.
</instructions>

<guidelines>
- Tone of Voice:
{tone_rules}
- Brand Principles:
{principles}
- Standards:
  - Create a magnetic hook in the first sentence to grab attention.
  - Ensure every sentence adds tangible value.
  - Prioritize concrete data over vague opinions.
  - End with a clear and actionable call to action (CTA).
- Language: Italian ONLY.
</guidelines>

<verification>
Check yourself before outputting:
- Is the language strictly Italian?
- Is the content completely original and not just a recycled summary?
- Does it strictly adhere to the {length_hint} guideline for {platform}?
If you cannot fulfill the request due to missing insight, output "I do not have enough context to write this." in the body.
</verification>

<output_format>
Return ONLY a valid JSON object matching this schema. Do not include markdown codeblocks outside the JSON.
{{
  "title": "A captivating title",
  "body": "The complete formatted content with paragraphs and line breaks",
  "hooks": ["Alternative hook 1", "Alternative hook 2"],
  "cta": "The final call to action",
  "hashtags": ["hashtag1", "hashtag2", "hashtag3"]
}}

<example>
{{
  "title": "Perché le metriche vanity stanno uccidendo la tua azienda",
  "body": "Tutti festeggiano i follower. Nessuno festeggia il fatturato.\\n\\nHo visto startup chiudere con 100k follower su Instagram. Il motivo? Non avevano costruito un modello di business, avevano costruito una tribù digitale.\\n\\nEcco i 3 KPI che devi guardare oggi:\\n1. CAC (Cost of Customer Acquisition)\\n2. LTV (Life Time Value)\\n3. Churn Rate\\n\\nLascia i like agli influencer. Costruisci un'azienda vera.",
  "hooks": ["Hai 100k follower. E stai per fallire.", "Smettila di esultare per i like. Guarda il CAC."],
  "cta": "Iscriviti alla newsletter per altre analisi.",
  "hashtags": ["#startup", "#kpi", "#marketing"]
}}
</example>
</output_format>
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
        # H-07: sanitize web-scraped fields before inserting into the LLM prompt
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
