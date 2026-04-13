"""Structured JSON logging configuration for Content Engine.

L-03: Replaces basicConfig with JSON-formatted logs for SIEM compatibility.
Each log line is a single JSON object with consistent fields, making it
trivial to parse with tools like jq, Datadog, Loki, or Elasticsearch.

Usage:
    from ..utils.logging_config import setup_logging
    setup_logging()  # Call once at startup in main.py
"""

from __future__ import annotations

import json
import logging
import os
import sys
import traceback
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Format log records as newline-delimited JSON (NDJSON).

    Fields emitted per record:
        timestamp   — ISO 8601 UTC
        level       — DEBUG / INFO / WARNING / ERROR / CRITICAL
        logger      — logger name (e.g. "content_engine.api")
        message     — the formatted log message
        module      — source module name
        line        — source line number
        exc_info    — exception traceback (only on ERROR+)
        extra.*     — any extra fields passed to the logger
    """

    SERVICE_NAME = os.environ.get("SERVICE_NAME", "content-engine")
    ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")

    # Fields added by logging.makeLogRecord we want to strip from extras
    _BUILTIN_ATTRS = frozenset({
        "args", "asctime", "created", "exc_info", "exc_text", "filename",
        "funcName", "levelname", "levelno", "lineno", "message", "module",
        "msecs", "msg", "name", "pathname", "process", "processName",
        "relativeCreated", "stack_info", "taskName", "thread", "threadName",
    })

    def format(self, record: logging.LogRecord) -> str:
        record.message = record.getMessage()

        payload: dict = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.message,
            "service": self.SERVICE_NAME,
            "env": self.ENVIRONMENT,
            "module": record.module,
            "line": record.lineno,
        }

        # Add exception info for errors
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        elif record.exc_text:
            payload["exc_info"] = record.exc_text

        # Add any extra fields passed via logger.info("msg", extra={"key": val})
        for key, val in record.__dict__.items():
            if key not in self._BUILTIN_ATTRS and not key.startswith("_"):
                payload[f"extra.{key}"] = val

        return json.dumps(payload, default=str, ensure_ascii=False)


def setup_logging(level: str | None = None) -> None:
    """Configure root logger with JSON formatter.

    Call once at application startup (main.py).
    """
    log_level = level or os.environ.get("LOG_LEVEL", "INFO").upper()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    root = logging.getLogger()
    root.setLevel(log_level)

    # Remove any existing handlers set by basicConfig calls
    root.handlers.clear()
    root.addHandler(handler)

    # Suppress noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("supabase").setLevel(logging.WARNING)
    logging.getLogger("postgrest").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
