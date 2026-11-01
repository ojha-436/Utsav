"""Structured JSON logs on stdout, which Cloud Logging parses into fields."""
import json
import logging
import sys

_FIELDS = ("request_id", "method", "path", "status", "latency_ms", "model", "reason")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {"severity": record.levelname, "message": record.getMessage(), "logger": record.name}
        payload |= {key: getattr(record, key) for key in _FIELDS if hasattr(record, key)}
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


class StdoutHandler(logging.StreamHandler):
    """Always writes to the current sys.stdout (so test capture sees it)."""

    @property
    def stream(self):
        return sys.stdout

    @stream.setter
    def stream(self, _value):
        pass


def configure_logging() -> None:
    root = logging.getLogger()
    if any(isinstance(h, StdoutHandler) for h in root.handlers):
        return
    handler = StdoutHandler()
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    for noisy in ("httpx", "httpx2", "google_genai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
