"""Server-side accessors for brand_assets.

Read-only from Python side — writes happen through Next.js so ownership/RLS
checks are always enforced at the user-session layer. Python only needs to
resolve brand assets when generating content or images.
"""
from __future__ import annotations

from typing import TypedDict

from ..db import get_db


class BrandAsset(TypedDict):
    id: str
    kind: str
    label: str | None
    storage_path: str
    mime_type: str
    palette_hex: list[str] | None
    metadata: dict


def _signed_url(storage_path: str, ttl_seconds: int = 600) -> str:
    db = get_db()
    res = db.storage.from_("brand-assets").create_signed_url(storage_path, ttl_seconds)
    return res.get("signedURL") or res.get("signed_url") or ""


def get_brand_asset(brand_id: str, kind: str) -> BrandAsset | None:
    """Return the most recent asset of `kind` for `brand_id`, or None."""
    db = get_db()
    rows = (
        db.table("brand_assets")
        .select("id, kind, label, storage_path, mime_type, palette_hex, metadata")
        .eq("brand_id", brand_id).eq("kind", kind)
        .order("created_at", desc=True).limit(1).execute().data
    )
    return rows[0] if rows else None


def get_brand_logo_url(brand_id: str) -> str | None:
    a = get_brand_asset(brand_id, "logo_primary")
    return _signed_url(a["storage_path"]) if a else None


def get_brand_palette(brand_id: str) -> list[str]:
    """Return hex colors for the brand. Falls back to [] if no palette uploaded."""
    a = get_brand_asset(brand_id, "palette")
    return list(a.get("palette_hex") or []) if a else []


def list_example_content(brand_id: str, kind: str, limit: int = 5) -> list[BrandAsset]:
    """Fetch up to `limit` example assets (newsletter/post/carousel) ordered newest-first."""
    assert kind in ("example_newsletter", "example_post", "example_carousel")
    db = get_db()
    rows = (
        db.table("brand_assets")
        .select("id, kind, label, storage_path, mime_type, palette_hex, metadata")
        .eq("brand_id", brand_id).eq("kind", kind)
        .order("created_at", desc=True).limit(limit).execute().data
    )
    return rows or []
