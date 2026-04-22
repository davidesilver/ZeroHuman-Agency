"""Synthesizer — uses Sonnet to produce reflection summaries and resolve conflicts.

Called by the Arbiter when superseding a fact: it writes a short "temporal
reflection" sentence explaining why the new fact replaces the old one.
Also used by the consolidation worker to produce a session summary for Telegram.
"""

from __future__ import annotations

import logging

from ...utils.llm_client import call_llm

logger = logging.getLogger(__name__)

_REFLECTION_SYSTEM = """\
You are a brand memory archivist.  Write a single, concise sentence (max 30 words)
that explains why a newer brand memory supersedes an older one.
Be factual and objective — focus on what changed and why.
Output ONLY the sentence, no quotation marks, no markdown.
"""

_SESSION_SUMMARY_SYSTEM = """\
You are a brand memory consolidator.  Summarise what was learned about a brand
during a session in 2–3 bullet points (plain text, each starting with "•").
Be specific: mention actual facts, not meta-commentary.
Output ONLY the bullets, no preamble, no markdown headers.
"""


async def generate_reflection(
    brand_id: str,
    old_statement: str,
    new_statement: str,
    reason: str = "",
) -> str:
    """Return a short temporal-reflection sentence explaining the supersede.

    Returns empty string on failure (non-fatal — the arbiter will still
    proceed without a reflection summary).
    """
    prompt = (
        f"OLD MEMORY: {old_statement}\n\n"
        f"NEW MEMORY: {new_statement}\n\n"
        f"REASON FOR CHANGE: {reason or 'not specified'}\n\n"
        "Write the reflection sentence."
    )
    try:
        resp = await call_llm(
            prompt=prompt,
            brand_id=brand_id,
            context="memory_consolidation",
            action="reflection_summary",
            system_prompt=_REFLECTION_SYSTEM,
            task_type="editing",
            temperature=0.3,
        )
        return resp.content.strip()
    except Exception as e:
        logger.warning("synthesizer.generate_reflection failed: %s", e)
        return ""


async def summarise_session(
    brand_id: str,
    session_id: str,
    facts_added: list[str],
    facts_superseded: list[str],
) -> str:
    """Produce a 2–3 bullet session summary for Telegram alert + episodic log.

    Returns the raw bullet text, or empty string on failure.
    """
    if not facts_added and not facts_superseded:
        return "No new facts consolidated in this session."

    added_block = "\n".join(f"  + {f}" for f in facts_added[:10]) or "  (none)"
    superseded_block = (
        "\n".join(f"  ~ {f}" for f in facts_superseded[:5]) or "  (none)"
    )

    prompt = (
        f"Session ID: {session_id}\n\n"
        f"Facts ADDED ({len(facts_added)}):\n{added_block}\n\n"
        f"Facts SUPERSEDED ({len(facts_superseded)}):\n{superseded_block}\n\n"
        "Write the session summary bullets."
    )
    try:
        resp = await call_llm(
            prompt=prompt,
            brand_id=brand_id,
            context="memory_consolidation",
            action="session_summary",
            system_prompt=_SESSION_SUMMARY_SYSTEM,
            task_type="editing",
            temperature=0.3,
        )
        return resp.content.strip()
    except Exception as e:
        logger.warning("synthesizer.summarise_session failed: %s", e)
        return ""
