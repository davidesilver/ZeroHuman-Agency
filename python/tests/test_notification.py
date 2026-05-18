"""Tests for NotificationService.

Tests external behavior: event routing by severity, digest composition,
and graceful Telegram degradation.  DB and HTTP are mocked.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ── Helpers ───────────────────────────────────────────────────────────────


def _make_mock_db(events=None):
    """Return a mock Supabase client that returns `events` from notification_events."""
    mock_db = MagicMock()
    chain = MagicMock()
    chain.execute.return_value.data = events or []
    mock_db.table.return_value.select.return_value = chain
    mock_db.table.return_value.insert.return_value.execute.return_value = MagicMock()
    mock_db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
    # Support chained filtering (eq, order, limit, etc.)
    for method in ("eq", "neq", "order", "limit", "range", "gte", "maybe_single"):
        getattr(chain, method).return_value = chain
    return mock_db


# ── emit_event ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_emit_event_persists_row():
    """emit_event always writes to notification_events."""
    mock_db = _make_mock_db()
    with (
        patch("content_engine.services.notification.get_db", return_value=mock_db),
        patch("content_engine.services.notification._send_telegram", new_callable=AsyncMock) as mock_tg,
        patch("content_engine.services.notification.settings") as mock_settings,
    ):
        mock_settings.telegram_bot_token = "tok"
        mock_settings.telegram_chat_id = "123"
        mock_settings.dashboard_url = "http://localhost:3000"

        from content_engine.services.notification import emit_event
        await emit_event(event_type="test_event", title="Test", severity="info")

    mock_db.table.assert_called_with("notification_events")
    mock_db.table.return_value.insert.assert_called_once()


@pytest.mark.asyncio
async def test_emit_event_sends_telegram_for_error():
    """Error severity triggers an immediate Telegram alert."""
    mock_db = _make_mock_db()
    with (
        patch("content_engine.services.notification.get_db", return_value=mock_db),
        patch("content_engine.services.notification._send_telegram", new_callable=AsyncMock) as mock_tg,
        patch("content_engine.services.notification.settings") as mock_settings,
    ):
        mock_settings.telegram_bot_token = "tok"
        mock_settings.telegram_chat_id = "123"
        mock_settings.dashboard_url = ""

        from content_engine.services.notification import emit_event
        await emit_event(event_type="pipeline_failure", title="Pipeline failed", severity="error")

    mock_tg.assert_called_once()
    call_text = mock_tg.call_args[0][0]
    assert "Pipeline failed" in call_text


@pytest.mark.asyncio
async def test_emit_event_no_telegram_for_info():
    """Info severity does NOT trigger an immediate Telegram alert."""
    mock_db = _make_mock_db()
    with (
        patch("content_engine.services.notification.get_db", return_value=mock_db),
        patch("content_engine.services.notification._send_telegram", new_callable=AsyncMock) as mock_tg,
        patch("content_engine.services.notification.settings") as mock_settings,
    ):
        mock_settings.dashboard_url = ""

        from content_engine.services.notification import emit_event
        await emit_event(event_type="memory_consolidation", title="Consolidated", severity="info")

    mock_tg.assert_not_called()


@pytest.mark.asyncio
async def test_emit_event_graceful_on_telegram_failure():
    """Telegram failure does not raise — pipeline must not be blocked."""
    mock_db = _make_mock_db()
    with (
        patch("content_engine.services.notification.get_db", return_value=mock_db),
        patch("content_engine.services.notification._send_telegram", new_callable=AsyncMock, side_effect=Exception("network error")),
        patch("content_engine.services.notification.settings") as mock_settings,
    ):
        mock_settings.telegram_bot_token = "tok"
        mock_settings.telegram_chat_id = "123"
        mock_settings.dashboard_url = ""

        from content_engine.services.notification import emit_event
        # Must not raise
        await emit_event(event_type="test", title="Test", severity="error")


@pytest.mark.asyncio
async def test_emit_event_graceful_on_db_failure():
    """DB failure does not raise — notification is best-effort."""
    mock_db = MagicMock()
    mock_db.table.return_value.insert.return_value.execute.side_effect = Exception("db down")
    with (
        patch("content_engine.services.notification.get_db", return_value=mock_db),
        patch("content_engine.services.notification._send_telegram", new_callable=AsyncMock) as mock_tg,
        patch("content_engine.services.notification.settings") as mock_settings,
    ):
        mock_settings.dashboard_url = ""

        from content_engine.services.notification import emit_event
        await emit_event(event_type="test", title="Test", severity="error")


# ── send_digest ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_send_digest_all_success():
    """Digest includes 'No issues' section when no error/warning events."""
    mock_db = _make_mock_db(events=[])
    # brand query
    brand_chain = MagicMock()
    brand_chain.execute.return_value.data = {"name": "Acme"}
    brand_chain.maybe_single.return_value = brand_chain
    mock_db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value = brand_chain

    sent_messages = []

    async def capture(text):
        sent_messages.append(text)

    with (
        patch("content_engine.services.notification.get_db", return_value=mock_db),
        patch("content_engine.services.notification._send_telegram", side_effect=capture),
        patch("content_engine.services.notification.settings") as mock_settings,
    ):
        mock_settings.telegram_bot_token = "tok"
        mock_settings.telegram_chat_id = "123"
        mock_settings.dashboard_url = ""

        from content_engine.services.notification import send_digest
        pipeline_results = {
            "research": {"items_found": 8, "sources_scanned": 3},
            "scoring": {"average_score": 7.2},
            "drafts_generated": [{"item_id": "a"}, {"item_id": "b"}],
        }
        await send_digest("brand-1", pipeline_results)

    assert len(sent_messages) == 1
    msg = sent_messages[0]
    assert "No issues" in msg or "issues" in msg.lower()
    assert "Research" in msg


@pytest.mark.asyncio
async def test_send_digest_with_errors():
    """Digest includes issues section when error events exist."""
    error_events = [
        {"event_type": "pipeline_failure", "severity": "error", "title": "Step X failed", "detail": {}, "created_at": "2024-01-01T10:00:00"},
        {"event_type": "research_zero_items", "severity": "warning", "title": "Zero items", "detail": {}, "created_at": "2024-01-01T09:00:00"},
    ]
    mock_db = _make_mock_db(events=error_events)
    brand_chain = MagicMock()
    brand_chain.execute.return_value.data = {"name": "TestBrand"}
    brand_chain.maybe_single.return_value = brand_chain
    mock_db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value = brand_chain

    sent_messages = []

    async def capture(text):
        sent_messages.append(text)

    with (
        patch("content_engine.services.notification.get_db", return_value=mock_db),
        patch("content_engine.services.notification._send_telegram", side_effect=capture),
        patch("content_engine.services.notification.settings") as mock_settings,
    ):
        mock_settings.telegram_bot_token = "tok"
        mock_settings.telegram_chat_id = "123"
        mock_settings.dashboard_url = ""

        from content_engine.services.notification import send_digest
        await send_digest("brand-1", {"research": {"items_found": 0, "sources_scanned": 1}})

    assert len(sent_messages) == 1
    msg = sent_messages[0]
    assert "Issues" in msg or "Step X failed" in msg


@pytest.mark.asyncio
async def test_send_digest_graceful_on_failure():
    """Digest failure never raises."""
    mock_db = MagicMock()
    mock_db.table.side_effect = Exception("db totally down")

    with patch("content_engine.services.notification.get_db", return_value=mock_db):
        from content_engine.services.notification import send_digest
        await send_digest("brand-x", {})  # must not raise
