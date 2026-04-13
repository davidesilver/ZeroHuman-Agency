"""Alerting service — sends notifications to external channels like Telegram."""

from __future__ import annotations

import logging
import httpx
from pydantic import BaseModel

from ..config import settings

logger = logging.getLogger(__name__)

async def send_telegram_alert(message: str) -> bool:
    """Send an alert message via Telegram Bot API."""
    bot_token = settings.telegram_bot_token
    chat_id = settings.telegram_chat_id

    if not bot_token or not chat_id:
        logger.warning("Telegram alerting skipped: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not configured.")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": f"🚨 *Content Engine Alert*\n\n{message}",
        "parse_mode": "Markdown",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return True
    except Exception as e:
        logger.error("Failed to send Telegram alert: %s", e)
        return False
