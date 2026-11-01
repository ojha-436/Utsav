"""An in-memory event store for local development and tests."""

import threading
import uuid
from collections.abc import Callable

from app.models import EventInput, PlanSkeleton, PlanSource
from app.store.records import Clock, EventRecord, event_not_found, utc_now


class InMemoryEventStore:
    """Thread-safe and copy-on-read, so callers can never mutate stored state by accident."""

    def __init__(self, clock: Clock = utc_now) -> None:
        """`clock` sets created/updated times; tests pass a fixed one."""
        self._clock = clock
        self._records: dict[tuple[str, str], EventRecord] = {}
        self._lock = threading.Lock()

    def list(self, uid: str) -> list[EventRecord]:
        """The user's events, most recently updated first."""
        with self._lock:
            records = [r.model_copy(deep=True) for (owner, _), r in self._records.items() if owner == uid]
        return sorted(records, key=lambda r: r.updated_at, reverse=True)

    def create(self, uid: str, input: EventInput, skeleton: PlanSkeleton, generated_from: PlanSource) -> EventRecord:
        """Saves a new event under a random id."""
        now = self._clock()
        record = EventRecord(
            id=uuid.uuid4().hex,
            input=input,
            skeleton=skeleton,
            generated_from=generated_from,
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            self._records[(uid, record.id)] = record.model_copy(deep=True)
        return record

    def get(self, uid: str, event_id: str) -> EventRecord:
        """A copy of one event; NotFound if missing."""
        with self._lock:
            record = self._records.get((uid, event_id))
        if record is None:
            raise event_not_found()
        return record.model_copy(deep=True)

    def update(self, uid: str, event_id: str, mutate: Callable[[EventRecord], None]) -> EventRecord:
        """Read-mutate-write under one lock, so concurrent updates can't interleave."""
        with self._lock:
            current = self._records.get((uid, event_id))
            if current is None:
                raise event_not_found()
            record = current.model_copy(deep=True)
            mutate(record)
            record.updated_at = self._clock()
            self._records[(uid, event_id)] = record.model_copy(deep=True)
        return record

    def delete(self, uid: str, event_id: str) -> None:
        """Removes an event; NotFound if missing."""
        with self._lock:
            if self._records.pop((uid, event_id), None) is None:
                raise event_not_found()
