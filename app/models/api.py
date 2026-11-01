"""Request and response bodies of the HTTP API."""

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.common import EventType, ItemId, PlanSource, Slug, Strict
from app.models.event import EventInput
from app.models.plan import Plan, SpendEntry
from app.models.skeleton import PlanSkeleton


class GenerateRequest(Strict):
    """Body of POST /api/plans/generate."""

    input: EventInput


class RefineRequest(Strict):
    """Body of POST /api/plans/refine: the current plan and a plain-language instruction."""

    input: EventInput
    skeleton: PlanSkeleton
    instruction: str = Field(min_length=1, max_length=300)


class PlanResponse(BaseModel):
    """A skeleton and the plan computed from it."""

    skeleton: PlanSkeleton
    plan: Plan


class CalendarRequest(Strict):
    """Body of POST /api/calendar.ics; ticked items are left out of the calendar."""

    input: EventInput
    skeleton: PlanSkeleton
    done_ids: list[ItemId] = Field(default_factory=list, max_length=60)


class Source(BaseModel):
    """A citation from Google Search grounding."""

    title: str
    uri: str


class VendorItem(Strict):
    """One suggested local vendor."""

    category_key: Slug
    name: str = Field(min_length=1, max_length=100)
    why: str = Field(default="", max_length=200)
    area: str | None = Field(default=None, max_length=80)
    source_index: int | None = None


class VendorRequest(Strict):
    """Body of POST /api/vendors; `event_id` enables the 24-hour cache on a saved event."""

    input: EventInput
    category_keys: list[Slug] = Field(min_length=1, max_length=4)
    event_id: str | None = None


class VendorResponse(BaseModel):
    """Suggested vendors with their sources, or a message when none could be found."""

    items: list[VendorItem]
    sources: list[Source]
    message: str | None = None


class CreateEventRequest(Strict):
    """Body of POST /api/events: save a plan to the user's events."""

    input: EventInput
    skeleton: PlanSkeleton
    generated_from: PlanSource = "ai"


class UpdateEventRequest(Strict):
    """Body of PUT /api/events/{id}: a refined skeleton and, optionally, edited inputs."""

    input: EventInput | None = None
    skeleton: PlanSkeleton


class TaskToggle(Strict):
    """Body of PATCH /api/events/{id}/tasks/{task_id}."""

    done: bool


class SpendCreate(Strict):
    """Body of POST /api/events/{id}/spend."""

    category_key: Slug
    amount: int = Field(ge=1, le=100_000_000)
    note: str = Field(default="", max_length=120)


class EventSummary(BaseModel):
    """One row of the user's event list."""

    id: str
    title: str
    event_type: EventType
    event_date: date
    updated_at: datetime


class EventResponse(BaseModel):
    """A saved event: its skeleton, the computed plan and its spend entries."""

    id: str
    version: int
    skeleton: PlanSkeleton
    plan: Plan
    spend: list[SpendEntry] = Field(default_factory=list)  # entries, so the UI can delete one
