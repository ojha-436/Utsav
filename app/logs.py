"""Structured JSON logs on stdout, which Cloud Logging parses into fields."""

import json
import logging
import sys
from typing import TextIO

_FIELDS = ("request_id", "method", "path", "status", "latency_ms", "model", "reason")


class JsonFormatter(logging.Formatter):
    """Formats log records as one JSON object per line for Cloud Logging."""

    def format(self, record: logging.LogRecord) -> str:
        """The record as JSON, including the whitelisted request fields."""
        payload = {"severity": record.levelname, "message": record.getMessage(), "logger": record.name}
        payload |= {key: getattr(record, key) for key in _FIELDS if hasattr(record, key)}
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


class StdoutHandler(logging.StreamHandler):
    """Always writes to the current sys.stdout (so test capture sees it)."""

    @property
    def stream(self) -> TextIO:
        """The current sys.stdout, looked up on every write."""
        return sys.stdout

    @stream.setter
    def stream(self, _value: TextIO) -> None:
        pass


def configure_logging() -> None:
    """Installs the JSON stdout handler once and quiets noisy HTTP-client loggers."""
    root = logging.getLogger()
    if any(isinstance(h, StdoutHandler) for h in root.handlers):
        return
    handler = StdoutHandler()
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    for noisy in ("httpx", "httpx2", "google_genai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
