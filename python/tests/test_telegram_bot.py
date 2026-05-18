"""Tests for TelegramBot command handler.

Tests external behavior: command parsing, authorization, replies,
and error handling.  DB and HTTP are mocked.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_update(text: str, chat_id: int = 111) -> dict:
    return {
        "message": {
            "chat": {"id": chat_id},
            "text": text,
        }
    }


def _make_db_with_draft(draft_id: str, brand_id: str = "brand-1", exists: bool = True):
    mock_db = MagicMock()
    chain = MagicMock()
    chain.execute.return_value.data = {"id": draft_id, "status": "draft"} if exists else None
    chain.maybe_single.return_value = chain
    for method in ("eq", "order", "limit"):
        getattr(chain, method).return_value = chain
    mock_db.table.return_value.select.return_value = chain
    mock_db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
    # Brand resolution
    brand_chain = MagicMock()
    brand_chain.execute.return_value.data = [{"id": brand_id}]
    mock_db.table.return_value.select.return_value.order.return_value.limit.return_value = brand_chain
    return mock_db


# ── Authorization ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_handle_update_rejects_unauthorized_chat():
    """Updates from unauthorized chat_id are silently ignored."""
    with patch("content_engine.services.telegram_bot.settings") as mock_settings:
        mock_settings.telegram_chat_id = "999"
        mock_settings.telegram_bot_token = "tok"

        from content_engine.services.telegram_bot import handle_update
        result = await handle_update(_make_update("/status", chat_id=111))

    assert result == {"ok": True}  # silently ignored


@pytest.mark.asyncio
async def test_handle_update_allows_configured_chat():
    """Updates from the configured chat_id are processed."""
    replies = []

    async def mock_reply(chat_id, text):
        replies.append(text)

    mock_db = MagicMock()
    chain = MagicMock()
    chain.execute.return_value.data = []
    for method in ("select", "eq", "order", "limit"):
        getattr(mock_db.table.return_value, method).return_value = chain
    chain.select.return_value = chain

    with (
        patch("content_engine.services.telegram_bot.settings") as mock_settings,
        patch("content_engine.services.telegram_bot._reply", side_effect=mock_reply),
        patch("content_engine.services.telegram_bot.get_db", return_value=mock_db),
    ):
        mock_settings.telegram_chat_id = "111"
        mock_settings.telegram_bot_token = "tok"

        from content_engine.services.telegram_bot import handle_update
        result = await handle_update(_make_update("/status", chat_id=111))

    assert result == {"ok": True}
    assert len(replies) == 1


# ── Webhook secret validation ─────────────────────────────────────────────


def test_verify_secret_passes_when_not_configured():
    with patch("content_engine.services.telegram_bot.settings") as mock_settings:
        mock_settings.telegram_webhook_secret = ""
        from content_engine.services.telegram_bot import _verify_secret
        assert _verify_secret(None) is True
        assert _verify_secret("anything") is True


def test_verify_secret_rejects_missing_header():
    with patch("content_engine.services.telegram_bot.settings") as mock_settings:
        mock_settings.telegram_webhook_secret = "mysecret"
        from content_engine.services.telegram_bot import _verify_secret
        assert _verify_secret(None) is False


def test_verify_secret_accepts_correct_value():
    with patch("content_engine.services.telegram_bot.settings") as mock_settings:
        mock_settings.telegram_webhook_secret = "mysecret"
        from content_engine.services.telegram_bot import _verify_secret
        assert _verify_secret("mysecret") is True


def test_verify_secret_rejects_wrong_value():
    with patch("content_engine.services.telegram_bot.settings") as mock_settings:
        mock_settings.telegram_webhook_secret = "mysecret"
        from content_engine.services.telegram_bot import _verify_secret
        assert _verify_secret("wrongsecret") is False


# ── Command parsing ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_approve_missing_arg_replies_usage():
    replies = []

    async def mock_reply(chat_id, text):
        replies.append(text)

    with (
        patch("content_engine.services.telegram_bot.settings") as mock_settings,
        patch("content_engine.services.telegram_bot._reply", side_effect=mock_reply),
        patch("content_engine.services.telegram_bot.get_db", return_value=_make_db_with_draft("x")),
    ):
        mock_settings.telegram_chat_id = "111"
        mock_settings.telegram_bot_token = "tok"

        from content_engine.services.telegram_bot import handle_update
        await handle_update(_make_update("/approve", chat_id=111))

    assert any("Usage" in r or "approve" in r.lower() for r in replies)


@pytest.mark.asyncio
async def test_approve_invalid_id_replies_error():
    replies = []

    async def mock_reply(chat_id, text):
        replies.append(text)

    mock_db = _make_db_with_draft("not-this-id", exists=False)

    with (
        patch("content_engine.services.telegram_bot.settings") as mock_settings,
        patch("content_engine.services.telegram_bot._reply", side_effect=mock_reply),
        patch("content_engine.services.telegram_bot.get_db", return_value=mock_db),
    ):
        mock_settings.telegram_chat_id = "111"
        mock_settings.telegram_bot_token = "tok"

        from content_engine.services.telegram_bot import handle_update
        await handle_update(_make_update("/approve bad-id-xxxx", chat_id=111))

    assert any("not found" in r.lower() or "❌" in r for r in replies)


@pytest.mark.asyncio
async def test_unknown_command_replies_help():
    replies = []

    async def mock_reply(chat_id, text):
        replies.append(text)

    mock_db = MagicMock()
    chain = MagicMock()
    chain.execute.return_value.data = [{"id": "brand-1"}]
    mock_db.table.return_value.select.return_value.order.return_value.limit.return_value = chain

    with (
        patch("content_engine.services.telegram_bot.settings") as mock_settings,
        patch("content_engine.services.telegram_bot._reply", side_effect=mock_reply),
        patch("content_engine.services.telegram_bot.get_db", return_value=mock_db),
    ):
        mock_settings.telegram_chat_id = "111"
        mock_settings.telegram_bot_token = "tok"

        from content_engine.services.telegram_bot import handle_update
        await handle_update(_make_update("/unknowncmd", chat_id=111))

    assert any("available commands" in r.lower() or "approve" in r.lower() for r in replies)


@pytest.mark.asyncio
async def test_non_command_message_ignored():
    """Plain text messages (not starting with /) are ignored."""
    replies = []

    async def mock_reply(chat_id, text):
        replies.append(text)

    with (
        patch("content_engine.services.telegram_bot.settings") as mock_settings,
        patch("content_engine.services.telegram_bot._reply", side_effect=mock_reply),
    ):
        mock_settings.telegram_chat_id = "111"

        from content_engine.services.telegram_bot import handle_update
        await handle_update(_make_update("hello bot", chat_id=111))

    assert len(replies) == 0


# ── Event log persistence ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_emit_event_stores_entity_fields():
    """entity_type and entity_id are persisted in the event row."""
    mock_db = MagicMock()
    inserted_rows = []

    def capture_insert(row):
        inserted_rows.append(row)
        m = MagicMock()
        m.execute.return_value = MagicMock()
        return m

    chain = MagicMock()
    chain.execute.return_value.data = []
    for method in ("eq", "order", "limit", "neq", "gte", "maybe_single"):
        getattr(chain, method).return_value = chain
    mock_db.table.return_value.select.return_value = chain
    mock_db.table.return_value.insert.side_effect = capture_insert

    with (
        patch("content_engine.services.notification.get_db", return_value=mock_db),
        patch("content_engine.services.notification._send_telegram", new_callable=AsyncMock),
        patch("content_engine.services.notification.settings") as mock_settings,
    ):
        mock_settings.telegram_bot_token = ""
        mock_settings.telegram_chat_id = ""
        mock_settings.dashboard_url = ""

        from content_engine.services.notification import emit_event
        await emit_event(
            event_type="campaign_sent",
            title="Newsletter sent",
            severity="success",
            brand_id="brand-x",
            entity_type="newsletter",
            entity_id="nl-123",
        )

    assert len(inserted_rows) == 1
    row = inserted_rows[0]
    assert row.get("entity_type") == "newsletter"
    assert row.get("entity_id") == "nl-123"
    assert row.get("brand_id") == "brand-x"
