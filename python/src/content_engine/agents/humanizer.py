"""Humanizer Agent — removes AI patterns and applies brand voice calibration.

Based on blader/humanizer SKILL.md, implements:
- 29 anti-AI patterns from Wikipedia's "Signs of AI writing"
- Voice calibration using brand's gold_examples (manual) + top performers (automatic)
- Double-pass: initial rewrite → anti-AI audit → final revision
- Soul injection: adds personality, opinions, and natural rhythm
- Explicit model override option (bypasses default routing)

Position in pipeline: after god_system, before publisher/adapter.

Cost estimation:
- Pass 1 (initial): ~$0.001-0.002 (Gemma 4 free) or ~$0.003-0.005 (Haiku)
- Pass 2 (audit): ~$0.001-0.002 (Gemma 4 free) or ~$0.002-0.003 (Haiku)
- Total: ~$0.002-0.004 (free model) or ~$0.005-0.008 (Haiku)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from ..db import get_db
from ..memory.retrieval import recall as memory_recall
from ..utils.llm_client import LLMResponse, call_llm
from ..utils.security_utils import sanitize_for_prompt
from .agent_loader import get_agent_identity

logger = logging.getLogger("content_engine.humanizer")

# Load the Humanizer skill instructions
_HUMANIZER_SKILL_PATH = Path(__file__).parent.parent / "prompts" / "skills" / "humanizer_skill.md"
_HUMANIZER_SKILL_TEXT = _HUMANIZER_SKILL_PATH.read_text() if _HUMANIZER_SKILL_PATH.exists() else ""

# Base prompt template
HUMANIZER_PROMPT_BASE = """<context>
Target Platform: {platform}
Content Type: {content_type}

Content to Humanize:
Title: {title}
Body:
{body}
</context>

<voice_calibration>
{voice_calibration_text}
</voice_calibration>

<instructions>
Apply the Humanizer patterns above to the content:
1. Identify and remove all AI-isms from the 29 patterns
2. Rewrite problematic sections with natural alternatives
3. Match the voice calibration sample (sentence length, word choice, transitions)
4. Preserve the core message completely
5. Add soul: opinions, varied rhythm, first-person perspective where appropriate
6. Output entirely in Italian
</instructions>

<guidelines>
- The anti-AI patterns above are in English, but you must apply them to ITALIAN text
- Adapt patterns to Italian linguistic structures (e.g., "inoltre/peraltro/d'altronde" are normal Italian, not AI-isms)
- Focus on Italian AI-tells: overuse of formal connectors, passive constructions, impersonal "si" constructions
- The voice calibration sample is your reference for tone and rhythm
- Language: output body in Italian ONLY
</guidelines>

<verification>
Check yourself before outputting:
- Did you remove AI patterns without destroying meaning?
- Does the voice match the calibration sample?
- Is the text in flawless, natural Italian?
- Does it have a human pulse (opinions, varied rhythm, personality)?
</verification>

<output_format>
Return ONLY a valid JSON object matching this schema. Do not include markdown codeblocks outside of JSON.
{{
  "title": "Humanized title (or original if already natural)",
  "body": "Complete humanized content body in Italian",
  "ai_patterns_found": ["list of AI patterns detected and fixed"],
  "changes_summary": "English summary of humanization applied"
}}

<example>
{{
  "title": "Il vero costo del turnover",
  "body": "Perdere un dipendente ti costa il 30% del suo stipendio annuale.\\n\\nNon lo dico io, lo dicono i bilanci. Eppure le aziende continuano a tagliare il budget per la formazione.\\n\\nEcco come invertire la rotta in 2 mesi...",
  "ai_patterns_found": ["Overuse of formal connectors", "Passive voice", "Generic positive conclusion"],
  "changes_summary": "Removed formal 'inoltre/peraltro', replaced passive with active voice, added first-person opinion for personality"
}}
</example>
</output_format>
"""


# Anti-AI audit prompt (second pass)
ANTI_AI_AUDIT_PROMPT = """<context>
Content After First Humanization Pass:
Title: {title}
Body:
{body}
</context>

<instructions>
This is your ANTI-AI AUDIT. Do one thing:

Ask yourself: "What makes this text obviously AI generated?"

Answer briefly (1-2 sentences in English) with the remaining AI-tells you still see.

Then answer: "Now make it not obviously AI generated."

Rewrite the content to fix those remaining issues. Be ruthless.
</instructions>

