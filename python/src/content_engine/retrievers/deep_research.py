"""Deep research job wrapper for local-deep-research Docker sidecar.

local-deep-research runs on port 5000 (configured in docker-compose.yaml).
Jobs are asynchronous:
  1. POST /v1/research/start → { job_id }
  2. GET  /v1/research/status/{job_id} → { status, progress }
  3. GET  /v1/research/results/{job_id} → { report, sources }

Feature gate: DEEP_RESEARCH_ENABLED feature flag must be ON.
Per-brand depth cap: brand.feature_flags['deep_research_max_depth'] (default 3).

Usage:
    from content_engine.retrievers.deep_research import start_deep_research_job, get_job_status, get_job_results
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, Optional

import httpx

from ..services.feature_flags import DEEP_RESEARCH_ENABLED, get_feature_flag
from ..db import get_db

logger = logging.getLogger("content_engine.retrievers.deep_research")

DEEP_RESEARCH_URL = os.environ.get("DEEP_RESEARCH_URL", "http://localhost:5000")
DEFAULT_MAX_DEPTH = 3


class DeepResearchError(Exception):
    """Raised when the local-deep-research sidecar returns an error."""


def _check_feature(brand_id: str) -> None:
    if not get_feature_flag(brand_id, DEEP_RESEARCH_ENABLED):
        raise DeepResearchError(
            f"deep_research_enabled is OFF for brand {brand_id}. "
            "Enable it in Settings → Feature Flags."
        )


def _get_max_depth(brand_id: str) -> int:
    """Read per-brand depth cap from feature_flags (default 3)."""
    try:
        result = (
            get_db()
            .from_("feature_flags")
            .select("value")
            .eq("brand_id", brand_id)
            .eq("key", "deep_research_max_depth")
            .maybe_single()
            .execute()
        )
        if result.data and result.data.get("value") is not None:
            return int(result.data["value"])
    except Exception:
        pass
    return DEFAULT_MAX_DEPTH


def start_job(brand_id: str, topic: str, depth: int = 3) -> str:
    """Dispatch a deep research job. Returns the local DB job UUID.

    The job is created in deep_research_jobs with status='pending', then the
    external request is sent to local-deep-research. The external job ID is
    stored in external_id.
    """
    _check_feature(brand_id)

    max_depth = _get_max_depth(brand_id)
    depth = min(depth, max_depth)

    # Create local record
    result = get_db().from_("deep_research_jobs").insert({
        "brand_id": brand_id,
        "topic": topic,
        "depth": depth,
        "status": "pending",
    }).execute()

    if not result.data:
        raise DeepResearchError("Failed to create deep_research_jobs record")

    job_id = result.data[0]["id"]

    # Submit to sidecar
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{DEEP_RESEARCH_URL}/v1/research/start",
                json={"query": topic, "depth": depth},
            )
            resp.raise_for_status()
            external_id = resp.json().get("job_id")

        get_db().from_("deep_research_jobs").update({
            "status": "running",
            "external_id": external_id,
            "started_at": "now()",
        }).eq("id", job_id).execute()
    except Exception as exc:
        get_db().from_("deep_research_jobs").update({
            "status": "failed",
            "error": str(exc),
        }).eq("id", job_id).execute()
        logger.error("Failed to start deep research job %s: %s", job_id, exc)
        raise DeepResearchError(f"Failed to submit to deep-research sidecar: {exc}") from exc

    return job_id


def get_status(job_id: str, brand_id: str) -> dict:
    """Return the status of a deep research job."""
    result = (
        get_db()
        .from_("deep_research_jobs")
        .select("id, status, topic, depth, error, started_at, completed_at, created_at")
        .eq("id", job_id)
        .eq("brand_id", brand_id)
        .maybe_single()
        .execute()
    )
    if not result.data:
        raise DeepResearchError(f"Job {job_id} not found")

    row = result.data

    # If running, poll sidecar for live progress
    if row["status"] == "running":
        try:
            r = (
                get_db()
                .from_("deep_research_jobs")
                .select("external_id")
                .eq("id", job_id)
                .single()
                .execute()
            )
            ext_id = r.data.get("external_id") if r.data else None
            if ext_id:
                with httpx.Client(timeout=10.0) as client:
                    resp = client.get(f"{DEEP_RESEARCH_URL}/v1/research/status/{ext_id}")
                    if resp.ok:
                        status_data = resp.json()
                        if status_data.get("status") == "completed":
                            _finalize_job(job_id, ext_id)
                            row["status"] = "completed"
        except Exception:
            pass  # status is best-effort

    return row


def get_results(job_id: str, brand_id: str) -> dict:
    """Return the results of a completed deep research job."""
    result = (
        get_db()
        .from_("deep_research_jobs")
        .select("id, status, topic, result, sources, error, completed_at")
        .eq("id", job_id)
        .eq("brand_id", brand_id)
        .maybe_single()
        .execute()
    )
    if not result.data:
        raise DeepResearchError(f"Job {job_id} not found")
    return result.data


_IDEAS_SYSTEM = (
    "You are a content strategist. Given a research report, extract "
    "exactly the requested number of distinct content ideas. "
    "Respond ONLY with a JSON array of objects, no markdown fences. "
    "Each object must have: title (str), summary (str, ≤200 chars), "
    "angle (str, the unique perspective or hook), "
    "source_excerpt (str, a verbatim quote or key finding from the report that supports this idea, ≤300 chars)."
)


def generate_ideas(job_id: str, brand_id: str, n: int = 5) -> list[dict]:
    """Extract n content ideas from a completed deep research job and store them as research_items.

    Returns the list of created item dicts (id, title, summary).
    Raises DeepResearchError if the job is not completed or not found.
    """
    result = (
        get_db()
        .from_("deep_research_jobs")
        .select("id, status, topic, result, sources")
        .eq("id", job_id)
        .eq("brand_id", brand_id)
        .maybe_single()
        .execute()
    )
    if not result.data:
        raise DeepResearchError(f"Job {job_id} not found")

    row = result.data
    if row["status"] != "completed":
        raise DeepResearchError(f"Job {job_id} is not completed (status={row['status']})")

    report_text = row["result"]
    if isinstance(report_text, dict):
        report_text = json.dumps(report_text)

    prompt = (
        f"Research topic: {row['topic']}\n\n"
        f"Research report:\n{str(report_text)[:8000]}\n\n"
        f"Extract {n} actionable content ideas from this report."
    )

    from ..utils.llm_client import call_llm  # local import to avoid circular

    try:
        llm_response = asyncio.get_event_loop().run_until_complete(
            call_llm(prompt, brand_id, system_prompt=_IDEAS_SYSTEM, task_type="research")
        )
    except RuntimeError:
        # No event loop in this thread
        loop = asyncio.new_event_loop()
        try:
            llm_response = loop.run_until_complete(
                call_llm(prompt, brand_id, system_prompt=_IDEAS_SYSTEM, task_type="research")
            )
        finally:
            loop.close()

    raw = llm_response.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    ideas: list[dict] = json.loads(raw)

    db = get_db()
    created = []
    for idea in ideas[:n]:
        try:
            ins = db.from_("research_items").upsert({
                "brand_id": brand_id,
                "url": f"deep-research://{job_id}/{ideas.index(idea)}",
                "title": idea.get("title", "Untitled idea"),
                "summary": idea.get("summary", ""),
                "source_name": f"Deep Research: {row['topic']}",
                "source_type": "scrape",
                "retriever_type": "deep_research",
                "raw_content": idea.get("source_excerpt", ""),
                "metadata": {
                    "deep_research_job_id": job_id,
                    "angle": idea.get("angle", ""),
                },
                "status": "new",
            }, on_conflict="brand_id,url").execute()
            if ins.data:
                created.append(ins.data[0])
        except Exception as exc:
            logger.error("Failed to insert research_item for job %s: %s", job_id, exc)

    return created


def _finalize_job(job_id: str, external_id: str) -> None:
    """Fetch results from sidecar and store in DB."""
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(f"{DEEP_RESEARCH_URL}/v1/research/results/{external_id}")
            resp.raise_for_status()
            data = resp.json()

        get_db().from_("deep_research_jobs").update({
            "status": "completed",
            "result": data.get("report") or data,
            "sources": data.get("sources"),
            "completed_at": "now()",
        }).eq("id", job_id).execute()
    except Exception as exc:
        logger.error("Failed to finalize deep research job %s: %s", job_id, exc)
        get_db().from_("deep_research_jobs").update({
            "status": "failed",
            "error": str(exc),
        }).eq("id", job_id).execute()
