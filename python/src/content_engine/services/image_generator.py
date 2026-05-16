"""Autonomous image generation with async job queue.

Flow:
  1. Caller requests generation → `create_image_job()` inserts `pending` row
     and returns immediately with `job_id`.
  2. Background `asyncio.create_task` executes `_run_image_job()` which:
       a. Loads draft + brand config
       b. Builds prompt
       c. Calls backend
       d. Uploads to Storage
       e. Appends URL to content_drafts.media_urls
       f. Tracks cost + logs to memory_events
  3. Client polls `GET /images/jobs/{job_id}` until terminal state.

Retry:
  - Failed jobs store attempt count in `metadata`. Automatic retry up to
    MAX_RETRIES with exponential backoff.
  - After max retries the job stays `failed`.

Cost/failure handling:
  - Every call is logged even on failure (status='failed' + error text).
  - cost_usd is passed into cost_tracker so the per-brand daily cap applies.
"""
from __future__ import annotations
import asyncio
import logging
from typing import Optional
from uuid import uuid4

from ..config import settings
from ..db import get_db
from ..utils.brand_assets import get_brand_palette
from ..utils.cost_tracker import track_cost, check_daily_cost_cap, CostCapExceeded
from ..memory import events as memory_events
from .image_backends import get_backend
from .image_prompt_builder import build_prompt

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
JOB_TIMEOUT_SECONDS = 300  # 5 minutes
MAX_CONCURRENT_JOBS_PER_BRAND = 3

# Per-brand semaphores to limit concurrent generation jobs
_brand_semaphores: dict[str, asyncio.Semaphore] = {}


def _get_brand_semaphore(brand_id: str) -> asyncio.Semaphore:
    if brand_id not in _brand_semaphores:
        _brand_semaphores[brand_id] = asyncio.Semaphore(MAX_CONCURRENT_JOBS_PER_BRAND)
    return _brand_semaphores[brand_id]


# ── Public API ───────────────────────────────────────────────────────────────

async def create_image_job(
    brand_id: str, draft_id: str, *, width: int = 1024, height: int = 1024,
) -> dict:
    """Enqueue a new image generation job and return immediately.

    Returns {"id": <uuid>, "status": "pending"} so the caller can poll.
    """
    db = get_db()

    # Validate draft exists AND belongs to caller's brand (prevent cross-tenant IDOR)
    draft = (
        db.table("content_drafts")
        .select("id")
        .eq("id", draft_id)
        .eq("brand_id", brand_id)
        .single()
        .execute()
        .data
    )
    if not draft:
        raise ValueError(f"Draft {draft_id} not found")

    # Pre-flight cost cap check (fail fast before enqueueing)
    try:
        await check_daily_cost_cap(brand_id)
    except CostCapExceeded as cap_exc:
        gen_row = db.table("image_generations").insert({
            "brand_id": brand_id, "draft_id": draft_id,
            "backend": "", "model_id": "",
            "prompt": "", "status": "failed",
            "error": str(cap_exc)[:500], "finished_at": "now()",
        }).execute().data[0]
        return {"id": gen_row["id"], "status": "failed", "error": str(cap_exc)}

    # Insert pending row
    gen_row = db.table("image_generations").insert({
        "brand_id": brand_id, "draft_id": draft_id,
        "backend": "", "model_id": "",
        "prompt": "", "status": "pending",
    }).execute().data[0]
    gen_id = gen_row["id"]

    # Fire background task; attach callback to surface unhandled errors
    # (otherwise asyncio.create_task failures are silently dropped).
    task = asyncio.create_task(
        _run_image_job_with_timeout(gen_id, brand_id, draft_id, width, height),
        name=f"image-job-{gen_id}",
    )

    def _log_task_exc(t: asyncio.Task) -> None:
        if t.cancelled():
            return
        exc = t.exception()
        if exc is not None:
            logger.error(
                "Background image job %s crashed: %s", gen_id, exc, exc_info=exc,
            )

    task.add_done_callback(_log_task_exc)

    return {"id": gen_id, "status": "pending"}


