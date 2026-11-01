"""What a saved event looks like in storage, and the interface every store implements."""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol

from pydantic import BaseModel, Field

from app.errors import NotFound
from app.models import EventInput, PhotoIdea, PlanSkeleton, PlanSource, Source, SpendEntry, VendorItem

Clock = Callable[[], datetime]


def utc_now() -> datetime:
    """The current time, timezone-aware (UTC). The default clock for every store."""
    return datetime.now(UTC)


def event_not_found() -> NotFound:
    """The error every store raises for a missing (or someone else's) event."""
    return NotFound("Event not found")


class VendorCache(BaseModel):
    """Grounded vendor results saved on an event, reused for 24 hours."""

    fetched_at: datetime
    category_keys: list[str]
    items: list[VendorItem]
    sources: list[Source]


class EventRecord(BaseModel):
    """A saved event: the inputs and skeleton plus everything the user has done since."""

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
    """Per-user event storage. Every method is scoped to `uid`; other users' events are never visible."""

    def list(self, uid: str) -> list[EventRecord]:
        """The user's events, most recently updated first."""
        ...

    def create(self, uid: str, input: EventInput, skeleton: PlanSkeleton, generated_from: PlanSource) -> EventRecord:
        """Saves a new event and returns it with its generated id."""
        ...

    def get(self, uid: str, event_id: str) -> EventRecord:
        """One event. Raises NotFound if it doesn't exist for this user."""
        ...

    def update(self, uid: str, event_id: str, mutate: Callable[[EventRecord], None]) -> EventRecord:
        """Atomically reads the current record, applies `mutate`, and writes it back.

        Raises NotFound (and writes nothing) if the event doesn't exist; if `mutate`
        raises, nothing is written either.
        """
        ...

    def delete(self, uid: str, event_id: str) -> None:
        """Deletes an event. Raises NotFound if it doesn't exist for this user."""
        ...
