import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .api.routes_agents import router as agents_router
from .api.routes_images import router as images_router
from .api.auth_middleware import JWTAuthMiddleware
from .utils.rate_limiter_persistent import PersistentRateLimitMiddleware
from .utils.logging_config import setup_logging

# L-03: Structured JSON logging (replaces basicConfig)
setup_logging()

_logger = logging.getLogger("content_engine")

app = FastAPI(title="Content Engine Backend", version="0.1.0")

# H-01: CORS configured from ALLOWED_ORIGINS env var (comma-separated)
# Restrictive methods/headers — no wildcards in production
_raw_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000")
_allowed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]
if "*" in _allowed_origins:
    _logger.warning("ALLOWED_ORIGINS contains wildcard '*' — this is insecure in production!")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Scheduler-Secret", "X-Request-ID"],
)

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