async def get_image_job(gen_id: str, brand_id: str | None = None) -> dict:
    """Poll endpoint: return current status of a generation job.

    When ``brand_id`` is provided, the job must belong to that brand
    (prevents cross-tenant IDOR via guessed job UUIDs).
    """
    db = get_db()
    query = db.table("image_generations").select("*").eq("id", gen_id)
    if brand_id is not None:
        query = query.eq("brand_id", brand_id)
    row = query.single().execute().data
    if not row:
        raise ValueError(f"Job {gen_id} not found")
    return {
        "id": row["id"],
        "status": row["status"],
        "url": row.get("public_url"),
        "error": row.get("error"),
        "cost_usd": row.get("cost_usd"),
        "width_px": row.get("width_px"),
        "height_px": row.get("height_px"),
        "created_at": row.get("created_at"),
        "started_at": row.get("started_at"),
        "finished_at": row.get("finished_at"),
    }


async def generate_image_for_draft(
    brand_id: str, draft_id: str, *, width: int = 1024, height: int = 1024,
) -> dict:
    """Synchronous-style wrapper that blocks until the job completes.

    Used by carousels and legacy callers. Prefer `create_image_job()` + poll
    for UI-facing endpoints to avoid Vercel timeouts.
    """
    job = await create_image_job(brand_id, draft_id, width=width, height=height)
    if job["status"] == "failed":
        return job

    gen_id = job["id"]

    # Poll locally until terminal state (max 5 min)
    for _ in range(150):  # 150 × 2s = 300s
        await asyncio.sleep(2)
        state = await get_image_job(gen_id)
        if state["status"] in ("succeeded", "failed"):
            return state

    # Timeout — mark failed
    db = get_db()
    db.table("image_generations").update({
        "status": "failed", "error": "timeout", "finished_at": "now()",
    }).eq("id", gen_id).execute()
    return {"id": gen_id, "status": "failed", "error": "timeout"}


