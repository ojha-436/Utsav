"""Request and response bodies of the HTTP API."""

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.common import EventType, ItemId, PlanSource, Slug, Strict
from app.models.event import EventInput
from app.models.plan import Plan, SpendEntry
from app.models.skeleton import PlanSkeleton


class GenerateRequest(Strict):
    input: EventInput


class RefineRequest(Strict):
    input: EventInput
    skeleton: PlanSkeleton
    instruction: str = Field(min_length=1, max_length=300)


class PlanResponse(BaseModel):
    skeleton: PlanSkeleton
    plan: Plan


class CalendarRequest(Strict):
    input: EventInput
    skeleton: PlanSkeleton
    done_ids: list[ItemId] = Field(default_factory=list, max_length=60)


class Source(BaseModel):
    title: str
    uri: str


class VendorItem(Strict):
    category_key: Slug
    name: str = Field(min_length=1, max_length=100)
    why: str = Field(default="", max_length=200)
    area: str | None = Field(default=None, max_length=80)
    source_index: int | None = None


class VendorRequest(Strict):
    input: EventInput
    category_keys: list[Slug] = Field(min_length=1, max_length=4)
    event_id: str | None = None


class VendorResponse(BaseModel):
    items: list[VendorItem]
    sources: list[Source]
    message: str | None = None


class CreateEventRequest(Strict):
    input: EventInput
    skeleton: PlanSkeleton
    generated_from: PlanSource = "ai"


class UpdateEventRequest(Strict):
    input: EventInput | None = None
    skeleton: PlanSkeleton


class TaskToggle(Strict):
    done: bool


class SpendCreate(Strict):
    category_key: Slug
    amount: int = Field(ge=1, le=100_000_000)
    note: str = Field(default="", max_length=120)


class EventSummary(BaseModel):
    id: str
    title: str
    event_type: EventType
    event_date: date
    updated_at: datetime


class EventResponse(BaseModel):
    id: str
    version: int
    skeleton: PlanSkeleton
    plan: Plan
    spend: list[SpendEntry] = Field(default_factory=list)  # entries, so the UI can delete one
