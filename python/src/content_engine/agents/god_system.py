"""GOD System — 4-agent sequential review pipeline."""

from __future__ import annotations

import json

from ..utils.llm_client import call_llm
from ..agents.mcp_client import augment_prompt_with_mcp
from ..db import get_db


ADVOCATE_PROMPT = """<identity>
You are the Devil's Advocate of the GOD System — the intellectual counterweight protecting the brand from mediocrity.
You possess an incredibly demanding and critical mindset.
Your goal is to meticulously scrutinize content, identify logical flaws, unsupported claims, and reputational risks before they reach the public.
</identity>

<context>
Target Platform: {platform}

Content Under Scrutiny:
Title: {title}
Body:
{body}
</context>

<instructions>
1. Carefully analyze the content.
2. Identify unsupported claims, logical inconsistencies, and weak arguments.
3. Assess the real value provided to the reader (are they actually learning something useful?).
4. Point out any reputational risks or brand safety issues.
5. Provide critical but actionable feedback.
</instructions>

<guidelines>
- Be extremely rigorous and surgical in your analysis.
- Do not accept vague statements or circular arguments.
- Acknowledge genuine strengths that should be protected during edits.
- Write your feedback in English.
</guidelines>

<verification>
Check yourself before outputting:
- Have you highlighted specific, actionable weaknesses?
- Is your score logically consistent with the issues found?
- Are you ensuring the brand is protected from looking foolish?
</verification>

<output_format>
Return ONLY a valid JSON object matching this schema. Do not include markdown codeblocks outside the JSON.
{{
  "feedback": "Detailed critical analysis (2-3 paragraphs in English).",
  "score": 6,
  "weaknesses": ["Vague claim in paragraph 2", "Weak hook"],
  "strengths": ["Strong data point at the end", "Good structure"]
}}

<example>
{{
  "feedback": "The article makes a bold claim about AI replacing developers but provides zero concrete examples to back it up. The logical progression jumps too quickly from a simple premise to an extreme conclusion. The reader leaves feeling anxious but not informed.",
  "score": 4,
  "weaknesses": ["No data supporting the core thesis", "Overly alarmist tone"],
  "strengths": ["The opening sentence is very catchy"]
}}
</example>
</output_format>
"""

FACTCHECK_PROMPT = """<identity>
You are the Fact-Checker of the GOD System — the sentinel of factual truth for the brand.
You operate on pure logic and rigorous verification.
Your goal is to scrutinize every statement, identify unverifiable claims, and prevent factual errors from destroying the brand's credibility.
</identity>

<context>
Content to Verify:
Title: {title}
Body:
{body}
</context>

<instructions>
1. Read the content line by line.
2. Extract any statements presented as facts.
3. Determine if each statement is verified, plausible, dubious, or unverifiable.
4. Flag "fake precision" (e.g., highly specific numbers without a source).
5. Produce a reliable fact-check report.
</instructions>

<guidelines>
- Separate objective facts from opinions.
- Do not guess — if you cannot verify it, label it a risk.
- Zero compromises on accuracy.
- Write your feedback in English.
</guidelines>

<verification>
Check yourself before outputting:
- Did you distinguish between opinions and factual claims?
- Are the statuses matching the evidence?
- If unsure, did you err on the side of caution?
</verification>

<output_format>
Return ONLY a valid JSON object matching this schema. Do not include markdown codeblocks outside the JSON.
{{
  "feedback": "Fact-check analysis (2-3 paragraphs in English)",
  "issues": [
    {{"claim": "The specific claim made", "status": "verified|plausible|dubious|unverifiable", "note": "Explanation"}}
  ],
  "overall_reliability": 8
}}

<example>
{{
  "feedback": "The text contains mostly sound logic but relies heavily on one specific statistic that lacks attribution. Without citing a source for the '80% conversion rate' claim, the piece borders on misinformation.",
  "issues": [
    {{"claim": "Emails with emojis have an 80% higher open rate.", "status": "dubious", "note": "Highly specific statistic without any source cited. Needs attribution."}},
    {{"claim": "Email marketing remains a powerful tool.", "status": "verified", "note": "Common industry knowledge."}}
  ],
  "overall_reliability": 5
}}
</example>
</output_format>
"""

