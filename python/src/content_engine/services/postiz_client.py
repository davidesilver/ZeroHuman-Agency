"""Typed HTTP client for Postiz Public API.

Works with both self-hosted (docker-compose.postiz.yaml) and cloud/managed
Postiz instances. The only difference is the base_url.

Endpoints used:
  GET  /public/v1/integrations
  POST /public/v1/posts
  GET  /public/v1/posts
  DELETE /public/v1/posts/:id
  GET  /public/v1/analytics/:integration
  GET  /public/v1/analytics/post/:postId

CLI path for read-only analytics (PrintingPress postiz):
  Generate from your self-hosted instance: printing-press http://localhost:3001/api-json
  Binary:   postiz  (or override via PP_POSTIZ_BIN env var)
  Commands: postiz analytics post <postId>
            postiz analytics integration <integrationId> --days 7
  Cache:    SQLite local — analytics polled within 1 h skip network round-trip.

Write operations (create_post, delete_post) always use direct HTTP with
retry+idempotency keys — CLI caching is counterproductive for writes.
"""
from __future__ import annotations

import logging
import os
import random
from typing import Optional
import asyncio

import httpx

from ..config import settings
from ..utils.cli_runner import CLINotFoundError, run_cli

_logger = logging.getLogger("content_engine.postiz_client")
_CLI_BINARY_ENV = "PP_POSTIZ_BIN"
_CLI_BINARY_DEFAULT = "postiz"

_RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}
_MAX_ATTEMPTS = 3

# Module-level shared AsyncClient.  Postiz analytics fans out across hundreds
# of posts per day; one TCP/TLS handshake per call drowned the event loop.
# Limits chosen to be polite to a self-hosted Postiz: max 20 concurrent + 100
# keep-alive sockets total.
_HTTP_LIMITS = httpx.Limits(max_connections=100, max_keepalive_connections=20)
_SHARED_CLIENT: httpx.AsyncClient | None = None
_SHARED_CLIENT_LOCK = asyncio.Lock()


async def get_shared_client() -> httpx.AsyncClient:
    """Lazy-initialise the shared AsyncClient on first use."""
    global _SHARED_CLIENT
    if _SHARED_CLIENT is None or _SHARED_CLIENT.is_closed:
        async with _SHARED_CLIENT_LOCK:
            if _SHARED_CLIENT is None or _SHARED_CLIENT.is_closed:
                _SHARED_CLIENT = httpx.AsyncClient(
                    timeout=httpx.Timeout(60.0, connect=10.0),
                    limits=_HTTP_LIMITS,
                )
    return _SHARED_CLIENT


async def close_shared_client() -> None:
    """Tear-down hook for app shutdown."""
    global _SHARED_CLIENT
    if _SHARED_CLIENT is not None and not _SHARED_CLIENT.is_closed:
        await _SHARED_CLIENT.aclose()
    _SHARED_CLIENT = None


def _mask(secret: str | None) -> str:
    """Return a redacted form safe for logs/exceptions."""
    if not secret:
        return "<unset>"
    if len(secret) <= 8:
        return "***"
    return f"{secret[:4]}…{secret[-2:]}"


