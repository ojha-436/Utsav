"""Saved events, scoped per user: planner_users/{uid}/events/{eventId}."""
import threading
import uuid
from datetime import UTC, datetime
from typing import Protocol

from pydantic import BaseModel, Field

from app.errors import NotFound
from app.models import EventInput, PhotoIdea, PlanSkeleton, PlanSource, Source, SpendEntry, VendorItem


def utc_now() -> datetime:
    return datetime.now(UTC)


class VendorCache(BaseModel):
    fetched_at: datetime
    category_keys: list[str]
    items: list[VendorItem]
    sources: list[Source]


class EventRecord(BaseModel):
    id: str
    input: EventInput
    skeleton: PlanSkeleton
    generated_from: PlanSource = "ai"
    version: int = 1
    created_at: datetime
    updated_at: datetime
    progress: dict[str, datetime] = Field(default_factory=dict)
    spend: list[SpendEntry] = Field(default_factory=list)
    vendor_cache: VendorCache | None = None
    photo_ideas: list[PhotoIdea] = Field(default_factory=list)


class EventStore(Protocol):
    def list(self, uid: str) -> list[EventRecord]: ...

    def create(self, uid: str, input: EventInput, skeleton: PlanSkeleton, generated_from: PlanSource) -> EventRecord: ...

    def get(self, uid: str, event_id: str) -> EventRecord: ...

    def save(self, uid: str, record: EventRecord) -> EventRecord: ...

    def delete(self, uid: str, event_id: str) -> None: ...


def _not_found() -> NotFound:
    return NotFound("Event not found")


class InMemoryEventStore:
    """For local development and tests. Hands out copies so callers can't mutate stored state."""

    def __init__(self, clock=utc_now):
        self._clock = clock
        self._records: dict[tuple[str, str], EventRecord] = {}
        self._lock = threading.Lock()

    def list(self, uid: str) -> list[EventRecord]:
        with self._lock:
            records = [r.model_copy(deep=True) for (owner, _), r in self._records.items() if owner == uid]
        return sorted(records, key=lambda r: r.updated_at, reverse=True)

    def create(self, uid: str, input: EventInput, skeleton: PlanSkeleton, generated_from: PlanSource) -> EventRecord:
        now = self._clock()
        record = EventRecord(id=uuid.uuid4().hex, input=input, skeleton=skeleton, generated_from=generated_from,
                             created_at=now, updated_at=now)
        with self._lock:
            self._records[(uid, record.id)] = record.model_copy(deep=True)
        return record

    def get(self, uid: str, event_id: str) -> EventRecord:
        with self._lock:
            record = self._records.get((uid, event_id))
        if record is None:
            raise _not_found()
        return record.model_copy(deep=True)

    def save(self, uid: str, record: EventRecord) -> EventRecord:
        updated = record.model_copy(update={"updated_at": self._clock()}, deep=True)
        with self._lock:
            if (uid, record.id) not in self._records:
                raise _not_found()
            self._records[(uid, record.id)] = updated.model_copy(deep=True)
        return updated

    def delete(self, uid: str, event_id: str) -> None:
        with self._lock:
            if self._records.pop((uid, event_id), None) is None:
                raise _not_found()


class FirestoreEventStore:
    def __init__(self, client, clock=utc_now):
        self._client = client
        self._clock = clock

    def _events(self, uid: str):
        return self._client.collection("planner_users").document(uid).collection("events")

    def list(self, uid: str) -> list[EventRecord]:
        records = [EventRecord.model_validate(doc.to_dict()) for doc in self._events(uid).stream()]
        return sorted(records, key=lambda r: r.updated_at, reverse=True)

    def create(self, uid: str, input: EventInput, skeleton: PlanSkeleton, generated_from: PlanSource) -> EventRecord:
        ref = self._events(uid).document()
        now = self._clock()
        record = EventRecord(id=ref.id, input=input, skeleton=skeleton, generated_from=generated_from,
                             created_at=now, updated_at=now)
        ref.set(record.model_dump(mode="json"))
        return record

    def get(self, uid: str, event_id: str) -> EventRecord:
        snapshot = self._events(uid).document(event_id).get()
        if not snapshot.exists:
            raise _not_found()
        return EventRecord.model_validate(snapshot.to_dict())

    def save(self, uid: str, record: EventRecord) -> EventRecord:
        ref = self._events(uid).document(record.id)
        if not ref.get().exists:
            raise _not_found()
        updated = record.model_copy(update={"updated_at": self._clock()})
        ref.set(updated.model_dump(mode="json"))
        return updated

    def delete(self, uid: str, event_id: str) -> None:
        ref = self._events(uid).document(event_id)
        if not ref.get().exists:
            raise _not_found()
        ref.delete()