<output_format>
Return ONLY a valid JSON object matching this schema. Do not include markdown codeblocks outside of JSON.
{{
  "remaining_ai_tells": ["AI patterns still visible after first pass"],
  "body": "Final humanized content with all AI-tells removed",
  "audit_summary": "English summary of what was fixed in second pass"
}}
"""


async def _load_voice_calibration(brand_id: str) -> str:
    """Load voice calibration using semantic memory first, then static DB fallback.

    Priority:
    1. Semantic memory: tone_rule facts + gold_example facts via memory.recall()
    2. Manual gold_examples in brands.tone_of_voice.gold_examples (highest-priority static)
    3. Automatic: top-3 performing content from content_performance (fallback)
    4. Default natural voice if nothing is available

    Returns:
        Formatted text with voice calibration samples
    """
    # 1. Try semantic memory first (highest priority)
    try:
        tone_facts = await memory_recall(
            brand_id,
            "brand voice tone rules writing style",
            kind="tone_rule",
            k=3,
        )
        gold_facts = await memory_recall(
            brand_id,
            "gold example best content sample",
            kind="gold_example",
            k=3,
        )

        if tone_facts or gold_facts:
            parts = []
            if tone_facts:
                parts.append("# Voice Rules (from Brand Memory)")
                for i, f in enumerate(tone_facts, 1):
                    parts.append(f"## Rule {i}\n{f['statement']}")
            if gold_facts:
                parts.append("# Gold Examples (from Brand Memory)")
                for i, f in enumerate(gold_facts, 1):
                    parts.append(f"## Example {i}\n{f['statement']}")
            logger.info(
                "Using memory calibration for brand %s: %d tone rules, %d gold examples",
                brand_id, len(tone_facts), len(gold_facts),
            )
            return "\n\n".join(parts)

    except Exception as e:
        logger.warning("Memory recall failed for brand %s, falling back to DB: %s", brand_id, e)

    # 2–4. Static DB fallback (original logic preserved exactly)
    try:
        db = get_db()

        # 2. Try manual gold_examples from brand config (highest priority)
        brand = db.table("brands").select("tone_of_voice").eq("id", brand_id).single().execute()

        if brand.data and brand.data.get("tone_of_voice"):
            tone_data = brand.data["tone_of_voice"]
            gold_examples = tone_data.get("gold_examples", [])

            if gold_examples:
                samples = []
                for i, example in enumerate(gold_examples[:3], 1):  # Max 3 examples
                    samples.append(f"""
## Manual Gold Example {i}
{example.get("title", "Untitled")}

{example.get("content", example.get("body", ""))}
""")
                logger.info("Using %d manual gold_examples for brand %s", len(gold_examples), brand_id)
                return "# Voice Calibration (Manual Gold Examples)\n" + "\n\n".join(samples)

        # 3. Fallback: automatic top performers from engagement data
        logger.debug("No manual gold_examples for brand %s, using top performers", brand_id)

        gold = db.table("content_performance") \
            .select("title, body, platform, engagement_score") \
            .eq("brand_id", brand_id) \
            .order("engagement_score", desc=True) \
            .limit(3) \
            .execute()

        if gold.data:
            samples = []
            for i, g in enumerate(gold.data, 1):
                samples.append(f"""
## Top Performer {i}: {g.get('title', '')}
Platform: {g.get('platform', '')}
Engagement Score: {g.get('engagement_score', 0)}

{g.get('body', '')}
""")
            logger.info("Using %d top performers as voice calibration for brand %s", len(gold.data), brand_id)
            return "# Voice Calibration (Top Performers)\n" + "\n\n".join(samples)

        # 4. Fallback: default natural voice
        logger.warning("No voice calibration data for brand %s, using default", brand_id)
        return "# Voice Calibration\nNo samples available — using default natural voice: varied rhythm, opinions, first-person perspective where appropriate."

    except Exception as e:
        logger.warning("Failed to load voice calibration for brand %s: %s", brand_id, e)
        return "# Voice calibration unavailable - using default natural voice"


async def humanize_draft(
    brand_id: str,
    draft_id: str,
    model_override: str | None = None,
) -> dict:
    """Humanize a content draft using anti-AI patterns and brand voice calibration.

    Implements double-pass:
    1. Initial rewrite with 29 AI patterns + voice calibration
    2. Anti-AI audit: "What's still AI?" → final revision

    Args:
        brand_id: Brand identifier
        draft_id: Draft identifier to humanize
        model_override: Optional specific model to use (bypasses routing).
                       Example: "anthropic/claude-3-5-haiku-20241022" or "google/gemma-4-150b:free"
                       If None, uses default routing (Gemma 4 free → Haiku fallback).

    Returns:
        Dict with humanized content and metadata
    """
    db = get_db()

    # Load draft
    draft = db.table("content_drafts").select("*").eq("id", draft_id).single().execute()
    draft_data = draft.data

    # Update status
    db.table("content_drafts").update({"status": "humanizing"}).eq("id", draft_id).execute()

    title = draft_data.get("title", "")
    body = draft_data.get("body", "")
    platform = draft_data.get("platform", "")
    content_type = draft_data.get("content_type", "post")

    # Load voice calibration (async: tries semantic memory first, then DB fallback)
    voice_calibration = await _load_voice_calibration(brand_id)

    # === PASS 1: Initial humanization ===
    try:
        identity = await get_agent_identity(brand_id, "humanizer")

        full_prompt = f"""<identity>
{identity}
</identity>

{_HUMANIZER_SKILL_TEXT}

