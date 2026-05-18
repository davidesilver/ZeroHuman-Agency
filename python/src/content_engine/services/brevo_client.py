"""Brevo (formerly Sendinblue) API client.

Handles per-brand authentication, contacts, and lists.
The Brevo API key is stored encrypted in brand_integrations (provider='brevo', key_name='api_key').
Campaigns are handled in a separate module (brevo_campaigns.py) in Phase 5.

Rate limits (Brevo free / Starter):
  - Contacts API: 10 req/s per account
  We use exponential backoff with up to 5 retries.

Usage:
    from content_engine.services.brevo_client import BrevoClient
    client = BrevoClient(brand_id="...")
    contacts = client.list_contacts()
"""

from __future__ import annotations

import csv
import io
import logging
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

import httpx

from .brand_secrets import get_brand_secret
from .feature_flags import EMAIL_MARKETING_ENABLED, get_feature_flag

logger = logging.getLogger(__name__)

BREVO_API_BASE = "https://api.brevo.com/v3"
_MAX_RETRIES = 5
_RETRY_BASE_DELAY = 0.5  # seconds, doubles on each retry


@dataclass
class BrevoContact:
    email: str
    first_name: str | None = None
    last_name: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    list_ids: list[int] = field(default_factory=list)
    brevo_id: int | None = None
    is_blocklisted: bool = False


@dataclass
class BrevoList:
    id: int
    name: str
    total_subscribers: int
    total_active_contacts: int


class BrevoAuthError(Exception):
    """Raised when the Brevo API key is missing or rejected."""