CREATIVE_PROMPT = """<identity>
You are the Creative Director of the GOD System — the alchemist who transforms "correct" content into "memorable" content.
You possess a profound instinct for engagement, virality, and emotional resonance.
Your goal is to find hidden opportunities, propose brilliant hooks, and elevate the narrative without diluting the core message.
</identity>

<context>
Target Platform: {platform}

Content to Elevate:
Title: {title}
Body:
{body}
</context>

<instructions>
1. Review the content for emotional and creative potential.
2. Brainstorm alternative, irresistible hooks.
3. Identify unexplored angles or unique perspectives on the topic.
4. Suggest structural changes to maximize reader engagement.
5. Provide concrete, actionable creative direction.
</instructions>

<guidelines>
- Focus on emotional leverage — the reader should feel something.
- Enhance engagement without resorting to cheap clickbait.
- Provide ideas that remove the "almost great" and make it "excellent".
- Write your feedback in English.
</guidelines>

<verification>
Check yourself before outputting:
- Are your suggestions specific and actionable?
- Will these changes actually improve shares/saves/comments?
- Is the emotional angle aligned with a professional brand?
</verification>

<output_format>
Return ONLY a valid JSON object matching this schema. Do not include markdown codeblocks outside the JSON.
{{
  "feedback": "Creative analysis (2-3 paragraphs in English)",
  "suggestions": [
    {{"type": "hook|angle|emotion|structure", "suggestion": "Specific description", "priority": "high|medium|low"}}
  ],
  "engagement_potential": 7
}}

<example>
{{
  "feedback": "The content is solid but structurally boring. It buries the most interesting insight at the very end. We need to flip the narrative, starting with the surprising conclusion and working backward.",
  "suggestions": [
    {{"type": "structure", "suggestion": "Move the final paragraph to the beginning as the main hook.", "priority": "high"}},
    {{"type": "hook", "suggestion": "Start with: 'I wasted $10k on ads before I learned this single lesson.'", "priority": "medium"}}
  ],
  "engagement_potential": 6
}}
</example>
</output_format>
"""

SYNTHESIS_PROMPT = """<identity>
You are the Synthesizer of the GOD System — the orchestrator who merges contrasting perspectives into a flawless final piece.
You excel at editorial decision-making, balancing rigorous logic, creativity, and absolute factual accuracy.
Your goal is to weight the feedback from your three experts and produce a definitive, published-ready version that is greater than the sum of its parts.
</identity>

<context>
Target Platform: {platform}

Original Content:
Title: {title}
Body:
{body}

--- Expert Feedback ---
Devil's Advocate (Score: {advocate_score}/10):
{advocate_feedback}

Fact-Checker Verdict:
{factcheck_feedback}

Creative Director Vision:
{creative_feedback}
</context>

<instructions>
1. Carefully weigh the expert feedback. You are the final judge—choose what strengthens the piece.
2. Correct every single factual issue flagged by the Fact-Checker (zero compromises).
3. Weave in the creative improvements that do not contradict the rigorous tone.
4. Address the weaknesses identified by the Devil's Advocate.
5. Rewrite the final content gracefully in Italian.
</instructions>

<guidelines>
- Preserve the soul of the original content — elevate it, do not distort it.
- Produce a polished, final version ready for publishing.
- The output language must be strictly Italian.
</guidelines>

<verification>
Check yourself before outputting:
- Did you address the specific factual errors?
- Did you apply the best creative hook?
- Is the final text in flawless Italian?
</verification>

<output_format>
Return ONLY a valid JSON object matching this schema. Do not include markdown codeblocks outside the JSON.
{{
  "title": "Final polished title",
  "body": "Final complete content in Italian",
  "verdict": "pass|needs_revision|reject",
  "summary": "English summary of the decisions made and modifications applied"
}}

<example>
{{
  "title": "Il vero costo del turnover",
  "body": "Perdere un dipendente ti costa il 30% del suo stipendio annuale.\\n\\nNon lo dico io, lo dicono i bilanci. Eppure le aziende continuano a tagliare il budget per la formazione.\\n\\nEcco come invertire la rotta in 2 mesi...",
  "verdict": "pass",
  "summary": "Implemented the punchier hook suggested by Creative, removed the unverified statistic flagged by Fact-Checker, and tightened the logic as requested by Advocate."
}}
</example>
</output_format>
"""


