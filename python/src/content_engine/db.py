"""Supabase DB client factory.

M-11: The original singleton used a bare `global` variable with no thread-safety.
      We now use threading.Lock for the service-role client and provide a
      separate factory for user-scoped clients (C-02: RLS enforcement).

Two clients are provided:
- get_db()           — uses SERVICE ROLE KEY  — for background jobs, cron
- get_user_db(jwt)   — uses user JWT          — for user-scoped operations
                                                (RLS policies apply)
"""

from __future__ import annotations

import threading

from supabase import Client, create_client

from .config import settings

# Thread-safe singleton for service-role client (used only for background jobs)
_service_client: Client | None = None
_service_lock = threading.Lock()


def get_db() -> Client:
    """Return the SERVICE ROLE Supabase client.

    C-02 reminder: This client BYPASSES all RLS policies.
    Use ONLY for background/system operations (cron, migrations).
    For user-facing operations, use get_user_db(jwt) instead.
    """
    global _service_client
    # M-11: double-checked locking for thread safety
    if _service_client is None:
        with _service_lock:
            if _service_client is None:
                _service_client = create_client(
                    settings.supabase_url,
                    settings.supabase_service_role_key,
                )
    return _service_client


def get_user_db(jwt: str) -> Client:
    """Return a Supabase client scoped to the authenticated user's JWT.

    C-02: This client respects RLS policies — the user can only see/modify
    their own brand's data, enforced at the database level.

    A new client is created per request (lightweight — no persistent connection).
    """
    client = create_client(settings.supabase_url, settings.supabase_anon_key)
    # Set the session so RLS functions (auth_user_brand_id, auth_user_role)
    # resolve correctly in PostgreSQL
    client.auth.set_session(jwt, "")
    return client
