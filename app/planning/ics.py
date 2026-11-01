"""RFC 5545 calendar export: the event day plus every open task and vendor booking."""

import re
from datetime import UTC, date, datetime, timedelta

from app.models import EventInput, ScheduledTask, ScheduledVendor

_MAX_OCTETS = 75
_NEWLINES = re.compile(r"\r\n|\r|\n")
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")  # keeps \t and \n


def _escape(text: str) -> str:
    """RFC 5545 TEXT escaping. Every line-break form becomes \\n; other control characters are dropped."""
    text = _CONTROL.sub("", _NEWLINES.sub("\n", text))
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _fold(line: str) -> str:
    """Split lines longer than 75 UTF-8 octets without breaking a character."""
    parts, current = [], ""
    for ch in line:
        if len((current + ch).encode()) > _MAX_OCTETS:
            parts.append(current)
            current = " " + ch
        else:
            current += ch
    parts.append(current)
    return "\r\n".join(parts)


def _vevent(uid: str, summary: str, day: date, stamp: str) -> list[str]:
    return [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{stamp}",
        f"DTSTART;VALUE=DATE:{day:%Y%m%d}",
        f"DTEND;VALUE=DATE:{day + timedelta(days=1):%Y%m%d}",
        f"SUMMARY:{_escape(summary)}",
        "END:VEVENT",
    ]


def build_calendar(
    event: EventInput, title: str, tasks: list[ScheduledTask], vendors: list[ScheduledVendor], now: datetime
) -> str:
    stamp = now.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
    suffix = f"{event.event_date.isoformat()}@utsav"
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Utsav//Event Planner//EN", "CALSCALE:GREGORIAN"]
    lines += _vevent(f"event-{suffix}", title, event.event_date, stamp)
    for task in tasks:
        if task.status != "done":
            lines += _vevent(f"{task.id}-{suffix}", task.title, task.due, stamp)
    for vendor in vendors:
        if vendor.status != "done":
            lines += _vevent(f"{vendor.id}-{suffix}", f"Book {vendor.role}", vendor.book_by, stamp)
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(line) for line in lines) + "\r\n"