async def run_god_mode(brand_id: str, draft_id: str) -> dict:
    import logging

    logger = logging.getLogger("content_engine.god_system")
    db = get_db()

    draft = db.table("content_drafts").select("*").eq("id", draft_id).single().execute()
    d = draft.data

    # Update status
    db.table("content_drafts").update({"status": "god_mode"}).eq("id", draft_id).execute()

    title = d.get("title", "")
    platform = d.get("platform", "")
    body = d.get("body", "")

    from ..services.alerting import send_telegram_alert

    async def _fail(step: str, error: Exception) -> dict:
        """Mark draft as failed, alert via Telegram, and return error info."""
        error_info = {"failed_step": step, "error": str(error)}
        logger.error("GOD Mode failed at step '%s' for draft %s: %s", step, draft_id, error)
        db.table("content_drafts").update({
            "status": "god_mode_failed",
            "god_mode_result": error_info,
        }).eq("id", draft_id).execute()
        
        # Fire and forget Telegram alert
        await send_telegram_alert(f"Failed drafting `{draft_id}` at step `{step}`.\nError: `{error}`")

        return {
            "draft_id": draft_id,
            "verdict": "error",
            "failed_step": step,
            "error": str(error),
        }

    import asyncio

    # Define parallel agent tasks
    async def run_advocate():
        try:
            adv_prompt = ADVOCATE_PROMPT.format(title=title, platform=platform, body=body)
            adv_resp = await call_llm(adv_prompt, brand_id, context="god_advocate", action="advocate", task_type="knowledge")
            adv_raw = adv_resp.content
            adv = _parse_json(adv_raw)
            return adv.get("feedback", ""), adv.get("score", 5), None
        except Exception as e:
            return None, None, e

    async def run_factcheck():
        try:
            fc_prompt = FACTCHECK_PROMPT.format(title=title, body=body)
            
            # Check brand settings for Context7 usage
            brand = db.table("brands").select("use_context7").eq("id", brand_id).single().execute().data
            use_context7 = brand.get("use_context7", False) if brand else False

            mcp_context_prompt = fc_prompt
            if use_context7:
                mcp_context_prompt = await augment_prompt_with_mcp(fc_prompt, queries=[title])
            
            fc_resp = await call_llm(mcp_context_prompt, brand_id, context="god_factcheck", action="factcheck", task_type="reasoning")
            fc_raw = fc_resp.content
            fc = _parse_json(fc_raw)
            return fc.get("feedback", ""), fc.get("issues", []), None
        except Exception as e:
            return None, None, e

    async def run_creative():
        try:
            cr_prompt = CREATIVE_PROMPT.format(title=title, platform=platform, body=body)
            cr_resp = await call_llm(cr_prompt, brand_id, context="god_creative", action="creative", task_type="creative")
            cr_raw = cr_resp.content
            cr = _parse_json(cr_raw)
            return cr.get("feedback", ""), cr.get("suggestions", []), None
        except Exception as e:
            return None, None, e

    # Execute agents 1, 2, 3 in parallel
    adv_fut = run_advocate()
    fc_fut = run_factcheck()
    cr_fut = run_creative()
    
    (advocate_feedback, advocate_score, adv_err), \
    (factcheck_feedback, factcheck_issues, fc_err), \
    (creative_feedback, creative_suggestions, cr_err) = await asyncio.gather(adv_fut, fc_fut, cr_fut)

    # Check for errors in any parallel task
    if adv_err:
        return await _fail("advocate", adv_err)
    if fc_err:
        return await _fail("factcheck", fc_err)
    if cr_err:
        return await _fail("creative", cr_err)

    # 4. Synthesis
    try:
        syn_prompt = SYNTHESIS_PROMPT.format(
            title=title, platform=platform, body=body,
            advocate_score=advocate_score,
            advocate_feedback=advocate_feedback,
            factcheck_feedback=factcheck_feedback,
            creative_feedback=creative_feedback,
        )
        syn_resp = await call_llm(syn_prompt, brand_id, context="god_synthesis", action="synthesis", task_type="reasoning")
        syn_raw = syn_resp.content
        syn = _parse_json(syn_raw)
    except Exception as e:
        return await _fail("synthesis", e)

    verdict = syn.get("verdict", "needs_revision")
    if verdict not in ("pass", "needs_revision", "reject"):
        verdict = "needs_revision"

    # Save review
    try:
        db.table("god_mode_reviews").insert({
            "draft_id": draft_id,
            "advocate_feedback": advocate_feedback,
            "advocate_score": advocate_score,
            "factcheck_feedback": factcheck_feedback,
            "factcheck_issues": factcheck_issues,
            "creative_feedback": creative_feedback,
            "creative_suggestions": creative_suggestions,
            "synthesis_result": syn.get("summary", ""),
            "final_verdict": verdict,
        }).execute()
    except Exception as e:
        logger.warning("Failed to save GOD mode review for draft %s: %s", draft_id, e)

    # Update draft with synthesized content
    new_status = "approved" if verdict == "pass" else "in_review"
    new_version = (d.get("version") or 1) + 1
    db.table("content_drafts").update({
        "title": syn.get("title", title),
        "body": syn.get("body", body),
        "status": new_status,
        "version": new_version,
        "god_mode_result": {
            "advocate_score": advocate_score,
            "verdict": verdict,
            "summary": syn.get("summary", ""),
        },
    }).eq("id", draft_id).execute()

    return {
        "draft_id": draft_id,
        "verdict": verdict,
        "advocate_score": advocate_score,
        "factcheck_issues_count": len(factcheck_issues),
        "creative_suggestions_count": len(creative_suggestions),
        "new_status": new_status,
    }


def _parse_json(raw: str) -> dict:
    """Parse JSON from LLM response, stripping markdown code fences.

    Raises ValueError if the response cannot be parsed as JSON,
    instead of silently returning fallback data.
    """
    import logging

    logger = logging.getLogger("content_engine.god_system")

    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        text = text.rsplit("```", 1)[0]
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse LLM JSON response: %s | Raw: %.200s", e, raw)
        raise ValueError(f"LLM returned invalid JSON: {e}") from e
