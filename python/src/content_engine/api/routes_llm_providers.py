"""LLM provider API routes.

GET  /llm/providers/catalog        — static provider catalog (all supported)
GET  /llm/providers                — list registered providers (legacy)
GET  /llm/providers/configured     — BYOK-configured providers for this brand
GET  /llm/providers/metrics        — aggregated telemetry (last 24h / 7d / 30d)
POST /llm/providers/{id}/key       — save BYOK API key (encrypted)
DELETE /llm/providers/{id}/key     — remove BYOK API key
POST /llm/providers/{id}/validate  — test key without saving
POST /llm/gateways/probe           — health-check a gateway URL
"""

from __future__ import annotations

import ipaddress
import logging
import socket
from typing import Literal
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from ..db import get_db
from ..services.llm.registrar import list_providers
from ..services.llm.provider_catalog import PROVIDER_CATALOG, list_providers_by_category
from ..services.brand_secrets import get_brand_secret, set_brand_secret, delete_brand_secret

_logger = logging.getLogger("content_engine.llm_providers")

router = APIRouter(prefix="/llm", tags=["llm-providers"])


def _brand_id(request: Request) -> str:
    brand_id = getattr(request.state, "brand_id", None)
    if not brand_id:
        raise HTTPException(401, "Not authenticated")
    return brand_id


@router.get("/providers/catalog")
async def get_catalog(request: Request):
    """Return the static provider catalog — no credentials, no brand state."""
    _brand_id(request)  # auth check only
    return [
        {
            "id": p.id,
            "display_name": p.display_name,
            "category": p.category,
            "api_type": p.api_type,
            "auth_type": p.auth_type,
            "billing_model": p.billing_model,
            "base_url_editable": p.base_url_editable,
            "default_base_url": p.default_base_url,
            "models": list(p.models),
            "priority": p.priority,
            "docs_url": p.docs_url,
            "logo": p.logo,
        }
        for p in sorted(PROVIDER_CATALOG.values(), key=lambda x: (x.priority, x.display_name))
    ]


@router.get("/providers/configured")
async def get_configured_providers(request: Request):
    """Return providers that have a BYOK key saved for the active brand."""
    brand_id = _brand_id(request)
    rows = (
        get_db()
        .from_("brand_integrations")
        .select("provider, key_name, updated_at")
        .eq("brand_id", brand_id)
        .eq("key_name", "api_key")
        .execute()
    )
    configured: set[str] = {r["provider"] for r in (rows.data or [])}
    return [
        {
            "id": p.id,
            "display_name": p.display_name,
            "category": p.category,
            "configured": p.id in configured,
        }
        for p in PROVIDER_CATALOG.values()
        if p.auth_type in ("api_key", "optional_key")
    ]


class KeyBody(BaseModel):
    api_key: str
    default_model: str | None = None


class ValidateBody(BaseModel):
    api_key: str


@router.post("/providers/{provider_id}/key")
async def save_provider_key(provider_id: str, body: KeyBody, request: Request):
    """Validate format, test the key, then encrypt and save to brand_integrations."""
    brand_id = _brand_id(request)

    defn = PROVIDER_CATALOG.get(provider_id)
    if not defn:
        raise HTTPException(404, f"Unknown provider: {provider_id}")
    if defn.auth_type == "none":
        raise HTTPException(400, f"Provider {provider_id} does not use API keys")

    api_key = body.api_key.strip()
    if not api_key:
        raise HTTPException(400, "api_key must not be empty")
    if defn.key_prefix and not api_key.startswith(defn.key_prefix):
        raise HTTPException(400, f"Key must start with '{defn.key_prefix}'")

    # Test the key before saving
    valid, error, latency_ms, models = _test_provider_key(defn, api_key)
    if not valid:
        raise HTTPException(400, f"Key validation failed: {error}")

    set_brand_secret(brand_id, provider_id, "api_key", api_key)
    if body.default_model:
        set_brand_secret(brand_id, provider_id, "default_model", body.default_model)

    return {"valid": True, "latency_ms": latency_ms, "models": models[:20]}


@router.delete("/providers/{provider_id}/key")
async def delete_provider_key(provider_id: str, request: Request):
    """Remove a BYOK key from brand_integrations."""
    brand_id = _brand_id(request)
    if provider_id not in PROVIDER_CATALOG:
        raise HTTPException(404, f"Unknown provider: {provider_id}")
    delete_brand_secret(brand_id, provider_id, "api_key")
    delete_brand_secret(brand_id, provider_id, "default_model")
    return {"deleted": True}