{HUMANIZER_PROMPT_BASE}
"""

        prompt = full_prompt.format(
            title=sanitize_for_prompt(title, context="draft.title"),
            body=sanitize_for_prompt(body, context="draft.body"),
            platform=platform,
            content_type=content_type,
            voice_calibration_text=voice_calibration,
        )

        # Use model_override if provided, else use default routing
        if model_override:
            logger.info("Using model override for humanizer pass1: %s", model_override)
            resp = await _call_llm_with_model(
                prompt=prompt,
                brand_id=brand_id,
                model=model_override,
                context="humanizer_pass1",
                action="initial_humanization",
            )
        else:
            resp = await call_llm(
                prompt=prompt,
                brand_id=brand_id,
                context="humanizer_pass1",
                action="initial_humanization",
                task_type="creative"
            )

        result1 = json.loads(_strip_json(resp.content))

        title = result1.get("title", title)
        body = result1.get("body", body)
        ai_patterns_found = result1.get("ai_patterns_found", [])
        changes_summary = result1.get("changes_summary", "")

        logger.info("Pass 1 complete for draft %s: found %d AI patterns", draft_id, len(ai_patterns_found))

    except Exception as e:
        logger.error("Pass 1 failed for draft %s: %s", draft_id, e)
        return await _fail(draft_id, "pass1", e)

    # === PASS 2: Anti-AI audit ===
    try:
        audit_prompt = ANTI_AI_AUDIT_PROMPT.format(
            title=sanitize_for_prompt(title, context="draft.title"),
            body=sanitize_for_prompt(body, context="draft.body"),
        )

        # Use model_override if provided, else use default routing
        if model_override:
            logger.info("Using model override for humanizer pass2: %s", model_override)
            resp = await _call_llm_with_model(
                prompt=audit_prompt,
                brand_id=brand_id,
                model=model_override,
                context="humanizer_pass2",
                action="anti_ai_audit",
            )
        else:
            resp = await call_llm(
                prompt=audit_prompt,
                brand_id=brand_id,
                context="humanizer_pass2",
                action="anti_ai_audit",
                task_type="creative"
            )

        result2 = json.loads(_strip_json(resp.content))

        remaining_tells = result2.get("remaining_ai_tells", [])
        final_body = result2.get("body", body)
        audit_summary = result2.get("audit_summary", "")

        logger.info("Pass 2 complete for draft %s: found %d remaining AI-tells", draft_id, len(remaining_tells))

    except Exception as e:
        logger.error("Pass 2 failed for draft %s: %s", draft_id, e)
        # Continue with pass 1 result if audit fails
        final_body = body
        remaining_tells = []
        audit_summary = f"Audit failed: {e}"

    # === Update draft with humanized content ===
    new_version = (draft_data.get("version") or 1) + 1
    db.table("content_drafts").update({
        "title": title,
        "body": final_body,
        "version": new_version,
        "status": "humanized",
    }).eq("id", draft_id).execute()

    return {
        "draft_id": draft_id,
        "status": "humanized",
        "version": new_version,
        "ai_patterns_found_count": len(ai_patterns_found),
        "remaining_ai_tells_count": len(remaining_tells),
        "changes_summary": changes_summary,
        "audit_summary": audit_summary,
    }


async def _call_llm_with_model(
    prompt: str,
    brand_id: str,
    model: str,
    context: str,
    action: str,
    temperature: float = 0.7,
) -> LLMResponse:
    """Call LLM with explicit model override (bypasses default routing).

    This is a lightweight wrapper around the OpenRouter API that uses a specific model
    instead of the capability-based routing. Used when fine-grained model control is needed.

    Args:
        prompt: The prompt to send
        brand_id: Brand ID for cost tracking
        model: Specific model to use (e.g., "anthropic/claude-3-5-haiku-20241022")
        context: Context label for cost tracking
        action: Action label for cost tracking
        temperature: Temperature for generation

    Returns:
        LLMResponse with content and metadata
    """
    import httpx

    from ..config import settings
    from .cost_tracker import track_cost

    if not settings.openrouter_api_key:
        raise RuntimeError("OpenRouter API key required for model override")

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature if "o3-mini" not in model else 1,
            },
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:3000",
                "X-Title": "Content Engine"
            },
        )
        resp.raise_for_status()

        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        prompt_tok = usage.get("prompt_tokens", 0)
        comp_tok = usage.get("completion_tokens", 0)

        # Track cost
        from ..utils.llm_client import LLMResponse
        await track_cost(brand_id, context, model, action, prompt_tok, comp_tok)

        return LLMResponse(
            content=content,
            model_used=model,
            tokens_prompt=prompt_tok,
            tokens_completion=comp_tok
        )


def _strip_json(raw: str) -> str:
    """Strip markdown code fences from LLM response."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        text = text.rsplit("```", 1)[0].strip()
    return text


async def _fail(draft_id: str, step: str, error: Exception) -> dict:
    """Mark draft as failed and return error info."""
    logger.error("Humanizer failed at step '%s' for draft %s: %s", step, draft_id, error)

    db = get_db()
    db.table("content_drafts").update({
        "status": "humanizer_failed",
        "humanizer_result": {
            "failed_step": step,
            "error": str(error),
        },
    }).eq("id", draft_id).execute()

    return {
        "draft_id": draft_id,
        "status": "failed",
        "failed_step": step,
        "error": str(error),
    }


# Export
__all__ = ["humanize_draft", "HUMANIZER_PROMPT_BASE"]
