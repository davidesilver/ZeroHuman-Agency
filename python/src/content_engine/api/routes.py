from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..db import get_db
from ..models import TriggerRequest, ScoringRequest
from ..orchestrator.research import run_research
from ..scoring.engine import run_scoring

router = APIRouter(prefix="/api")

BRAND_ID = "b6e639ac-33e7-402b-b928-c98af55eec47"  # Vest — will be dynamic later


@router.post("/research/trigger")
async def trigger_research(req: TriggerRequest | None = None):
    if req is None:
        req = TriggerRequest()
    result = await run_research(BRAND_ID, req)
    return {"success": True, "data": result.model_dump()}


@router.get("/research/runs")
async def list_runs(
    status: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    db = get_db()
    query = (
        db.table("research_runs")
        .select("*", count="exact")
        .eq("brand_id", BRAND_ID)
        .order("created_at", desc=True)
    )
    if status:
        query = query.eq("status", status)
    query = query.range((page - 1) * per_page, page * per_page - 1)
    resp = query.execute()
    return {
        "success": True,
        "data": resp.data,
        "meta": {
            "page": page,
            "per_page": per_page,
            "total": resp.count or 0,
        },
    }


@router.get("/research/items")
async def list_items(
    status: str | None = None,
    run_id: str | None = None,
    retriever: str | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    db = get_db()
    query = (
        db.table("research_items")
        .select("*, scores(*)", count="exact")
        .eq("brand_id", BRAND_ID)
    )
    if status:
        query = query.eq("status", status)
    if run_id:
        query = query.eq("run_id", run_id)
    if retriever:
        query = query.eq("retriever", retriever)
    query = query.order(sort_by, desc=(sort_order == "desc"))
    query = query.range((page - 1) * per_page, page * per_page - 1)
    resp = query.execute()
    return {
        "success": True,
        "data": resp.data,
        "meta": {
            "page": page,
            "per_page": per_page,
            "total": resp.count or 0,
        },
    }


@router.patch("/research/items/{item_id}/status")
async def update_item_status(item_id: str, body: dict):
    new_status = body.get("status")
    if new_status not in ("new", "scored", "approved", "rejected", "archived"):
        raise HTTPException(400, "Invalid status")
    db = get_db()
    resp = (
        db.table("research_items")
        .update({"status": new_status})
        .eq("id", item_id)
        .eq("brand_id", BRAND_ID)
        .execute()
    )
    if not resp.data:
        raise HTTPException(404, "Item not found")
    return {"success": True, "data": resp.data[0]}


@router.post("/scoring/run")
async def trigger_scoring(req: ScoringRequest | None = None):
    if req is None:
        req = ScoringRequest()
    result = await run_scoring(BRAND_ID, req)
    return {"success": True, "data": result}


@router.get("/research/stats")
async def research_stats():
    db = get_db()
    items = (
        db.table("research_items")
        .select("status", count="exact")
        .eq("brand_id", BRAND_ID)
        .execute()
    )
    # Count by status
    all_items = (
        db.table("research_items")
        .select("id, status")
        .eq("brand_id", BRAND_ID)
        .execute()
    )
    counts = {"total": 0, "pending": 0, "approved": 0, "rejected": 0, "archived": 0, "top_pick": 0}
    for item in all_items.data:
        counts["total"] += 1
        s = item.get("status", "pending")
        if s in counts:
            counts[s] += 1
    return {"success": True, "data": counts}
