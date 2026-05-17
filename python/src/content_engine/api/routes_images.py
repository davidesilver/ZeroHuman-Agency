# routes_images.py
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..db import get_db
from ..services.image_generator import (
    create_image_job,
    get_image_job,
    generate_carousel_for_draft,
)

router = APIRouter(prefix="/images", tags=["images"])


def _get_brand_id(request: Request) -> str:
    """Resolve brand_id from JWT middleware (same helper as routes.py)."""
    brand_id = getattr(request.state, "brand_id", None)
    if not brand_id:
        raise HTTPException(
            status_code=401,
            detail="Authenticated brand context not found. Ensure you are logged in.",
        )
    return brand_id


class GenerateBody(BaseModel):
    draft_id: str
    width: int = 1024
    height: int = 1024


class CarouselBody(BaseModel):
    draft_id: str
    slides: int = 5


@router.post("/generate")
async def generate(body: GenerateBody, request: Request):
    brand_id = _get_brand_id(request)
    if body.width not in (512, 768, 1024, 1080, 1536) or body.height not in (512, 768, 1024, 1350, 1536):
        raise HTTPException(400, "Unsupported dimensions")
    return await create_image_job(brand_id, body.draft_id, width=body.width, height=body.height)


@router.post("/carousel")
async def carousel(body: CarouselBody, request: Request):
    brand_id = _get_brand_id(request)
    if not 2 <= body.slides <= 10:
        raise HTTPException(400, "slides must be 2..10")
    return await generate_carousel_for_draft(brand_id, body.draft_id, slides=body.slides)


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, request: Request):
    """Poll endpoint for async image generation jobs (brand-scoped)."""
    brand_id = _get_brand_id(request)
    try:
        return await get_image_job(job_id, brand_id=brand_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get("/stats")
async def get_stats(request: Request):
    """Return image generation stats for the authenticated brand."""
    brand_id = _get_brand_id(request)
    db = get_db()

    from datetime import datetime, timezone
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    ).isoformat()

    # Today's count + cost
    today_rows = (
        db.table("image_generations")
        .select("cost_usd")
        .eq("brand_id", brand_id)
        .gte("created_at", today_start)
        .execute()
        .data
        or []
    )
    today_count = len(today_rows)
    today_cost = sum(float(r.get("cost_usd", 0) or 0) for r in today_rows)

    # Recent jobs (last 20)
    recent = (
        db.table("image_generations")
        .select("*")
        .eq("brand_id", brand_id)
        .order("created_at", desc=True)
        .limit(20)
        .execute()
        .data
        or []
    )

    return {
        "success": True,
        "data": {
            "today": {"count": today_count, "cost_usd": round(today_cost, 4)},
            "recent_jobs": recent,
        },
    }