@router.post("/providers/{provider_id}/validate")
async def validate_provider_key(provider_id: str, body: ValidateBody, request: Request):
    """Test a key without saving it. Returns latency and available models."""
    _brand_id(request)

    defn = PROVIDER_CATALOG.get(provider_id)
    if not defn:
        raise HTTPException(404, f"Unknown provider: {provider_id}")

    api_key = body.api_key.strip()
    if not api_key:
        raise HTTPException(400, "api_key must not be empty")

    valid, error, latency_ms, models = _test_provider_key(defn, api_key)
    return {"valid": valid, "error": error, "latency_ms": latency_ms, "models": models[:20]}


class ProbeBody(BaseModel):
    url: str


@router.post("/gateways/probe")
async def probe_gateway(body: ProbeBody, request: Request):
    """Health-check a local gateway by fetching its /v1/models endpoint.

    SSRF protection: only localhost and RFC-1918 addresses are allowed.
    """
    _brand_id(request)

    url = body.url.strip().rstrip("/")
    _assert_safe_gateway_url(url)

    import time
    t0 = time.monotonic()
    try:
        with httpx.Client(timeout=5.0, follow_redirects=False) as client:
            resp = client.get(f"{url}/models")
            resp.raise_for_status()
            data = resp.json()
        latency_ms = int((time.monotonic() - t0) * 1000)
        models = [m["id"] for m in data.get("data", [])]

        # Ollama native format fallback
        if not models and "models" in data:
            models = [m.get("name", m.get("id", "")) for m in data["models"]]

        return {"online": True, "models": models, "latency_ms": latency_ms}
    except Exception as exc:
        latency_ms = int((time.monotonic() - t0) * 1000)
        return {"online": False, "error": str(exc), "latency_ms": latency_ms}


@router.get("/gateways/auto-discover")
async def auto_discover_gateways(request: Request):
    """Probe all default gateway ports and return which ones are online."""
    _brand_id(request)
    import concurrent.futures, time

    defaults = [
        {"id": "ollama",    "display_name": "Ollama",     "url": "http://localhost:11434"},
        {"id": "openclaw",  "display_name": "OpenClaw",   "url": "http://localhost:18789"},
        {"id": "lmstudio",  "display_name": "LM Studio",  "url": "http://localhost:1234"},
        {"id": "vllm",      "display_name": "vLLM",        "url": "http://localhost:8000"},
        {"id": "litellm",   "display_name": "LiteLLM",    "url": "http://localhost:4000"},
    ]

    def _probe_one(entry: dict) -> dict:
        t0 = time.monotonic()
        try:
            with httpx.Client(timeout=2.0, follow_redirects=False) as client:
                resp = client.get(f"{entry['url']}/v1/models")
                resp.raise_for_status()
                data = resp.json()
            latency_ms = int((time.monotonic() - t0) * 1000)
            models = [m["id"] for m in data.get("data", [])]
            if not models and "models" in data:
                models = [m.get("name", m.get("id", "")) for m in data["models"]]
            return {**entry, "online": True, "models": models, "latency_ms": latency_ms}
        except Exception as exc:
            return {**entry, "online": False, "models": [], "latency_ms": int((time.monotonic() - t0) * 1000), "error": str(exc)}

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(_probe_one, defaults))

    return results


class GatewayUrlBody(BaseModel):
    base_url: str


@router.post("/gateways/{gateway_id}/url")
async def save_gateway_url(gateway_id: str, body: GatewayUrlBody, request: Request):
    """Save a custom base URL for a gateway provider."""
    brand_id = _brand_id(request)
    defn = PROVIDER_CATALOG.get(gateway_id)
    if not defn or defn.category != "gateway":
        raise HTTPException(404, f"Unknown gateway: {gateway_id}")

    url = body.base_url.strip().rstrip("/")
    if not url:
        raise HTTPException(400, "base_url must not be empty")

    set_brand_secret(brand_id, gateway_id, "base_url", url)
    return {"saved": True, "base_url": url}


@router.get("/providers")
async def get_providers(request: Request):
    """List all registered LLM providers (legacy endpoint)."""
    _brand_id(request)
    return list_providers()


