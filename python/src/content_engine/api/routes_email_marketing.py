"""Email marketing API routes (Brevo foundation — Phase 3).

Endpoints:
  POST /email-marketing/contacts  — sync contacts from JSON or CSV
  GET  /email-marketing/lists     — list all Brevo lists
  POST /email-marketing/lists     — create a Brevo list

Authentication: JWTAuthMiddleware sets request.state.brand_id.
Feature gate: email_marketing_enabled must be ON for the brand.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..db import get_db
from ..services.brevo_client import BrevoAuthError, BrevoClient, BrevoContact
from ..services.feature_flags import EMAIL_MARKETING_ENABLED, get_feature_flag

_logger = logging.getLogger("content_engine.email_marketing")

router = APIRouter(prefix="/email-marketing", tags=["email-marketing"])


def _brand_id(request: Request) -> str:
    brand_id = getattr(request.state, "brand_id", None)
    if not brand_id:
        raise HTTPException(401, "Not authenticated")
    return brand_id


def _require_feature(brand_id: str) -> None:
    if not get_feature_flag(brand_id, EMAIL_MARKETING_ENABLED):
        raise HTTPException(403, "email_marketing_enabled is OFF for this brand")


# ── Contact models ────────────────────────────────────────────────────────

class ContactInput(BaseModel):
    email: str
    first_name: str | None = None
    last_name: str | None = None
    attributes: dict[str, Any] = {}


class ContactSyncRequest(BaseModel):
    contacts: list[ContactInput] | None = None
    csv: str | None = None
    list_id: int | None = None


class SyncResult(BaseModel):
    synced: int
    errors: list[dict[str, str]] = []


# ── List models ───────────────────────────────────────────────────────────

class ListCreateRequest(BaseModel):
    name: str
    folder_id: int | None = None


# ── Routes ───────────────────────────────────────────────────────────────

@router.post("/contacts", response_model=SyncResult)
async def sync_contacts(body: ContactSyncRequest, request: Request):
    """Sync contacts into Brevo and mirror locally."""
    brand_id = _brand_id(request)
    _require_feature(brand_id)

    try:
        client = BrevoClient(brand_id)
    except BrevoAuthError as exc:
        raise HTTPException(422, str(exc))

    synced = 0
    errors: list[dict[str, str]] = []

    if body.csv:
        for contact in client.import_contacts_csv(body.csv, list_id=body.list_id):
            _mirror_contact(brand_id, contact)
            synced += 1
    elif body.contacts:
        for c in body.contacts:
            try:
                contact = BrevoContact(
                    email=c.email,
                    first_name=c.first_name,
                    last_name=c.last_name,
                    attributes=c.attributes,
                    list_ids=[body.list_id] if body.list_id else [],
                )
                result = client.create_or_update_contact(contact)
                _mirror_contact(brand_id, result)
                synced += 1
            except Exception as exc:
                _logger.warning("Failed to sync contact %s: %s", c.email, exc)
                errors.append({"email": c.email, "reason": str(exc)})
    else:
        raise HTTPException(400, "Provide either 'contacts' list or 'csv' string")

    return SyncResult(synced=synced, errors=errors)


@router.get("/lists")
async def get_lists(request: Request):
    """Return all Brevo lists for the active brand."""
    brand_id = _brand_id(request)
    _require_feature(brand_id)

    try:
        client = BrevoClient(brand_id)
        lists = client.list_lists()
    except BrevoAuthError as exc:
        raise HTTPException(422, str(exc))

    return [
        {"id": lst.id, "name": lst.name, "total_subscribers": lst.total_subscribers}
        for lst in lists
    ]


@router.post("/lists", status_code=201)
async def create_list(body: ListCreateRequest, request: Request):
    """Create a new contact list in Brevo."""
    brand_id = _brand_id(request)
    _require_feature(brand_id)

    if not body.name.strip():
        raise HTTPException(400, "name is required")

    try:
        client = BrevoClient(brand_id)
        lst = client.create_list(body.name.strip(), folder_id=body.folder_id)
    except BrevoAuthError as exc:
        raise HTTPException(422, str(exc))

    return {"id": lst.id, "name": lst.name}


# ── Mirror helper ─────────────────────────────────────────────────────────

def _mirror_contact(brand_id: str, contact: BrevoContact) -> None:
    """Upsert a synced contact into the local brevo_contacts mirror."""
    try:
        get_db().from_("brevo_contacts").upsert(
            {
                "brand_id": brand_id,
                "email": contact.email,
                "brevo_id": contact.brevo_id,
                "first_name": contact.first_name,
                "last_name": contact.last_name,
                "attributes": contact.attributes,
                "list_ids": contact.list_ids,
                "is_blocklisted": contact.is_blocklisted,
                "synced_at": "now()",
            },
            on_conflict="brand_id,email",
        ).execute()
    except Exception:
        _logger.exception("Failed to mirror contact %s for brand %s", contact.email, brand_id)
