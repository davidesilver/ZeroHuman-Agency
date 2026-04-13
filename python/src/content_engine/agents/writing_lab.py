"""Writing Lab — A/B testing engine for copy optimization."""

from __future__ import annotations

import json
from ..config import settings
from ..db import get_db
from ..utils.cost_tracker import track_cost
from ..utils.llm_client import call_llm

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

CHAMPION_PROMPT = """You are a world-class copywriter for the brand "{brand_name}".
Generate a compelling opening (hook + first paragraph) for the following topic.

Topic: {topic}
Content type: {content_type}
Hook type to use: {hook_type}
Tone of voice: {tone_of_voice}

Requirements:
- Write in Italian
- Maximum 280 characters for the hook line
- Follow the hook type precisely
- Make it irresistible to read further

Return ONLY a JSON object:
{{
  "hook": "<the hook line>",
  "body": "<the first paragraph, 2-3 sentences>",
  "hook_type": "{hook_type}"
}}
"""

CHALLENGER_PROMPT = """You are a world-class copywriter for the brand "{brand_name}".
Generate a DIFFERENT and BETTER opening for the same topic, using a different hook style.

Topic: {topic}
Content type: {content_type}
Hook type to use: {hook_type}
Tone of voice: {tone_of_voice}

Current champion text (you must BEAT this):
{champion_text}

Requirements:
- Write in Italian
- Maximum 280 characters for the hook line
- Use a completely different angle than the champion
- Make it MORE compelling

Return ONLY a JSON object:
{{
  "hook": "<the hook line>",
  "body": "<the first paragraph, 2-3 sentences>",
  "hook_type": "{hook_type}"
}}
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
