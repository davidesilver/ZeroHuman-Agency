import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.auth_middleware import JWTAuthMiddleware
from .api.setup_mode_middleware import SetupModeMiddleware
from .api.routes import router
from .api.routes_agents import router as agents_router
from .api.routes_images import router as images_router
from .utils.logging_config import setup_logging
from .utils.rate_limiter_persistent import PersistentRateLimitMiddleware

# L-03: Structured JSON logging (replaces basicConfig)
setup_logging()

_logger = logging.getLogger("content_engine")

app = FastAPI(title="Content Engine Backend", version="0.1.0")

# H-01: CORS configured from ALLOWED_ORIGINS env var (comma-separated)
# Restrictive methods/headers — no wildcards in production
_raw_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3080")
_allowed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]
_debug_mode = os.environ.get("DEBUG", "").strip().lower() in ("1", "true", "yes")
if "*" in _allowed_origins:
    if not _debug_mode:
        raise RuntimeError(
            "Refusing to start: ALLOWED_ORIGINS contains '*' but DEBUG is not enabled. "
            "Set DEBUG=true for local development or restrict ALLOWED_ORIGINS for production."
        )
    _logger.warning(
        "ALLOWED_ORIGINS contains wildcard '*' — accepted only because DEBUG=true."
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Scheduler-Secret", "X-Request-ID"],
)

# Setup mode guard — short-circuits all non-health routes when Supabase
# URL is not configured. Must be outermost (added last in LIFO stack).
app.add_middleware(SetupModeMiddleware)

# H-03: Persistent rate limiting — Supabase-backed sliding window
# Falls back to in-memory if DB unavailable (fail-open with warning logged)
app.add_middleware(PersistentRateLimitMiddleware)

# C-01/C-02: JWT authentication — must be added AFTER rate limiting
# (middleware stack is LIFO: last added = first executed)
app.add_middleware(JWTAuthMiddleware)

app.include_router(router)
app.include_router(agents_router)
app.include_router(images_router)

# P9: Postiz social publishing bridge (health, integrations CRUD, analytics)
from .api.routes_postiz import router as postiz_router

app.include_router(postiz_router)  # prefix="/social" already declared in routes_postiz.py

# Phase 3: Email marketing (Brevo)
from .api.routes_email_marketing import router as email_marketing_router

app.include_router(email_marketing_router)

# Phase 0: Internal brand secrets management
from .api.routes_internal import router as internal_router

app.include_router(internal_router)

# Phase 4: LLM provider list + metrics
from .api.routes_llm_providers import router as llm_providers_router

app.include_router(llm_providers_router)

# Phases 7+9: Deep research + competitor monitoring
from .api.routes_research import router as research_ext_router

app.include_router(research_ext_router)

# Phase 10: HyperFrames video rendering
from .api.routes_video import router as video_router

app.include_router(video_router)

# Phase 5: Brevo campaigns
from .api.routes_campaigns import router as campaigns_router
from .api.routes_campaigns import webhook_router as campaigns_webhook_router

app.include_router(campaigns_router)
app.include_router(campaigns_webhook_router)

# Phase 6: Brevo automations
from .api.routes_automations import router as automations_router

app.include_router(automations_router)

# Brand voice auto-discovery from website URLs and social profiles
from .api.routes_brand_discovery import router as brand_discovery_router

app.include_router(brand_discovery_router)

# Setup wizard progress tracking
from .api.routes_setup import router as setup_router

app.include_router(setup_router)


@app.on_event("shutdown")
async def _close_shared_clients() -> None:
    """Tear down module-level httpx pools on graceful shutdown."""
    from .services.postiz_client import close_shared_client
    await close_shared_client()


def serve() -> None:
    """Entry point for `uv run serve` — starts uvicorn on port 8082."""
    import uvicorn
    uvicorn.run(
        "content_engine.main:app",
        host="0.0.0.0",
        port=8082,
        reload=os.environ.get("DEBUG", "").strip().lower() in ("1", "true", "yes"),
    )


@app.get("/health")
async def health():
    """Basic liveness probe — always returns 200 if the process is up."""
    return {"status": "ok"}


@app.get("/health/db")
async def health_db():
    """L-04: Readiness probe — verifies the Supabase DB connection."""
    import time

    from .db import get_db
    try:
        t0 = time.monotonic()
        db = get_db()
        # Lightweight query: select 1 from brands limit 1
        db.table("brands").select("id").limit(1).execute()
        latency_ms = round((time.monotonic() - t0) * 1000)
        return {"status": "ok", "db": "connected", "latency_ms": latency_ms}
    except Exception as e:
        _logger.error("DB health check failed: %s", e)
        from fastapi import HTTPException
        raise HTTPException(503, "Database connection failed")