async def generate_carousel_for_draft(
    brand_id: str, draft_id: str, *, slides: int = 5,
) -> dict:
    """Generate N images in parallel (default 5 = typical Instagram carousel)."""
    tasks = [
        generate_image_for_draft(brand_id, draft_id, width=1080, height=1350)
        for _ in range(slides)
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    out = [r if isinstance(r, dict) else {"status": "failed", "error": str(r)} for r in results]
    return {
        "slides": out,
        "total": len(out),
        "succeeded": sum(1 for r in out if r.get("status") == "succeeded"),
    }


# ── Internal execution ───────────────────────────────────────────────────────

async def _run_image_job_with_timeout(
    gen_id: str, brand_id: str, draft_id: str, width: int, height: int,
) -> None:
    """Wrapper that enforces JOB_TIMEOUT_SECONDS and per-brand concurrency."""
    sem = _get_brand_semaphore(brand_id)
    # asyncio.Semaphore does not accept blocking=False; use sem.locked() to check.
    if sem.locked():
        logger.warning("Brand %s has too many concurrent image jobs", brand_id)
        db = get_db()
        db.table("image_generations").update({
            "status": "failed",
            "error": f"Too many concurrent jobs (max {MAX_CONCURRENT_JOBS_PER_BRAND})",
            "finished_at": "now()",
        }).eq("id", gen_id).execute()
        return

    await sem.acquire()
    try:
        await asyncio.wait_for(
            _run_image_job(gen_id, brand_id, draft_id, width, height),
            timeout=JOB_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.error("Image job %s timed out after %ds", gen_id, JOB_TIMEOUT_SECONDS)
        db = get_db()
        db.table("image_generations").update({
            "status": "failed", "error": "timeout", "finished_at": "now()",
        }).eq("id", gen_id).execute()
    except Exception as e:
        logger.exception("Unhandled exception in image job %s", gen_id)
        db = get_db()
        db.table("image_generations").update({
            "status": "failed", "error": str(e)[:500], "finished_at": "now()",
        }).eq("id", gen_id).execute()
    finally:
        sem.release()


async def _run_image_job(
    gen_id: str, brand_id: str, draft_id: str, width: int, height: int,
) -> None:
    db = get_db()

    # Load config
    draft = (
        db.table("content_drafts")
        .select("id,title,body")
        .eq("id", draft_id)
        .single()
        .execute()
        .data
    )
    if not draft:
        raise ValueError(f"Draft {draft_id} not found")

    brand = (
        db.table("brands")
        .select("name, image_model, image_backend, image_style_preset, image_prompt_template")
        .eq("id", brand_id)
        .single()
        .execute()
        .data
        or {}
    )

    model_id = brand.get("image_model") or settings.default_image_model
    backend_name = brand.get("image_backend") or settings.default_image_backend
    style_preset = brand.get("image_style_preset") or "editorial-minimal"
    prompt_tpl = brand.get("image_prompt_template")
    palette = get_brand_palette(brand_id)

    prompt = build_prompt(
        draft_title=draft["title"] or "",
        draft_body=draft["body"] or "",
        brand_name=brand.get("name", ""),
        palette_hex=palette,
        style_preset=style_preset,
        prompt_template=prompt_tpl,
    )

    # Mark running
    db.table("image_generations").update({
        "backend": backend_name,
        "model_id": model_id,
        "prompt": prompt,
        "status": "running",
        "started_at": "now()",
    }).eq("id", gen_id).execute()

    # Retry loop
    attempt = 0
    last_error = ""
    while attempt < MAX_RETRIES:
        attempt += 1
        try:
            backend = get_backend(backend_name)
            result = await backend.generate(
                prompt=prompt,
                negative_prompt=None,
                model_id=model_id,
                width=width,
                height=height,
                seed=None,
            )

            # Upload bytes to Storage. Path MUST start with brand_id for RLS.
            storage_path = f"{brand_id}/{uuid4().hex}.png"
            db.storage.from_("generated-images").upload(
                path=storage_path,
                file=result.image_bytes,
                file_options={"content-type": result.mime_type, "upsert": "false"},
            )
            signed = db.storage.from_("generated-images").create_signed_url(
                storage_path, 60 * 60 * 24 * 7
            )
            public_url = signed.get("signedURL") or signed.get("signed_url")

            # Update job row
            db.table("image_generations").update({
                "status": "succeeded",
                "storage_path": storage_path,
                "public_url": public_url,
                "width_px": result.width_px,
                "height_px": result.height_px,
                "cost_usd": result.cost_usd,
                "finished_at": "now()",
            }).eq("id", gen_id).execute()

            # Append to draft media_urls
            draft_row = (
                db.table("content_drafts")
                .select("media_urls")
                .eq("id", draft_id)
                .single()
                .execute()
                .data
            )
            current_media = list(draft_row.get("media_urls") or [])
            current_media.append(public_url)
            db.table("content_drafts").update({"media_urls": current_media}).eq(
                "id", draft_id
            ).execute()

            # Track cost
            await track_cost(
                brand_id=brand_id,
                agent_name="image_generator",
                model=model_id,
                operation=f"generate:{backend_name}",
                input_chars=0,
                output_chars=0,
                cost_usd=result.cost_usd,
            )

            # Log to memory_events
            await memory_events.log(
                brand_id=brand_id,
                kind="image_generated",
                summary=f"{backend_name}:{model_id} — {result.width_px}×{result.height_px} — ${result.cost_usd:.4f}",
                subject_kind="content_draft",
                subject_id=draft_id,
                payload={
                    "prompt": prompt,
                    "style_preset": style_preset,
                    "palette_size": len(palette),
                    "public_url": public_url,
                },
            )

            return  # Success — exit retry loop

        except Exception as e:
            last_error = str(e)[:500]
            logger.warning(
                "Image generation attempt %d/%d failed for job %s: %s",
                attempt, MAX_RETRIES, gen_id, last_error
            )
            if attempt < MAX_RETRIES:
                backoff = 2 ** attempt  # 2, 4, 8 seconds
                await asyncio.sleep(backoff)

    # All retries exhausted
    db.table("image_generations").update({
        "status": "failed",
        "error": last_error,
        "finished_at": "now()",
    }).eq("id", gen_id).execute()
