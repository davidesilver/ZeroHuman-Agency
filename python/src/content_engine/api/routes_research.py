"""Research API routes — deep research + competitor monitoring (Phases 7 + 9).

Endpoints:
  POST   /research/deep                    — start deep research job
  GET    /research/deep/{job_id}/status    — poll job status
  GET    /research/deep/{job_id}/results   — fetch completed results
  GET    /research/deep                    — list recent jobs

  POST   /research/competitor              — start competitor spider
  GET    /research/competitor/snapshots    — list snapshots (optionally ?url=)
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from ..db import get_db
from ..retrievers.competitor_spider import SpiderError, get_snapshots, start_spider
from ..retrievers.deep_research import (
    DeepResearchError,
    generate_ideas,
    get_results,
    get_status,
    start_job,
)

_logger = logging.getLogger("content_engine.research")

router = APIRouter(prefix="/research", tags=["research"])


def _brand_id(request: Request) -> str:
    brand_id = getattr(request.state, "brand_id", None)
    if not brand_id:
        raise HTTPException(401, "Not authenticated")
    return brand_id


# ── Deep research ─────────────────────────────────────────────────────────

class DeepResearchRequest(BaseModel):
    topic: str
    depth: int = 3


@router.post("/deep", status_code=202)
async def start_deep_research(body: DeepResearchRequest, request: Request):
    """Start a new deep research job (async, returns 202 Accepted)."""
    brand_id = _brand_id(request)
    if not body.topic.strip():
        raise HTTPException(400, "topic is required")
    if not 1 <= body.depth <= 5:
        raise HTTPException(400, "depth must be between 1 and 5")
    try:
        job_id = start_job(brand_id, body.topic.strip(), body.depth)
    except DeepResearchError as exc:
        raise HTTPException(422, str(exc))
    return {"job_id": job_id, "status": "accepted"}


@router.get("/deep")
async def list_deep_research_jobs(
    request: Request,
    status: str | None = Query(None),
    limit: int = Query(20, le=100),
):
    """List recent deep research jobs for the active brand."""
    brand_id = _brand_id(request)
    query = (
        get_db()
        .from_("deep_research_jobs")
        .select("id, topic, depth, status, error, started_at, completed_at, created_at")
        .eq("brand_id", brand_id)
        .order("created_at", desc=True)
        .limit(limit)
    )
    if status:
        query = query.eq("status", status)
    result = query.execute()
    return result.data or []


@router.get("/deep/{job_id}/status")
async def get_deep_research_status(job_id: str, request: Request):
    brand_id = _brand_id(request)
    try:
        return get_status(job_id, brand_id)
    except DeepResearchError as exc:
        raise HTTPException(404, str(exc))


@router.get("/deep/{job_id}/results")
async def get_deep_research_results(job_id: str, request: Request):
    brand_id = _brand_id(request)
    try:
        data = get_results(job_id, brand_id)
    except DeepResearchError as exc:
        raise HTTPException(404, str(exc))
    if data["status"] != "completed":
        raise HTTPException(409, f"Job is not completed yet (status: {data['status']})")
    return data


class GenerateIdeasRequest(BaseModel):
    n: int = 5


@router.post("/deep/{job_id}/generate-ideas")
async def generate_ideas_from_job(
    job_id: str, request: Request, body: GenerateIdeasRequest = GenerateIdeasRequest()
):
    """Extract n content ideas from a completed deep research job and insert them as research_items."""
    brand_id = _brand_id(request)
    if not 1 <= body.n <= 20:
        raise HTTPException(400, "n must be between 1 and 20")
    try:
        items = generate_ideas(job_id, brand_id, n=body.n)
    except DeepResearchError as exc:
        raise HTTPException(409, str(exc))
    return {"created": len(items), "items": items}


# ── Competitor monitoring ─────────────────────────────────────────────────

class CompetitorSpiderRequest(BaseModel):
    urls: list[str]


@router.post("/competitor", status_code=202)
async def start_competitor_spider(body: CompetitorSpiderRequest, request: Request):
    """Trigger competitor snapshots for a list of URLs."""
    brand_id = _brand_id(request)
    if not body.urls:
        raise HTTPException(400, "urls must be non-empty")
    try:
        snapshot_ids = start_spider(brand_id, body.urls)
    except SpiderError as exc:
        raise HTTPException(422, str(exc))
    return {"snapshot_ids": snapshot_ids, "status": "accepted"}


@router.get("/competitor/snapshots")
async def list_competitor_snapshots(
    request: Request,
    url: str | None = Query(None),
    limit: int = Query(20, le=100),
):
    """List competitor snapshots for the active brand."""
    brand_id = _brand_id(request)
    try:
        return get_snapshots(brand_id, url=url, limit=limit)
    except SpiderError as exc:
        raise HTTPException(422, str(exc))
