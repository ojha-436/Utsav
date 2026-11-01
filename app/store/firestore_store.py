"""The production event store: Firestore at planner_users/{uid}/events/{eventId}."""

from collections.abc import Callable
from typing import TYPE_CHECKING

from app.errors import Conflict
from app.models import EventInput, PlanSkeleton, PlanSource
from app.store.records import Clock, EventRecord, event_not_found, utc_now

if TYPE_CHECKING:  # imported lazily at runtime so tests never need Google libraries loaded
    from google.cloud import firestore

FIRESTORE_MAX_ATTEMPTS = 15  # quick successive ticks on one event contend for the same document


class FirestoreEventStore:
    """Firestore-backed store. Updates run in a transaction, so concurrent writes never lose data."""

    def __init__(self, client: "firestore.Client", clock: Clock = utc_now) -> None:
        """Wraps a Firestore client; `clock` sets created/updated times."""
        self._client = client
        self._clock = clock

    def _events(self, uid: str) -> "firestore.CollectionReference":
        return self._client.collection("planner_users").document(uid).collection("events")

    def list(self, uid: str) -> list[EventRecord]:
        """The user's events, most recently updated first (sorted here; per-user lists are small)."""
        records = [EventRecord.model_validate(doc.to_dict()) for doc in self._events(uid).stream()]
        return sorted(records, key=lambda r: r.updated_at, reverse=True)

    def create(self, uid: str, input: EventInput, skeleton: PlanSkeleton, generated_from: PlanSource) -> EventRecord:
        """Saves a new event under a Firestore auto-id."""
        ref = self._events(uid).document()
        now = self._clock()
        record = EventRecord(
            id=ref.id, input=input, skeleton=skeleton, generated_from=generated_from, created_at=now, updated_at=now
        )
        ref.set(record.model_dump(mode="json"))
        return record

    def get(self, uid: str, event_id: str) -> EventRecord:
        """One event; NotFound if missing."""
        snapshot = self._events(uid).document(event_id).get()
        if not snapshot.exists:
            raise event_not_found()
        return EventRecord.model_validate(snapshot.to_dict())

    def update(self, uid: str, event_id: str, mutate: Callable[[EventRecord], None]) -> EventRecord:
        """Transactional read-mutate-write. Never recreates a deleted event.

        Raises Conflict (409) if contention outlasts the transaction's retries.
        """
        from google.cloud import firestore

        ref = self._events(uid).document(event_id)

        @firestore.transactional
        def run(transaction: "firestore.Transaction") -> EventRecord:
            snapshot = ref.get(transaction=transaction)
            if not snapshot.exists:
                raise event_not_found()
            record = EventRecord.model_validate(snapshot.to_dict())
            mutate(record)
            record.updated_at = self._clock()
            transaction.set(ref, record.model_dump(mode="json"))
            return record

        try:
            return run(self._client.transaction(max_attempts=FIRESTORE_MAX_ATTEMPTS))
        except ValueError as exc:
            if str(exc).startswith("Failed to commit transaction"):
                raise Conflict("Too many changes at once; please try again") from exc
            raise

    def delete(self, uid: str, event_id: str) -> None:
        """Deletes an event; NotFound if missing."""
        ref = self._events(uid).document(event_id)
        if not ref.get().exists:
            raise event_not_found()
        ref.delete()
