import threading
import time
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


def test_update_mutates_atomically_and_returns_copies():
    t = [datetime(2026, 11, 1, tzinfo=UTC)]
    s = InMemoryEventStore(clock=lambda: t[0])
    r = new(s)
    s.get("u1", r.id).progress.clear()
    t[0] = datetime(2026, 11, 2, tzinfo=UTC)
    updated = s.update("u1", r.id, lambda rec: rec.progress.__setitem__("book-venue", t[0]))
    assert "book-venue" in updated.progress and s.get("u1", r.id).updated_at == t[0]
    updated.progress.clear()
    assert "book-venue" in s.get("u1", r.id).progress


def test_update_unknown_or_deleted_event_raises_and_never_recreates():
    s = InMemoryEventStore()
    r = new(s)
    with pytest.raises(NotFound):
        s.update("u2", r.id, lambda rec: None)
    s.delete("u1", r.id)
    with pytest.raises(NotFound):
        s.update("u1", r.id, lambda rec: None)
    assert s.list("u1") == []


def test_update_failure_leaves_record_unchanged():
    s = InMemoryEventStore()
    r = new(s)

    def mutate(rec):
        rec.progress["book-venue"] = datetime(2026, 11, 1, tzinfo=UTC)
        raise NotFound("Task not found")

    with pytest.raises(NotFound):
        s.update("u1", r.id, mutate)
    assert s.get("u1", r.id).progress == {}


def test_concurrent_updates_are_not_lost():
    s = InMemoryEventStore()
    r = new(s)

    def tick(i):
        def mutate(rec):
            time.sleep(0.002)
            rec.progress[f"task-{i}"] = datetime(2026, 11, 1, tzinfo=UTC)
        s.update("u1", r.id, mutate)

    threads = [threading.Thread(target=tick, args=(i,)) for i in range(20)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    assert len(s.get("u1", r.id).progress) == 20


def test_list_newest_first():
    t = [datetime(2026, 11, 1, tzinfo=UTC)]
    s = InMemoryEventStore(clock=lambda: t[0])
    a = new(s)
    t[0] = datetime(2026, 11, 2, tzinfo=UTC)
    b = new(s)
    assert [r.id for r in s.list("u1")] == [b.id, a.id]
