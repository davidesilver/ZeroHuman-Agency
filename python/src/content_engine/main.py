import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .utils.rate_limiter import RateLimitMiddleware

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

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
    allow_headers=["Authorization", "Content-Type", "X-Scheduler-Secret"],
)

# Rate limiting — protects expensive LLM-calling routes
app.add_middleware(RateLimitMiddleware)

app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "ok"}
