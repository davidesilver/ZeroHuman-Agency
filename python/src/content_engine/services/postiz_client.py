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
"""
from __future__ import annotations
from typing import Optional
import asyncio
import logging
import random

import httpx

from ..config import settings

_logger = logging.getLogger("content_engine.postiz_client")

_RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}
_MAX_ATTEMPTS = 3


class PostizClient:
    """HTTP client for Postiz Public API.

    Args:
        api_url: Postiz base URL (e.g. http://localhost:3001 or https://api.postiz.com).
                 Defaults to settings.postiz_api_url.
        api_key: Postiz API key from Settings → API. Defaults to settings.postiz_api_key.
    """

    def __init__(self, api_url: str | None = None, api_key: str | None = None):
        self.api_url = (api_url or settings.postiz_api_url or "").rstrip("/")
        self.api_key = api_key or settings.postiz_api_key or ""

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
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.get(
                f"{self.api_url}/public/v1/integrations",
                headers=self._headers(),
            )
            r.raise_for_status()
            return r.json()

    async def get_integration(self, integration_id: str) -> dict:
        """Get details for a single integration."""
        self._check_config()
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.get(
                f"{self.api_url}/public/v1/integrations/{integration_id}",
                headers=self._headers(),
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

        last_exc: Exception | None = None
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                async with httpx.AsyncClient(timeout=60) as c:
                    r = await c.post(
                        f"{self.api_url}/public/v1/posts",
                        json=body,
                        headers=headers,
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
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.delete(
                f"{self.api_url}/public/v1/posts/{post_id}",
                headers=self._headers(),
            )
            r.raise_for_status()
            return r.json()

    # ── Analytics ─────────────────────────────────────────────────────────────

    async def get_platform_analytics(
        self, integration_id: str, days: int = 7,
    ) -> dict:
        """Pull aggregate analytics for an integration."""
        self._check_config()
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.get(
                f"{self.api_url}/public/v1/analytics/{integration_id}",
                params={"days": days},
                headers=self._headers(),
            )
            r.raise_for_status()
            return r.json()

    async def get_post_analytics(self, post_id: str) -> dict:
        """Pull analytics for a single post."""
        self._check_config()
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.get(
                f"{self.api_url}/public/v1/analytics/post/{post_id}",
                headers=self._headers(),
            )
            r.raise_for_status()
            return r.json()

    # ── Health ────────────────────────────────────────────────────────────────

    async def health(self) -> dict:
        """Ping Postiz health endpoint (no auth required)."""
        if not self.api_url:
            raise RuntimeError("Postiz API URL not configured")
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"{self.api_url}/api/health")
            r.raise_for_status()
            return r.json()