@router.get("/providers/metrics")
async def get_provider_metrics(
    request: Request,
    window: Literal["24h", "7d", "30d"] = Query("7d"),
):
    """Return aggregated provider metrics for the active brand.

    Returns per-provider stats: total_calls, avg_latency_ms, total_cost_usd,
    avg_cost_per_1k_tokens, error_rate.
    """
    brand_id = _brand_id(request)
    interval = {"24h": "1 day", "7d": "7 days", "30d": "30 days"}[window]

    try:
        result = get_db().rpc(
            "llm_provider_stats",
            {"p_brand_id": brand_id, "p_interval": interval},
        ).execute()
        return result.data or []
    except Exception:
        # RPC may not exist yet — fall back to direct query
        rows = (
            get_db()
            .from_("llm_provider_metrics")
            .select("provider, model, latency_ms, cost_usd, is_fallback, error, prompt_tokens, completion_tokens")
            .eq("brand_id", brand_id)
            .gte("ts", f"now() - interval '{interval}'")
            .execute()
        )
        if not rows.data:
            return []

        # Aggregate in Python
        from collections import defaultdict
        stats: dict[str, dict] = defaultdict(lambda: {
            "total_calls": 0,
            "error_calls": 0,
            "total_latency_ms": 0,
            "total_cost_usd": 0.0,
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
        })
        for row in rows.data:
            p = row["provider"]
            stats[p]["total_calls"] += 1
            if row.get("error"):
                stats[p]["error_calls"] += 1
            if row.get("latency_ms"):
                stats[p]["total_latency_ms"] += row["latency_ms"]
            if row.get("cost_usd"):
                stats[p]["total_cost_usd"] += float(row["cost_usd"])
            stats[p]["total_prompt_tokens"] += row.get("prompt_tokens", 0) or 0
            stats[p]["total_completion_tokens"] += row.get("completion_tokens", 0) or 0

        result = []
        for provider, s in stats.items():
            total = s["total_calls"]
            total_tokens = s["total_prompt_tokens"] + s["total_completion_tokens"]
            result.append({
                "provider": provider,
                "window": window,
                "total_calls": total,
                "error_rate": round(s["error_calls"] / total, 4) if total else 0,
                "avg_latency_ms": round(s["total_latency_ms"] / total) if total else None,
                "total_cost_usd": round(s["total_cost_usd"], 6),
                "cost_per_1k_tokens": round(
                    s["total_cost_usd"] / (total_tokens / 1000), 6
                ) if total_tokens else None,
            })
        return result


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _test_provider_key(
    defn,
    api_key: str,
) -> tuple[bool, str | None, int, list[str]]:
    """Test an API key against the provider. Returns (valid, error, latency_ms, models)."""
    import time

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    t0 = time.monotonic()

    if defn.api_type == "anthropic_native":
        try:
            import anthropic as _anthropic
            client = _anthropic.Anthropic(api_key=api_key)
            client.models.list()
            latency_ms = int((time.monotonic() - t0) * 1000)
            return True, None, latency_ms, ["claude-sonnet-4-20250514", "claude-haiku-4-20250514"]
        except Exception as exc:
            return False, str(exc), int((time.monotonic() - t0) * 1000), []

    # OpenAI-compatible
    base_url = defn.default_base_url.rstrip("/")

    if defn.key_validation == "models_list":
        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.get(f"{base_url}/models", headers=headers)
                resp.raise_for_status()
                data = resp.json()
            latency_ms = int((time.monotonic() - t0) * 1000)
            models = [m["id"] for m in data.get("data", [])]
            return True, None, latency_ms, models
        except Exception as exc:
            return False, str(exc), int((time.monotonic() - t0) * 1000), []

    # chat_completion validation (for providers without /models endpoint)
    try:
        model = defn.models[0] if defn.models else "gpt-4o-mini"
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json={"model": model, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 1},
            )
            resp.raise_for_status()
        latency_ms = int((time.monotonic() - t0) * 1000)
        return True, None, latency_ms, list(defn.models)
    except Exception as exc:
        return False, str(exc), int((time.monotonic() - t0) * 1000), []


_PRIVATE_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
]


def _assert_safe_gateway_url(url: str) -> None:
    """Raise HTTPException if the URL targets a non-local/non-private host."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(400, "Gateway URL must use http or https")

    host = parsed.hostname or ""
    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    if port < 1024:
        raise HTTPException(400, f"Port {port} is not allowed (use 1024+)")

    # Resolve hostname to IP
    try:
        addr = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
        ip_str = addr[0][4][0]
        ip = ipaddress.ip_address(ip_str)
    except Exception:
        raise HTTPException(400, f"Cannot resolve host: {host}")

    if ip.is_link_local:
        raise HTTPException(400, "Link-local addresses are not allowed")

    allowed = ip.is_loopback or any(ip in net for net in _PRIVATE_RANGES)
    if not allowed:
        raise HTTPException(400, "Gateway URL must point to localhost or a private network address")
