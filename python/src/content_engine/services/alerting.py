"""Legacy alerting shim — delegates to notification service.

All new code should import from notification.py directly.
This module exists only for backward compatibility with existing imports.
"""

from .notification import send_telegram_alert  # noqa: F401
