"""Structured JSON logs to stdout (PROJECT_SPEC §7.5). No PII — prompts are never logged."""

from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
stage_ctx: ContextVar[str | None] = ContextVar("stage", default=None)
provider_ctx: ContextVar[str | None] = ContextVar("provider", default=None)

_RESERVED = {
    "name",
    "msg",
    "args",
    "created",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "exc_info",
    "exc_text",
    "thread",
    "threadName",
    "taskName",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None) or request_id_ctx.get(),
            "stage": getattr(record, "stage", None) or stage_ctx.get(),
            "provider": getattr(record, "provider", None) or provider_ctx.get(),
        }
        extra_keys = (
            "duration_ms",
            "cache_hit",
            "budget_remaining",
            "path",
            "method",
            "status_code",
        )
        for key in extra_keys:
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        for key, value in record.__dict__.items():
            if key not in _RESERVED and key not in payload and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    resolved = getattr(logging, level.upper(), logging.INFO)
    root.setLevel(resolved)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
