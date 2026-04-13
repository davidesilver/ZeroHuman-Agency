"""GOD System — 4-agent sequential review pipeline."""

from __future__ import annotations

import json

from ..utils.llm_client import call_llm
from ..agents.mcp_client import augment_prompt_with_mcp
from ..db import get_db


ADVOCATE_PROMPT = """Sei l'Avvocato del Diavolo. Analizza criticamente questo contenuto.

Titolo: {title}
Piattaforma: {platform}
Contenuto:
{body}

Valuta:
1. Affermazioni non supportate o troppo generiche
2. Coerenza logica dell'argomentazione
3. Valore reale per il lettore
4. Rischi reputazionali o controversie
5. Punti di forza da enfatizzare

Rispondi SOLO in JSON:
{{
  "feedback": "analisi critica dettagliata (2-3 paragrafi)",
  "score": <numero 1-10>,
  "weaknesses": ["punto debole 1", "punto debole 2"],
  "strengths": ["punto forte 1", "punto forte 2"]
}}
"""

FACTCHECK_PROMPT = """Sei un Fact-Checker. Verifica le affermazioni in questo contenuto.

Titolo: {title}
Contenuto:
{body}

Contesto dell'Avvocato: {advocate_feedback}

Per ogni claim:
- Segna se verificabile o meno
- Se verificabile, indica se plausibile/dubbio/falso
- Suggerisci fonti per verifica

Rispondi SOLO in JSON:
{{
  "feedback": "analisi fact-check (2-3 paragrafi)",
  "issues": [
    {{"claim": "affermazione", "status": "verified|plausible|dubious|unverifiable", "note": "spiegazione"}}
  ],
  "overall_reliability": <numero 1-10>
}}
"""

CREATIVE_PROMPT = """Sei un Direttore Creativo. Migliora l'impatto di questo contenuto.

Titolo: {title}
Piattaforma: {platform}
Contenuto:
{body}

Feedback Avvocato: {advocate_feedback}
Fact-check: {factcheck_feedback}

Suggerisci:
1. Hook alternativi piu' potenti
2. Angoli creativi non esplorati
3. Elementi emotivi da aggiungere
4. Miglioramenti alla struttura per engagement

Rispondi SOLO in JSON:
{{
  "feedback": "analisi creativa (2-3 paragrafi)",
  "suggestions": [
    {{"type": "hook|angle|emotion|structure", "suggestion": "descrizione", "priority": "high|medium|low"}}
  ],
  "engagement_potential": <numero 1-10>
}}
"""

SYNTHESIS_PROMPT = """Sei il Sintetizzatore Finale. Integra tutti i feedback e produci la versione finale.

## Contenuto originale
Titolo: {title}
Piattaforma: {platform}
{body}

## Feedback Avvocato (score: {advocate_score}/10)
{advocate_feedback}

## Fact-check
{factcheck_feedback}

## Suggerimenti Creativi
{creative_feedback}

## Istruzioni
1. Integra i punti validi di tutti gli agenti
2. Correggi i problemi segnalati dal fact-checker
3. Applica i miglioramenti creativi prioritari
4. Mantieni il tono originale del brand
5. Produci la versione finale migliorata

Rispondi SOLO in JSON:
{{
  "title": "titolo finale",
  "body": "contenuto finale completo e migliorato",
  "verdict": "pass|needs_revision|reject",
  "summary": "sommario delle modifiche applicate"
}}
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

    def _fail(step: str, error: Exception) -> dict:
        """Mark draft as failed and return error info."""
        error_info = {"failed_step": step, "error": str(error)}
        logger.error("GOD Mode failed at step '%s' for draft %s: %s", step, draft_id, error)
        db.table("content_drafts").update({
            "status": "god_mode_failed",
            "god_mode_result": error_info,
        }).eq("id", draft_id).execute()
        return {
            "draft_id": draft_id,
            "verdict": "error",
            "failed_step": step,
            "error": str(error),
        }

    # 1. Advocate
    try:
        adv_prompt = ADVOCATE_PROMPT.format(title=title, platform=platform, body=body)
        adv_resp = await call_llm(adv_prompt, brand_id, context="god_advocate", action="advocate", complexity="normal")
        adv_raw = adv_resp.content
        adv = _parse_json(adv_raw)
        advocate_feedback = adv.get("feedback", "")
        advocate_score = adv.get("score", 5)
    except Exception as e:
        return _fail("advocate", e)

    # 2. Factchecker
    try:
        fc_prompt = FACTCHECK_PROMPT.format(title=title, body=body, advocate_feedback=advocate_feedback)
        
        # Determine subjects to research via MCP dynamically or simple heuristic
        # In a real setup, another LLM pass extracts technical keywords, here we just pass the title
        mcp_context_prompt = await augment_prompt_with_mcp(fc_prompt, queries=[title])
        
        fc_resp = await call_llm(mcp_context_prompt, brand_id, context="god_factcheck", action="factcheck", complexity="high")
        fc_raw = fc_resp.content
        fc = _parse_json(fc_raw)
        factcheck_feedback = fc.get("feedback", "")
        factcheck_issues = fc.get("issues", [])
    except Exception as e:
        return _fail("factcheck", e)

    # 3. Creative
    try:
        cr_prompt = CREATIVE_PROMPT.format(
            title=title, platform=platform, body=body,
            advocate_feedback=advocate_feedback, factcheck_feedback=factcheck_feedback,
        )
        cr_resp = await call_llm(cr_prompt, brand_id, context="god_creative", action="creative", complexity="normal")
        cr_raw = cr_resp.content
        cr = _parse_json(cr_raw)
        creative_feedback = cr.get("feedback", "")
        creative_suggestions = cr.get("suggestions", [])
    except Exception as e:
        return _fail("creative", e)

    # 4. Synthesis
    try:
        syn_prompt = SYNTHESIS_PROMPT.format(
            title=title, platform=platform, body=body,
            advocate_score=advocate_score,
            advocate_feedback=advocate_feedback,
            factcheck_feedback=factcheck_feedback,
            creative_feedback=creative_feedback,
        )
        syn_resp = await call_llm(syn_prompt, brand_id, context="god_synthesis", action="synthesis", complexity="high")
        syn_raw = syn_resp.content
        syn = _parse_json(syn_raw)
    except Exception as e:
        return _fail("synthesis", e)

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
