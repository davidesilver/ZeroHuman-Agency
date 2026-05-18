"""Writing Lab — A/B testing engine for copy optimization."""

from __future__ import annotations

import asyncio
import json
import logging

from ..db import get_db
from ..utils.llm_client import call_llm

logger = logging.getLogger(__name__)

HOOK_TYPES = [
    "Attacco numerico",
    "Domanda provocatoria",
    "Affermazione controintuitiva",
    "Storia personale",
    "Citazione esperta",
    "Dato scientifico",
    "Metafora",
    "Problema comune",
    "Previsione futura",
    "Confessione",
]

CHAMPION_PROMPT = """<identity>
You are the Champion Copywriter for {brand_name}.
You are an elite, top-tier copywriter whose words are impossible to ignore.
Your goal is to set an incredibly high standard for an opening hook that grabs attention immediately.
</identity>

<context>
Topic: {topic}
Content Type: {content_type}
Hook Technique: {hook_type}
Tone of Voice: {tone_of_voice}
</context>

<instructions>
1. Analyze the topic and the requested hook technique.
2. Write a brutally effective, scroll-stopping hook paragraph.
3. Write the hook in Italian.
</instructions>

<guidelines>
- The hook must be under 280 characters.
- Follow the '{hook_type}' technique with surgical precision.
- Every single character must earn its place. No fluff.
- Output strictly in Italian.
</guidelines>

<verification>
Check yourself before outputting:
- Is the text perfectly illustrating the '{hook_type}'?
- Is it under 280 characters?
- Is it written in flawless Italian?
</verification>

<output_format>
Return ONLY a valid JSON object matching this schema. Do not include markdown codeblocks outside the JSON.
{{
  "hook": "The punchy hook line",
  "body": "The first short paragraph elaborating on it, 2-3 sentences",
  "hook_type": "{hook_type}"
}}

<example>
{{
  "hook": "Il 90% delle startup fallisce. Ma nessuno ti dice il perché.",
  "body": "Non è il prodotto. Non è il mercato. È il fondatore che non sa delegare. Ho studiato 50 aziende fallite l'anno scorso e ho trovato un pattern inquietante.",
  "hook_type": "Attacco numerico"
}}
</example>
</output_format>
"""

CHALLENGER_PROMPT = """<identity>
You are the Challenger Copywriter for {brand_name}.
You thrive on dethroning the reigning champion with fresh, subversive, and superior copywriting angles.
Your goal is to write a hook that is unequivocally better and more compelling than the Champion's current text.
</identity>

<context>
Topic: {topic}
Content Type: {content_type}
Hook Technique: {hook_type}
Tone of Voice: {tone_of_voice}

Current Champion's Text:
{champion_text}
</context>

<instructions>
1. Critically analyze the Champion's text to find its blind spots.
2. Draft a new hook using the assigned '{hook_type}' technique.
3. Ensure your version is so compelling that a reader would immediately choose yours over the Champion's.
4. Write strictly in Italian.
</instructions>

<guidelines>
- The hook must be under 280 characters.
- Take a completely completely different angle from the Champion. 
- Stand out. Be punchy, incisive, and unforgettable.
- Output strictly in Italian.
</guidelines>

<verification>
Check yourself before outputting:
- Is this genuinely a different angle from the Champion?
- Does it perfectly embody the '{hook_type}'?
- Is the text in Italian under 280 chars?
</verification>

<output_format>
Return ONLY a valid JSON object matching this schema. Do not include markdown codeblocks outside the JSON.
{{
  "hook": "Your superior hook line",
  "body": "The short elaboration, 2-3 sentences",
  "hook_type": "{hook_type}"
}}

<example>
{{
  "hook": "Chiudere un'azienda fa male. Ne ho chiuse tre prima di capire da dove iniziare.",
  "body": "Tutti parlano di unicorni. Nessuno parla dei fallimenti che preparano il terreno. Se stai affrontando una crisi ora, ecco cosa devi sapere prima di staccare la spina.",
  "hook_type": "Storia personale"
}}
</example>
</output_format>
"""


