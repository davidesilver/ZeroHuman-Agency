"""Per-brand encrypted API secrets helper.

Reads/writes from `brand_integrations` (migration 032).
Encryption: Fernet (AES-128-CBC + HMAC-SHA256).
Key source: BRAND_SECRETS_ENCRYPTION_KEY env var (32-byte URL-safe base64).

Generate a key once:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

Usage:
    from content_engine.services.brand_secrets import get_brand_secret, set_brand_secret

    api_key = get_brand_secret(brand_id, "brevo", "api_key")
"""

from __future__ import annotations

import logging
import threading
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from ..config import settings
from ..db import get_db

logger = logging.getLogger(__name__)

# ── in-memory cache ────────────────────────────────────────────────────────
# Key: (brand_id, provider, key_name) → plaintext secret
_cache: dict[tuple[str, str, str], str] = {}
_cache_lock = threading.Lock()


def _fernet() -> Fernet:
    key = settings.brand_secrets_encryption_key
    if not key:
        raise RuntimeError(
            "BRAND_SECRETS_ENCRYPTION_KEY is not set. "
            "Generate with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    return Fernet(key.encode())


def get_brand_secret(
    brand_id: str,
    provider: str,
    key_name: str,
) -> Optional[str]:
    """Retrieve and decrypt a brand secret. Returns None if not found.

    Results are cached in-memory for the process lifetime.
    Call invalidate_brand_cache(brand_id) after updating a secret.
    """
    cache_key = (brand_id, provider, key_name)

    with _cache_lock:
        if cache_key in _cache:
            return _cache[cache_key]

    try:
        result = (
            get_db()
            .from_("brand_integrations")
            .select("encrypted_value")
            .eq("brand_id", brand_id)
            .eq("provider", provider)
            .eq("key_name", key_name)
            .maybe_single()
            .execute()
        )
        if not result.data:
            return None

        plaintext = _fernet().decrypt(result.data["encrypted_value"].encode()).decode()
        with _cache_lock:
            _cache[cache_key] = plaintext
        return plaintext

    except InvalidToken:
        logger.error(
            "brand_secrets: decryption failed for brand=%s provider=%s key=%s — wrong key?",
            brand_id, provider, key_name,
        )
        return None
    except Exception:
        logger.exception("brand_secrets: read error for brand=%s provider=%s key=%s", brand_id, provider, key_name)
        return None


def set_brand_secret(brand_id: str, provider: str, key_name: str, value: str) -> None:
    """Encrypt and upsert a brand secret. Invalidates the in-memory cache entry."""
    encrypted = _fernet().encrypt(value.encode()).decode()
    get_db().from_("brand_integrations").upsert(
        {
            "brand_id": brand_id,
            "provider": provider,
            "key_name": key_name,
            "encrypted_value": encrypted,
        },
        on_conflict="brand_id,provider,key_name",
    ).execute()
    invalidate_brand_cache(brand_id)


def delete_brand_secret(brand_id: str, provider: str, key_name: str) -> None:
    """Delete a brand secret and remove it from cache."""
    get_db().from_("brand_integrations").delete().eq("brand_id", brand_id).eq("provider", provider).eq("key_name", key_name).execute()
    with _cache_lock:
        _cache.pop((brand_id, provider, key_name), None)


def invalidate_brand_cache(brand_id: str) -> None:
    """Flush all cached secrets for a brand (call after any update)."""
    with _cache_lock:
        stale = [k for k in _cache if k[0] == brand_id]
        for k in stale:
            del _cache[k]
