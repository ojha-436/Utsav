from datetime import UTC, datetime

import pytest

from app.errors import NotFound
from app.models import EventInput, PlanSkeleton
from app.store import InMemoryEventStore
from tests.factories import event_input, skeleton_dict


def new(s):
    return s.create("u1", EventInput(**event_input()), PlanSkeleton(**skeleton_dict()), "ai")


def test_scoped_crud():
    s = InMemoryEventStore()
    r = new(s)
    assert s.get("u1", r.id).version == 1 and s.list("u2") == []
    with pytest.raises(NotFound):
        s.get("u2", r.id)
    s.delete("u1", r.id)
    with pytest.raises(NotFound):
        s.delete("u1", r.id)


def test_save_persists_and_returns_copies():
    t = [datetime(2026, 11, 1, tzinfo=UTC)]
    s = InMemoryEventStore(clock=lambda: t[0])
    r = new(s)
    r.progress["book-venue"] = t[0]
    s.get("u1", r.id).progress.clear()
    assert s.get("u1", r.id).progress == {}
    t[0] = datetime(2026, 11, 2, tzinfo=UTC)
    s.save("u1", r)
    assert "book-venue" in s.get("u1", r.id).progress and s.get("u1", r.id).updated_at == t[0]


def test_save_unknown_event_raises():
    s = InMemoryEventStore()
    r = new(s)
    with pytest.raises(NotFound):
        s.save("u2", r)


def test_list_newest_first():
    t = [datetime(2026, 11, 1, tzinfo=UTC)]
    s = InMemoryEventStore(clock=lambda: t[0])
    a = new(s)
    t[0] = datetime(2026, 11, 2, tzinfo=UTC)
    b = new(s)
    assert [r.id for r in s.list("u1")] == [b.id, a.id]
