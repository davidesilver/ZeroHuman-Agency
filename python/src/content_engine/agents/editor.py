"""Editor Agent — reviews and improves drafts."""

from __future__ import annotations

import json

from ..db import get_db
from ..utils.cost_tracker import track_cost
from ..utils.llm_client import call_llm
from ..utils.security_utils import sanitize_for_prompt         # H-07
from .agent_loader import get_agent_identity  # Fase 1: Use DB-based identity loader

# Base prompt template without identity section (identity will be loaded dynamically)
EDITOR_PROMPT_BASE = """<context>
Target Platform: {platform}
Required Tone: {tone_hint}

Content Draft:
Title: {title}
Body:
{body}
</context>

<instructions>
1. Review of Content Draft carefully.
2. Edit of the draft to eliminate errors, improve sentence rhythm and ensure effortless narrative flow.
3. Sharpen of hook and CTA to evoke immediate emotion.
4. Cut any redundant phrases or sentences that do not add clear insight.
5. Provide final rewritten content entirely in Italian.
</instructions>

<guidelines>
- Ensure perfect Italian grammar and syntax.
- Maintain specified tone exactly: {tone_hint}.
- Maximize the "density of value" — less fluff, more impact.
- Make bold changes if text is weak; refine details if it is strong.
- Language: output body in Italian.
</guidelines>

<verification>
Check yourself before outputting:
- Are there any remaining grammatical errors?
- Is the tone of voice perfectly matching "{tone_hint}"?
- Does every paragraph transition smoothly into the next?
- If the original text is completely nonsensical, output "I cannot edit this text as it lacks coherence." in body.
</verification>

<output_format>
Return ONLY a valid JSON object matching this schema. Do not include markdown codeblocks outside of JSON.
{
  "title": "Improved title (or original if it was good)",
  "body": "The complete revised content body",
  "changes_summary": "English summary of modifications made",
  "changes_count": 3
}

<example>
{
  "title": "Il futuro del B2B",
  "body": "Nel 2025, le vendite B2B cambieranno per sempre. Siamo abituati a cicli di vendita lunghi e call infinite. Ma il compratore moderno vuole un'esperienza zero-touch.\\n\\nCosa significa per te?\\n\\nIl tuo sito web non è più una brochure. È il tuo miglior venditore. Sfruttalo.",
  "changes_summary": "Shortened to sentences for impact, improved paragraph rhythm, and made to hook punchier.",
  "changes_count": 5
}
</example>
</output_format>
"""


async def edit_draft(brand_id: str, draft_id: str) -> dict:
    db = get_db()

    draft = db.table("content_drafts").select("*").eq("id", draft_id).single().execute()
    draft_data = draft.data

    brand = db.table("brands").select("*").eq("id", brand_id).single().execute()
    brand_data = brand.data

    tone = brand_data.get("tone_of_voice") or {}
    tone_hint = ", ".join(tone.get("personality") or ["diretto", "pratico"])

    # Fase 1: Load agent identity from DB (or fallback hardcoded)
    identity = await get_agent_identity(brand_id, "editor")

    # Build complete prompt with identity
    full_prompt = f"""<identity>
{identity}
</identity>

{EDITOR_PROMPT_BASE}
"""

    prompt = full_prompt.format(
        brand_name=brand_data.get("name", ""),
        tone_hint=tone_hint,
        # H-07: draft fields may contain web-scraped content — sanitize before LLM injection
        title=sanitize_for_prompt(draft_data.get("title", ""), context="draft.title"),
        platform=draft_data.get("platform", ""),
        body=sanitize_for_prompt(draft_data.get("body", ""), context="draft.body"),
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