class BrevoClient:
    """Per-brand Brevo API client."""

    def __init__(self, brand_id: str):
        self._brand_id = brand_id
        self._api_key: str | None = None

    def _get_key(self) -> str:
        if not self._api_key:
            key = get_brand_secret(self._brand_id, "brevo", "api_key")
            if not key:
                raise BrevoAuthError(
                    f"No Brevo API key for brand {self._brand_id}. "
                    "Set it via Settings → Brand → Audience."
                )
            self._api_key = key
        return self._api_key

    def _headers(self) -> dict[str, str]:
        return {
            "accept": "application/json",
            "content-type": "application/json",
            "api-key": self._get_key(),
        }

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: dict | None = None,
    ) -> Any:
        url = f"{BREVO_API_BASE}{path}"
        for attempt in range(_MAX_RETRIES):
            try:
                with httpx.Client(timeout=30.0) as client:
                    resp = client.request(
                        method, url, headers=self._headers(), json=json, params=params
                    )
                if resp.status_code == 401:
                    raise BrevoAuthError(f"Brevo 401: invalid API key for brand {self._brand_id}")
                if resp.status_code == 429:
                    delay = _RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning("Brevo rate limit hit, retrying in %.1fs", delay)
                    time.sleep(delay)
                    continue
                resp.raise_for_status()
                return resp.json() if resp.content else {}
            except BrevoAuthError:
                raise
            except httpx.HTTPStatusError as exc:
                if attempt == _MAX_RETRIES - 1:
                    raise
                delay = _RETRY_BASE_DELAY * (2 ** attempt)
                logger.warning("Brevo HTTP error %s, retry %d in %.1fs", exc.response.status_code, attempt + 1, delay)
                time.sleep(delay)
            except httpx.RequestError as exc:
                if attempt == _MAX_RETRIES - 1:
                    raise
                delay = _RETRY_BASE_DELAY * (2 ** attempt)
                logger.warning("Brevo network error %s, retry %d in %.1fs", exc, attempt + 1, delay)
                time.sleep(delay)
        raise RuntimeError(f"Brevo {method} {path} failed after {_MAX_RETRIES} retries")

    # ── Contacts ────────────────────────────────────────────────────────────

    def list_contacts(self, limit: int = 50, offset: int = 0) -> list[BrevoContact]:
        """List contacts from Brevo (paginated)."""
        data = self._request("GET", "/contacts", params={"limit": limit, "offset": offset})
        return [self._parse_contact(c) for c in data.get("contacts", [])]

    def get_contact(self, email: str) -> BrevoContact | None:
        """Fetch a single contact by email. Returns None if not found."""
        try:
            data = self._request("GET", f"/contacts/{email}")
            return self._parse_contact(data)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            raise

    def create_or_update_contact(self, contact: BrevoContact) -> BrevoContact:
        """Create a contact or update if the email already exists."""
        payload: dict[str, Any] = {"email": contact.email}
        attrs: dict[str, Any] = {**contact.attributes}
        if contact.first_name:
            attrs["FIRSTNAME"] = contact.first_name
        if contact.last_name:
            attrs["LASTNAME"] = contact.last_name
        if attrs:
            payload["attributes"] = attrs
        if contact.list_ids:
            payload["listIds"] = contact.list_ids
        try:
            data = self._request("POST", "/contacts", json=payload)
            contact.brevo_id = data.get("id")
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 400:
                # Contact exists — update it
                update_payload: dict[str, Any] = {}
                if attrs:
                    update_payload["attributes"] = attrs
                if contact.list_ids:
                    update_payload["listIds"] = contact.list_ids
                self._request("PUT", f"/contacts/{contact.email}", json=update_payload)
                existing = self.get_contact(contact.email)
                if existing:
                    contact.brevo_id = existing.brevo_id
            else:
                raise
        return contact

    def import_contacts_csv(
        self,
        csv_text: str,
        list_id: int | None = None,
    ) -> Iterator[BrevoContact]:
        """Parse a CSV string and upsert each row. Yields synced contacts.

        Expected columns (case-insensitive): email, first_name, last_name.
        Any extra columns are stored in attributes.
        """
        reader = csv.DictReader(io.StringIO(csv_text))
        if reader.fieldnames is None:
            raise ValueError("CSV has no header row")

        # Normalise column names to lowercase
        lower_fields = {f.lower(): f for f in reader.fieldnames if f}

        def _field(row: dict, *candidates: str) -> str | None:
            for c in candidates:
                if c in lower_fields:
                    val = row.get(lower_fields[c], "").strip()
                    if val:
                        return val
            return None

        for row in reader:
            email = _field(row, "email", "e-mail", "mail")
            if not email:
                continue
            contact = BrevoContact(
                email=email,
                first_name=_field(row, "first_name", "firstname", "nome"),
                last_name=_field(row, "last_name", "lastname", "cognome"),
                list_ids=[list_id] if list_id else [],
            )
            # Extra columns → attributes
            skip = {"email", "e-mail", "mail", "first_name", "firstname", "nome", "last_name", "lastname", "cognome"}
            for key, orig_key in lower_fields.items():
                if key not in skip:
                    val = row.get(orig_key, "").strip()
                    if val:
                        contact.attributes[key.upper()] = val
            yield self.create_or_update_contact(contact)

    # ── Lists ────────────────────────────────────────────────────────────────

    def list_lists(self) -> list[BrevoList]:
        """Fetch all lists for this account."""
        data = self._request("GET", "/contacts/lists", params={"limit": 50})
        return [
            BrevoList(
                id=lst["id"],
                name=lst["name"],
                total_subscribers=lst.get("totalSubscribers", 0),
                total_active_contacts=lst.get("uniqueSubscribers", 0),
            )
            for lst in data.get("lists", [])
        ]

    def create_list(self, name: str, folder_id: int | None = None) -> BrevoList:
        """Create a new contact list."""
        payload: dict[str, Any] = {"name": name}
        if folder_id:
            payload["folderId"] = folder_id
        data = self._request("POST", "/contacts/lists", json=payload)
        return BrevoList(id=data["id"], name=name, total_subscribers=0, total_active_contacts=0)

    # ── Private helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _parse_contact(data: dict) -> BrevoContact:
        attrs = data.get("attributes", {})
        return BrevoContact(
            brevo_id=data.get("id"),
            email=data.get("email", ""),
            first_name=attrs.get("FIRSTNAME"),
            last_name=attrs.get("LASTNAME"),
            attributes={k: v for k, v in attrs.items() if k not in ("FIRSTNAME", "LASTNAME")},
            list_ids=data.get("listIds", []),
            is_blocklisted=data.get("emailBlacklisted", False),
        )


def get_brevo_client(brand_id: str) -> BrevoClient:
    """Factory that checks the feature flag before returning a client."""
    if not get_feature_flag(brand_id, EMAIL_MARKETING_ENABLED):
        raise RuntimeError(
            f"email_marketing_enabled is OFF for brand {brand_id}. "
            "Enable it in Settings → Feature Flags."
        )
    return BrevoClient(brand_id)
