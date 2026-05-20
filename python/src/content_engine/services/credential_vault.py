"""Per-brand credential vault.

Credentials (API keys, tokens) for external services are stored encrypted in
brand_integrations (one row per key). Encryption uses Fernet symmetric keys —
plaintext never leaves this module.

Usage:
    from .credential_vault import get_credentials, set_credentials

    creds = await get_credentials(brand_id, "postiz")
    # creds = {"api_key": "pos_...", "base_url": "http://..."}  or None

    await set_credentials(brand_id, "serper", {"api_key": "..."})
    await delete_credentials(brand_id, "serper")

Credential resolution order (highest to lowest priority):
    1. Brand-specific vault entry from DB
    2. Global env var / settings (existing behaviour, unchanged)
"""

from __future__ import annotations

import json
import logging
import os
from functools import lru_cache

from ..db import get_db

logger = logging.getLogger(__name__)

_KEY_ENV = "BRAND_SECRETS_ENCRYPTION_KEY"


@lru_cache(maxsize=1)
def _get_fernet():
    """Lazy-load Fernet; raises ImportError if cryptography not installed."""
    from cryptography.fernet import Fernet
    key = os.environ.get(_KEY_ENV, "").strip()
    if not key:
        raise RuntimeError(
            f"{_KEY_ENV} env var is not set — credential vault is disabled. "
            "Generate a key with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    return Fernet(key.encode())


def _encrypt(data: str | dict) -> str:
    f = _get_fernet()
    return f.encrypt(json.dumps(data).encode()).decode()


def _decrypt(ciphertext: str) -> str | dict:
    f = _get_fernet()
    return json.loads(f.decrypt(ciphertext.encode()).decode())


def _vault_available() -> bool:
    try:
        _get_fernet()
        return True
    except Exception:
        return False


async def get_credentials(brand_id: str, service_name: str) -> dict | None:
    """Return decrypted credentials for a brand/service pair, or None.

    Returns None (silently) if the vault is not configured or the entry
    doesn't exist — callers fall back to global env vars.
    """
    if not _vault_available():
        return None
    try:
        db = get_db()
        rows = (
            db.table("brand_integrations")
            .select("key_name, encrypted_value")
            .eq("brand_id", brand_id)
            .eq("provider", service_name)
            .execute()
        )
        if not rows.data:
            return None
        return {r["key_name"]: _decrypt(r["encrypted_value"]) for r in rows.data}
    except Exception as exc:
        logger.warning("credential_vault.get_credentials failed for brand=%s service=%s: %s", brand_id, service_name, exc)
        return None


async def set_credentials(brand_id: str, service_name: str, credentials: dict) -> None:
    """Encrypt and upsert credentials for a brand/service pair."""
    if not _vault_available():
        raise RuntimeError(f"{_KEY_ENV} is not set — cannot store credentials")
    db = get_db()
    for key_name, value in credentials.items():
        db.table("brand_integrations").upsert(
            {
                "brand_id": brand_id,
                "provider": service_name,
                "key_name": key_name,
                "encrypted_value": _encrypt(value),
            },
            on_conflict="brand_id,provider,key_name",
        ).execute()
    logger.info("credential_vault: upserted credentials for brand=%s service=%s", brand_id, service_name)


async def delete_credentials(brand_id: str, service_name: str) -> None:
    """Delete credentials for a brand/service pair."""
    db = get_db()
    db.table("brand_integrations").delete().eq("brand_id", brand_id).eq("provider", service_name).execute()
    logger.info("credential_vault: deleted credentials for brand=%s service=%s", brand_id, service_name)


async def list_configured_services(brand_id: str) -> list[str]:
    """Return list of service names that have credentials configured for this brand."""
    try:
        db = get_db()
        rows = (
            db.table("brand_integrations")
            .select("provider")
            .eq("brand_id", brand_id)
            .execute()
        )
        return list({r["provider"] for r in (rows.data or [])})
    except Exception as exc:
        logger.warning("credential_vault.list_configured_services failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Service-to-env-var mapping
# Defines which dict keys map to which env var names when injecting into CLI.
# ---------------------------------------------------------------------------

_SERVICE_ENV_MAP: dict[str, dict[str, str]] = {
    "postiz":   {"api_key": "POSTIZ_API_KEY", "base_url": "POSTIZ_BASE_URL"},
    "serper":   {"api_key": "SERPER_API_KEY"},
    "tavily":   {"api_key": "TAVILY_API_KEY"},
    "youtube":  {"api_key": "YOUTUBE_API_KEY"},
    "firecrawl": {"api_key": "FIRECRAWL_API_KEY"},
    "x":        {"bearer_token": "X_BEARER_TOKEN"},
    "resend":   {"api_key": "RESEND_API_KEY"},
    "openrouter": {"api_key": "OPENROUTER_API_KEY"},
}


async def get_env_for_brand(brand_id: str, service_name: str) -> dict[str, str]:
    """Return env var dict for a brand/service pair.

    Merges vault credentials (priority) over global env vars (fallback).
    Safe to call even when vault is not configured — returns empty dict.
    """
    creds = await get_credentials(brand_id, service_name)
    if not creds:
        return {}

    mapping = _SERVICE_ENV_MAP.get(service_name, {})
    env: dict[str, str] = {}
    for cred_key, env_var in mapping.items():
        value = creds.get(cred_key, "")
        if value:
            env[env_var] = value

    # Pass-through any keys not in the mapping (custom services)
    for k, v in creds.items():
        if k not in mapping and isinstance(v, str) and v:
            env[k.upper()] = v

    return env
