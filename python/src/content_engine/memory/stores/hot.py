"""Hot memory store — session-scoped KV with 24h TTL.

Backed by the `memory_hot` table.  One row per (brand_id, session_id, key).
Values are JSON blobs; callers own serialisation of complex objects.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from ...db import get_db

logger = logging.getLogger(__name__)


async def put(
    brand_id: str,
    session_id: str,
    key: str,
    value: Any,
    ttl_hours: int = 24,
) -> None:
    """Upsert a KV entry in the hot store.

    The DB UNIQUE constraint on (brand_id, session_id, key) ensures
    ON CONFLICT DO UPDATE keeps only the freshest value.
    """
    from datetime import timedelta

    expires_at = (
        datetime.now(timezone.utc) + timedelta(hours=ttl_hours)
    ).isoformat()

    db = get_db()
    db.table("memory_hot").upsert(
        {
            "brand_id": brand_id,
            "session_id": session_id,
            "key": key,
            "value": value,
            "expires_at": expires_at,
        },
        on_conflict="brand_id,session_id,key",
    ).execute()
    logger.debug("memory_hot.put brand=%s session=%s key=%s", brand_id, session_id, key)


async def get(
    brand_id: str,
    session_id: str,
    key: str,
) -> Any | None:
    """Retrieve a value from the hot store, or None if missing / expired."""
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    resp = (
        db.table("memory_hot")
        .select("value")
        .eq("brand_id", brand_id)
        .eq("session_id", session_id)
        .eq("key", key)
        .gt("expires_at", now)
        .maybe_single()
        .execute()
    )
    if resp.data:
        return resp.data["value"]
    return None


async def delete(brand_id: str, session_id: str, key: str) -> None:
    """Hard-delete a single KV entry."""
    db = get_db()
    db.table("memory_hot").delete().eq("brand_id", brand_id).eq(
        "session_id", session_id
    ).eq("key", key).execute()


async def get_session(brand_id: str, session_id: str) -> dict[str, Any]:
    """Return all live KV pairs for a session as a plain dict."""
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    resp = (
        db.table("memory_hot")
        .select("key,value")
        .eq("brand_id", brand_id)
        .eq("session_id", session_id)
        .gt("expires_at", now)
        .execute()
    )
    return {row["key"]: row["value"] for row in (resp.data or [])}


async def clear_session(brand_id: str, session_id: str) -> int:
    """Delete all KV entries for a session; returns deleted row count."""
    db = get_db()
    resp = (
        db.table("memory_hot")
        .delete()
        .eq("brand_id", brand_id)
        .eq("session_id", session_id)
        .execute()
    )
    count = len(resp.data or [])
    logger.info("memory_hot.clear_session brand=%s session=%s deleted=%d", brand_id, session_id, count)
    return count