def _parse_json(text: str) -> dict:
    """Extract JSON from LLM response."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
        raise



async def create_session(brand_id: str, topic: str, content_type: str) -> dict:
    """Create a new Writing Lab session and generate round 1."""
    db = get_db()

    # Load brand config
    brand = db.table("brands").select("*").eq("id", brand_id).single().execute().data
    tone = brand.get("tone_of_voice", {}) if brand else {}
    brand_name = brand.get("name", "Brand") if brand else "Brand"

    # Create session
    session = db.table("writing_lab_sessions").insert({
        "brand_id": brand_id,
        "topic": topic,
        "content_type": content_type,
        "status": "active",
        "rounds_completed": 0,
        "max_rounds": 50,
        "hook_types_tried": [],
        "user_votes": {},
    }).execute().data[0]

    # Generate round 1
    champion_hook = HOOK_TYPES[0]
    challenger_hook = HOOK_TYPES[1]

    champion_prompt = CHAMPION_PROMPT.format(
        brand_name=brand_name,
        topic=topic,
        content_type=content_type,
        hook_type=champion_hook,
        tone_of_voice=json.dumps(tone, ensure_ascii=False),
    )
    challenger_prompt = CHALLENGER_PROMPT.format(
        brand_name=brand_name,
        topic=topic,
        content_type=content_type,
        hook_type=challenger_hook,
        tone_of_voice=json.dumps(tone, ensure_ascii=False),
        champion_text="(first round — no champion yet)",
    )

    champion_res = await call_llm(
        prompt=champion_prompt,
        brand_id=brand_id,
        context="writing_lab",
        action="generate_champion",
        task_type="creative"
    )
    champion_resp = champion_res.content

    challenger_res = await call_llm(
        prompt=challenger_prompt,
        brand_id=brand_id,
        context="writing_lab",
        action="generate_challenger",
        task_type="creative"
    )
    challenger_resp = challenger_res.content

    champion_data = _parse_json(champion_resp)
    challenger_data = _parse_json(challenger_resp)

    champion_text = f"{champion_data.get('hook', '')}\n\n{champion_data.get('body', '')}"
    challenger_text = f"{challenger_data.get('hook', '')}\n\n{challenger_data.get('body', '')}"

    # Save round
    round_data = db.table("writing_lab_rounds").insert({
        "session_id": session["id"],
        "round_number": 1,
        "champion_text": champion_text,
        "challenger_text": challenger_text,
        "hook_type_champion": champion_hook,
        "hook_type_challenger": challenger_hook,
    }).execute().data[0]

    # Update session
    db.table("writing_lab_sessions").update({
        "current_champion": champion_text,
        "champion_version": 1,
        "hook_types_tried": [champion_hook, challenger_hook],
    }).eq("id", session["id"]).execute()

    return {
        "session": session,
        "round": round_data,
    }


async def _log_vote_memory(
    brand_id: str,
    session_id: str,
    round_number: int,
    winner: str,
    feedback: str | None,
    hook_type_champion: str | None,
    hook_type_challenger: str | None,
) -> None:
    """P3.8 — Write vote to memory_events + update agent_skills counters.

    Fires-and-forgets (called via asyncio.create_task).
    Never raises — errors are logged but never surfaced to the caller.
    """
    db = get_db()

    # ── 1. memory_events: episodic record of the vote ──────────────────────
    try:
        summary = (
            f"Writing-lab round {round_number}: '{winner}' won"
            + (f" ({hook_type_challenger} vs {hook_type_champion})" if hook_type_challenger else "")
            + (f" — feedback: {feedback[:80]}" if feedback else "")
        )
        db.table("memory_events").insert({
            "brand_id": brand_id,
            "event_kind": "writing_lab_vote",
            "subject_kind": "writing_lab_session",
            "subject_id": session_id,
            "summary": summary,
            "payload": {
                "round_number": round_number,
                "winner": winner,
                "hook_type_champion": hook_type_champion,
                "hook_type_challenger": hook_type_challenger,
                "feedback": feedback,
            },
        }).execute()
    except Exception as e:
        logger.warning("writing_lab._log_vote_memory: memory_events insert failed: %s", e)

    # ── 2. agent_skills counters (success/failure per hook type) ──────────
    # The challenger hook_type is the "skill" being evaluated:
    # challenger wins → success; champion wins / draw → challenger skill failed this round.
    if not hook_type_challenger:
        return

    try:
        # Try to find an existing agent_skill row for this hook_type
        row = (
            db.table("agent_skills")
            .select("id, success_count, failure_count")
            .eq("brand_id", brand_id)
            .eq("skill_name", hook_type_challenger)
            .eq("target_agent", "writing_lab")
            .maybe_single()
            .execute()
        )

        if row.data:
            # Update existing row
            if winner == "challenger":
                db.table("agent_skills").update({
                    "success_count": (row.data.get("success_count") or 0) + 1,
                }).eq("id", row.data["id"]).execute()
            else:  # champion or draw
                db.table("agent_skills").update({
                    "failure_count": (row.data.get("failure_count") or 0) + 1,
                }).eq("id", row.data["id"]).execute()
        else:
            # Create a new skill row for this hook type
            db.table("agent_skills").insert({
                "brand_id": brand_id,
                "skill_name": hook_type_challenger,
                "target_agent": "writing_lab",
                "instructions": f"Hook type: {hook_type_challenger}",
                "priority": 50,
                "is_active": True,
                "success_count": 1 if winner == "challenger" else 0,
                "failure_count": 0 if winner == "challenger" else 1,
            }).execute()
    except Exception as e:
        logger.warning("writing_lab._log_vote_memory: agent_skills update failed: %s", e)


async def vote_round(brand_id: str, session_id: str, winner: str, feedback: str | None = None) -> dict:
    """Process a vote and generate the next round."""
    if winner not in ("champion", "challenger", "draw"):
        raise ValueError(f"Invalid winner: {winner}")

    db = get_db()

    # Get session
    session = db.table("writing_lab_sessions").select("*").eq("id", session_id).single().execute().data
    if not session:
        raise ValueError("Session not found")
    if session["status"] != "active":
        raise ValueError("Session is not active")

    # Get current round (latest)
    rounds = db.table("writing_lab_rounds").select("*").eq(
        "session_id", session_id
    ).order("round_number", desc=True).limit(1).execute().data

    if not rounds:
        raise ValueError("No rounds found")

    current_round = rounds[0]

    # Update current round with vote
    db.table("writing_lab_rounds").update({
        "winner": winner,
        "user_feedback": feedback,
    }).eq("id", current_round["id"]).execute()

    # P3.8 — fire-and-forget: memory_events + agent_skills counters
    asyncio.create_task(_log_vote_memory(
        brand_id=brand_id,
        session_id=session_id,
        round_number=current_round["round_number"],
        winner=winner,
        feedback=feedback,
        hook_type_champion=current_round.get("hook_type_champion"),
        hook_type_challenger=current_round.get("hook_type_challenger"),
    ))

    # Determine new champion
    if winner == "champion":
        new_champion = current_round["champion_text"]
    elif winner == "challenger":
        new_champion = current_round["challenger_text"]
    else:  # draw — keep champion
        new_champion = current_round["champion_text"]

    new_round_number = current_round["round_number"] + 1

    # Update vote counts
    user_votes = session.get("user_votes") or {}
    user_votes[str(current_round["round_number"])] = winner

    # Check if session is complete
    if new_round_number > (session.get("max_rounds") or 50):
        db.table("writing_lab_sessions").update({
            "status": "completed",
            "current_champion": new_champion,
            "rounds_completed": current_round["round_number"],
            "user_votes": user_votes,
        }).eq("id", session_id).execute()
        return {"status": "completed", "champion": new_champion}

    # Generate next challenger
    brand = db.table("brands").select("*").eq("id", brand_id).single().execute().data
    tone = brand.get("tone_of_voice", {}) if brand else {}
    brand_name = brand.get("name", "Brand") if brand else "Brand"

    hook_types_tried = session.get("hook_types_tried") or []
    remaining_hooks = [h for h in HOOK_TYPES if h not in hook_types_tried]
    if not remaining_hooks:
        remaining_hooks = HOOK_TYPES  # cycle through again
    next_hook = remaining_hooks[0]

    challenger_prompt = CHALLENGER_PROMPT.format(
        brand_name=brand_name,
        topic=session["topic"],
        content_type=session["content_type"],
        hook_type=next_hook,
        tone_of_voice=json.dumps(tone, ensure_ascii=False),
        champion_text=new_champion,
    )

    challenger_res = await call_llm(
        prompt=challenger_prompt,
        brand_id=brand_id,
        context="writing_lab",
        action="generate_challenger",
        task_type="creative"
    )
    challenger_resp = challenger_res.content

    challenger_data = _parse_json(challenger_resp)
    challenger_text = f"{challenger_data.get('hook', '')}\n\n{challenger_data.get('body', '')}"

    # Save new round
    new_round = db.table("writing_lab_rounds").insert({
        "session_id": session_id,
        "round_number": new_round_number,
        "champion_text": new_champion,
        "challenger_text": challenger_text,
        "hook_type_champion": current_round.get("hook_type_champion") if winner == "champion" else current_round.get("hook_type_challenger"),
        "hook_type_challenger": next_hook,
    }).execute().data[0]

    hook_types_tried.append(next_hook)

    # Update session
    db.table("writing_lab_sessions").update({
        "current_champion": new_champion,
        "champion_version": (session.get("champion_version") or 0) + (1 if winner == "challenger" else 0),
        "rounds_completed": current_round["round_number"],
        "hook_types_tried": hook_types_tried,
        "user_votes": user_votes,
    }).eq("id", session_id).execute()

    return {
        "status": "active",
        "round": new_round,
        "rounds_completed": current_round["round_number"],
    }
