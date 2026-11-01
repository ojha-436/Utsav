"""Pydantic models: user input, the Gemini skeleton, the computed plan, and API bodies."""
from datetime import date, datetime, timedelta
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.errors import InvalidInput

EventType = Literal["wedding", "birthday", "community"]
Vibe = Literal["traditional", "modern", "eco", "intimate", "grand", "budget-friendly", "outdoor", "themed"]
IdeaKind = Literal["theme", "decor", "food", "activity", "favour"]
ItemStatus = Literal["done", "compressed", "due_today", "upcoming"]
PlanSource = Literal["ai", "default"]

Slug = Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9-]{0,39}$")]
ItemId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9-]{0,47}$")]
HexColour = Annotated[str, StringConstraints(pattern=r"^#[0-9a-f]{6}$")]

MAX_EVENT_DAYS_AHEAD = 1096


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# --- user input -------------------------------------------------------------

class EventInput(Strict):
    event_type: EventType
    event_date: date
    guest_count: int = Field(ge=1, le=5000)
    budget_inr: int = Field(ge=1000, le=100_000_000)
    city: str = Field(min_length=2, max_length=80)
    vibe: list[Vibe] = Field(default_factory=list, max_length=5)
    notes: str = Field(default="", max_length=500)


def validate_event_date(event_date: date, today: date) -> None:
    """New or changed events must be after today and at most ~3 years out."""
    if not today < event_date <= today + timedelta(days=MAX_EVENT_DAYS_AHEAD):
        raise InvalidInput("event_date must be after today and within 3 years")


# --- skeleton (source of truth) ---------------------------------------------

class BudgetCategory(Strict):
    key: Slug
    label: str = Field(min_length=1, max_length=60)
    weight: int = Field(ge=1, le=100)
    essential: bool
    note: str = Field(default="", max_length=160)


class Task(Strict):
    id: Slug
    title: str = Field(min_length=1, max_length=100)
    category_key: Slug
    days_before: int = Field(ge=-30, le=540)


class Vendor(Strict):
    category_key: Slug
    role: str = Field(min_length=1, max_length=60)
    questions_to_ask: list[Annotated[str, StringConstraints(min_length=1, max_length=120)]] = Field(min_length=1, max_length=5)
    book_by_days_before: int = Field(ge=0, le=540)


class Idea(Strict):
    title: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=300)
    kind: IdeaKind


class PlanSkeleton(Strict):
    title: str = Field(min_length=1, max_length=80)
    summary: str = Field(max_length=400)
    budget_categories: list[BudgetCategory] = Field(min_length=3, max_length=14)
    tasks: list[Task] = Field(min_length=5, max_length=40)
    vendors: list[Vendor] = Field(default_factory=list, max_length=12)
    ideas: list[Idea] = Field(min_length=3, max_length=10)

    @model_validator(mode="after")
    def _unique_ids(self) -> "PlanSkeleton":
        for name, ids in (
            ("budget category keys", [c.key for c in self.budget_categories]),
            ("task ids", [t.id for t in self.tasks]),
            ("vendor category keys", [v.category_key for v in self.vendors]),
        ):
            if len(ids) != len(set(ids)):
                raise ValueError(f"duplicate {name}")
        return self


# Gemini-facing drafts: plain types only, repaired by planning.sanitize.

class Draft(BaseModel):
    model_config = ConfigDict(extra="ignore")


class BudgetCategoryDraft(Draft):
    key: str
    label: str
    weight: int
    essential: bool
    note: str = ""


class TaskDraft(Draft):
    id: str
    title: str
    category_key: str
    days_before: int


class VendorDraft(Draft):
    category_key: str
    role: str
    questions_to_ask: list[str]
    book_by_days_before: int


class IdeaDraft(Draft):
    title: str
    description: str
    kind: str


class SkeletonDraft(Draft):
    title: str
    summary: str
    budget_categories: list[BudgetCategoryDraft]
    tasks: list[TaskDraft]
    vendors: list[VendorDraft]
    ideas: list[IdeaDraft]


# --- computed plan (never stored) ------------------------------------------

class PlanWarning(BaseModel):
    code: str
    message: str


class BudgetLine(BaseModel):
    key: str
    label: str
    amount: int
    percent: float
    per_guest: int
    essential: bool


class Budget(BaseModel):
    total: int
    per_guest: int
    lines: list[BudgetLine]
    warnings: list[PlanWarning]


class ScheduledTask(BaseModel):
    id: str
    title: str
    category_key: str
    original_due: date
    due: date
    status: ItemStatus


class Timeline(BaseModel):
    tasks: list[ScheduledTask]
    short_notice: bool
    completion_pct: int


class ScheduledVendor(BaseModel):
    id: str
    category_key: str
    role: str
    questions_to_ask: list[str]
    original_book_by: date
    book_by: date
    status: ItemStatus


class TrackingLine(BaseModel):
    key: str
    label: str
    planned: int
    actual: int
    variance: int


class Tracking(BaseModel):
    lines: list[TrackingLine]
    other_actual: int


class PhotoIdea(Strict):
    title: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=300)
    palette: list[HexColour] = Field(min_length=1, max_length=6)


class SpendEntry(Strict):
    id: str
    category_key: Slug
    amount: int = Field(ge=1, le=100_000_000)
    note: str = Field(default="", max_length=120)
    at: datetime


class Plan(BaseModel):
    event: EventInput
    title: str
    summary: str
    generated_from: PlanSource
    budget: Budget
    timeline: Timeline
    vendors: list[ScheduledVendor]
    ideas: list[Idea]
    photo_ideas: list[PhotoIdea]
    tracking: Tracking | None


# --- API bodies --------------------------------------------------------------

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
