"""Gmail Retriever — scans labelled newsletter emails for research items."""

from __future__ import annotations

import base64
import logging
import os
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from ..models import ResearchItemCreate, SourceType
from .base import BaseRetriever

logger = logging.getLogger(__name__)


class GmailRetriever(BaseRetriever):
    retriever_type = "gmail"  # type: ignore[assignment]  # string sentinel — orchestrator maps by key

    async def fetch(self, config: dict) -> list[ResearchItemCreate]:  # noqa: C901
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
        except ImportError:
            logger.warning("GmailRetriever: google-auth / googleapiclient not installed — skipping")
            return []

        credentials_path = os.environ.get("GMAIL_CREDENTIALS_JSON")
        token_path = os.environ.get("GMAIL_TOKEN_JSON")

        if not credentials_path or not token_path:
            logger.warning(
                "GmailRetriever: GMAIL_CREDENTIALS_JSON and/or GMAIL_TOKEN_JSON env vars not set — skipping"
            )
            return []

        label: str = config.get("gmail_label", "newsletters")
        max_items: int = int(config.get("max_items", 50))
        days_back: int = int(config.get("days_back", 7))

        # --- Authenticate ---
        try:
            creds = Credentials.from_authorized_user_file(token_path)
        except Exception as exc:
            logger.warning("GmailRetriever: failed to load token file %s: %s", token_path, exc)
            return []

        try:
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
        except Exception as exc:
            logger.warning("GmailRetriever: credential refresh failed: %s", exc)
            return []

        # --- Build service ---
        try:
            service = build("gmail", "v1", credentials=creds)
        except Exception as exc:
            logger.warning("GmailRetriever: failed to build Gmail service: %s", exc)
            return []

        # --- List messages ---
        try:
            list_resp = (
                service.users()
                .messages()
                .list(
                    userId="me",
                    labelIds=[label],
                    maxResults=max_items,
                    q=f"newer_than:{days_back}d",
                )
                .execute()
            )
        except Exception as exc:
            logger.warning("GmailRetriever: messages.list failed: %s", exc)
            return []

        messages = list_resp.get("messages", [])
        if not messages:
            return []

        items: list[ResearchItemCreate] = []

        for msg_meta in messages:
            msg_id: str = msg_meta.get("id", "")
            if not msg_id:
                continue
            try:
                msg = (
                    service.users()
                    .messages()
                    .get(userId="me", id=msg_id, format="full")
                    .execute()
                )
            except Exception as exc:
                logger.debug("GmailRetriever: failed to fetch message %s: %s", msg_id, exc)
                continue

            # --- Extract headers ---
            headers: dict[str, str] = {}
            for header in msg.get("payload", {}).get("headers", []):
                headers[header.get("name", "").lower()] = header.get("value", "")

            title = headers.get("subject", "(no subject)").strip()
            source_name = headers.get("from", "").strip()
            raw_date = headers.get("date", "")
            published_at: datetime | None = None
            if raw_date:
                try:
                    published_at = parsedate_to_datetime(raw_date)
                except Exception:
                    try:
                        published_at = datetime.now(timezone.utc)
                    except Exception:
                        pass

            # --- Extract body ---
            summary = _extract_body(msg.get("payload", {}))[:500]

            url = f"https://mail.google.com/mail/u/0/#inbox/{msg_id}"

            try:
                items.append(
                    ResearchItemCreate(
                        brand_id=self.brand_id,
                        run_id=self.run_id,
                        retriever=self.retriever_type,  # type: ignore[arg-type]
                        source_type=SourceType.ARTICLE,
                        title=title,
                        url=url,
                        source_name=source_name,
                        summary=summary,
                        published_at=published_at,
                        language="en",
                    )
                )
            except Exception as exc:
                logger.debug("GmailRetriever: failed to create ResearchItemCreate for %s: %s", msg_id, exc)
                continue

        return items


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_body(payload: dict) -> str:
    """Recursively extract plain-text body from a Gmail message payload."""
    mime_type: str = payload.get("mimeType", "")

    # Direct body data
    body_data: str = payload.get("body", {}).get("data", "")
    if body_data and mime_type in ("text/plain", "text/html"):
        try:
            decoded = base64.urlsafe_b64decode(body_data + "==").decode("utf-8", errors="replace")
            # Strip obvious HTML tags for a rough plain-text summary
            if mime_type == "text/html":
                decoded = _strip_html(decoded)
            return decoded.strip()
        except Exception:
            pass

    # Multipart: recurse into parts
    for part in payload.get("parts", []):
        result = _extract_body(part)
        if result:
            return result

    return ""


def _strip_html(text: str) -> str:
    """Very lightweight HTML tag stripper — avoids importing external deps."""
    import re
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
