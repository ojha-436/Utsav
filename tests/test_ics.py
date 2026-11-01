from datetime import UTC, datetime

from app.models import EventInput, PlanSkeleton
from app.planning.assemble import assemble_plan
from app.planning.ics import build_calendar
from tests.factories import TODAY, event_input, skeleton_dict

NOW = datetime(2026, 11, 1, 6, 30, tzinfo=UTC)


def cal(title="Asha & Rohan's Wedding", done=frozenset()):
    p = assemble_plan(EventInput(**event_input()), PlanSkeleton(**skeleton_dict()), TODAY, done_ids=set(done))
    return build_calendar(p.event, title, p.timeline.tasks, p.vendors, NOW), p


def test_structure():
    c, p = cal()
    assert c.startswith("BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//Utsav//Event Planner//EN\r\n")
    assert c.endswith("END:VCALENDAR\r\n")
    assert c.count("BEGIN:VEVENT") == 1 + len(p.timeline.tasks) + len(p.vendors)
    for s in (
        "DTSTART;VALUE=DATE:20270214",
        "DTEND;VALUE=DATE:20270215",
        "DTSTAMP:20261101T063000Z",
        "UID:book-venue-2027-02-14@utsav",
    ):
        assert s in c


def test_done_items_excluded():
    c, _ = cal(done={"book-venue"})
    assert "UID:book-venue-2027-02-14@utsav" not in c


def test_text_escaping():
    c, _ = cal(title="Venue, decor; lights\\ x\nnew")
    assert "SUMMARY:Venue\\, decor\\; lights\\\\ x\\nnew" in c.replace("\r\n ", "")


def test_folding_counts_octets_for_devanagari():
    title = "जयपुर में शादी " * 12
    c, _ = cal(title=title)
    assert all(len(line.encode()) <= 75 for line in c.split("\r\n"))
    assert f"SUMMARY:{title}" in c.replace("\r\n ", "")


def test_lone_carriage_returns_and_control_chars_are_neutralised():
    c, _ = cal(title="Book DJ\rATTENDEE:evil\x07")
    assert "\r" not in c.replace("\r\n", "")
    assert "\x07" not in c
    assert "SUMMARY:Book DJ\\nATTENDEE:evil" in c.replace("\r\n ", "")