class PostizClient:
    """HTTP client for Postiz Public API.

    Uses a shared module-level httpx.AsyncClient (see get_shared_client) so
    analytics loops, schedulers, and ad-hoc publishes all reuse the same
    connection pool.

    Args:
        api_url: Postiz base URL (e.g. http://localhost:3001 or https://api.postiz.com).
                 Defaults to settings.postiz_api_url.
        api_key: Postiz API key from Settings → API. Defaults to settings.postiz_api_key.
    """

    def __init__(self, api_url: str | None = None, api_key: str | None = None):
        self.api_url = (api_url or settings.postiz_api_url or "").rstrip("/")
        self.api_key = api_key or settings.postiz_api_key or ""

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"PostizClient(api_url={self.api_url!r}, api_key={_mask(self.api_key)})"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _check_config(self) -> None:
        if not self.api_url:
            raise RuntimeError("Postiz API URL not configured (POSTIZ_API_URL)")
        if not self.api_key:
            raise RuntimeError("Postiz API key not configured (POSTIZ_API_KEY)")

    # ── Integrations ──────────────────────────────────────────────────────────

    async def list_integrations(self) -> list[dict]:
        """List all connected social integrations in Postiz."""
        self._check_config()
        c = await get_shared_client()
        r = await c.get(
            f"{self.api_url}/public/v1/integrations",
            headers=self._headers(),
            timeout=30,
        )
        r.raise_for_status()
        return r.json()

    async def get_integration(self, integration_id: str) -> dict:
        """Get details for a single integration."""
        self._check_config()
        c = await get_shared_client()
        r = await c.get(
            f"{self.api_url}/public/v1/integrations/{integration_id}",
            headers=self._headers(),
            timeout=30,
        )
        r.raise_for_status()
        return r.json()

    # ── Posts ─────────────────────────────────────────────────────────────────

    async def create_post(
        self,
        *,
        integration_ids: list[str],
        content: str,
        scheduled_at: Optional[str] = None,
        media_urls: Optional[list[str]] = None,
        settings_json: Optional[dict] = None,
        idempotency_key: Optional[str] = None,
    ) -> dict:
        """Create a post (publish immediately or schedule).

        Retries transient 5xx/429 up to 3 attempts with exponential backoff
        + jitter. Callers MUST pass a stable idempotency_key (e.g. draft_id)
        so a retry never produces duplicate posts on the platform.
        """
        self._check_config()
        body: dict = {
            "integrations": integration_ids,
            "posts": [{"content": content}],
        }
        if scheduled_at:
            body["date"] = scheduled_at
        if media_urls:
            body["posts"][0]["media"] = [{"url": url} for url in media_urls]
        if settings_json:
            body["settings"] = settings_json

        headers = self._headers()
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        c = await get_shared_client()
        last_exc: Exception | None = None
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                r = await c.post(
                    f"{self.api_url}/public/v1/posts",
                    json=body,
                    headers=headers,
                    timeout=60,
                )
                if r.status_code in _RETRYABLE_STATUS and attempt < _MAX_ATTEMPTS:
                    backoff = (2 ** (attempt - 1)) + random.uniform(0, 0.5)
                    _logger.warning(
                        "Postiz create_post attempt %d got %d; retrying in %.1fs",
                        attempt, r.status_code, backoff,
                    )
                    await asyncio.sleep(backoff)
                    continue
                r.raise_for_status()
                return r.json()
            except (httpx.TimeoutException, httpx.TransportError) as e:
                last_exc = e
                if attempt < _MAX_ATTEMPTS:
                    backoff = (2 ** (attempt - 1)) + random.uniform(0, 0.5)
                    _logger.warning(
                        "Postiz create_post transport error on attempt %d: %s; retrying in %.1fs",
                        attempt, e, backoff,
                    )
                    await asyncio.sleep(backoff)
                    continue
                raise
        # Should be unreachable, but keep typing honest
        if last_exc:
            raise last_exc
        raise RuntimeError("Postiz create_post failed without exception")

    async def delete_post(self, post_id: str) -> dict:
        """Delete a post from Postiz."""
        self._check_config()
        c = await get_shared_client()
        r = await c.delete(
            f"{self.api_url}/public/v1/posts/{post_id}",
            headers=self._headers(),
            timeout=30,
        )
        r.raise_for_status()
        return r.json()

    # ── Analytics ─────────────────────────────────────────────────────────────

    async def get_platform_analytics(
        self, integration_id: str, days: int = 7,
    ) -> dict:
        """Pull aggregate analytics for an integration.

        Tries the local Postiz CLI first (SQLite cache avoids repeat network
        calls for the same integration/day window). Falls back to direct HTTP.
        """
        binary = os.environ.get(_CLI_BINARY_ENV, _CLI_BINARY_DEFAULT)
        try:
            data = await run_cli(
                binary,
                ["analytics", "integration", integration_id, "--days", str(days)],
                env_extra={
                    "POSTIZ_API_KEY": self.api_key,
                    "POSTIZ_BASE_URL": self.api_url,
                },
            )
            if isinstance(data, dict) and data:
                return data
        except CLINotFoundError:
            _logger.debug("Postiz CLI not found — using API for platform analytics")
        except Exception as exc:
            _logger.warning("Postiz CLI analytics failed (%s) — using API", exc)

        self._check_config()
        c = await get_shared_client()
        r = await c.get(
            f"{self.api_url}/public/v1/analytics/{integration_id}",
            params={"days": days},
            headers=self._headers(),
            timeout=30,
        )
        r.raise_for_status()
        return r.json()

    async def get_post_analytics(self, post_id: str) -> dict:
        """Pull analytics for a single post.

        Tries the local Postiz CLI first (cached). Falls back to direct HTTP.
        """
        binary = os.environ.get(_CLI_BINARY_ENV, _CLI_BINARY_DEFAULT)
        try:
            data = await run_cli(
                binary,
                ["analytics", "post", post_id],
                env_extra={
                    "POSTIZ_API_KEY": self.api_key,
                    "POSTIZ_BASE_URL": self.api_url,
                },
            )
            if isinstance(data, dict) and data:
                return data
        except CLINotFoundError:
            _logger.debug("Postiz CLI not found — using API for post analytics")
        except Exception as exc:
            _logger.warning("Postiz CLI post analytics failed (%s) — using API", exc)

        self._check_config()
        c = await get_shared_client()
        r = await c.get(
            f"{self.api_url}/public/v1/analytics/post/{post_id}",
            headers=self._headers(),
            timeout=30,
        )
        r.raise_for_status()
        return r.json()

    # ── Health ────────────────────────────────────────────────────────────────

    async def health(self) -> dict:
        """Ping Postiz health endpoint (no auth required)."""
        if not self.api_url:
            raise RuntimeError("Postiz API URL not configured")
        c = await get_shared_client()
        r = await c.get(f"{self.api_url}/api/health", timeout=10)
        r.raise_for_status()
        return r.json()
