"""The computed plan returned to the browser. Recalculated on every read, never stored."""

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.common import HexColour, ItemStatus, PlanSource, Slug, Strict
from app.models.event import EventInput
from app.models.skeleton import Idea


class PlanWarning(BaseModel):
    """A note shown with the budget, e.g. when the per-guest budget is tight."""

    code: str
    message: str


class BudgetLine(BaseModel):
    """One category's share of the budget, in whole rupees."""

    key: str
    label: str
    amount: int
    percent: float
    per_guest: int
    essential: bool


class Budget(BaseModel):
    """The budget split; the lines always add up exactly to `total`."""

    total: int
    per_guest: int
    lines: list[BudgetLine]
    warnings: list[PlanWarning]


class ScheduledTask(BaseModel):
    """A task with its real due date; `original_due` differs when it was moved to today."""

    id: str
    title: str
    category_key: str
    original_due: date
    due: date
    status: ItemStatus


class Timeline(BaseModel):
    """All tasks in date order, plus progress."""

    tasks: list[ScheduledTask]
    short_notice: bool
    completion_pct: int


class ScheduledVendor(BaseModel):
    """A vendor to book, with its book-by date and questions to ask."""

    id: str
    category_key: str
    role: str
    questions_to_ask: list[str]
    original_book_by: date
    book_by: date
    status: ItemStatus


class TrackingLine(BaseModel):
    """Planned versus actual spending for one category."""

    key: str
    label: str
    planned: int
    actual: int
    variance: int


class Tracking(BaseModel):
    """Spending per category; spend on removed categories is totalled in `other_actual`."""

    lines: list[TrackingLine]
    other_actual: int


class PhotoIdea(Strict):
    """A decor idea from an inspiration photo, with its colour palette."""

    title: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=300)
    palette: list[HexColour] = Field(min_length=1, max_length=6)


class SpendEntry(Strict):
    """One logged payment."""

    id: str
    category_key: Slug
    amount: int = Field(ge=1, le=100_000_000)
    note: str = Field(default="", max_length=120)
    at: datetime


class Plan(BaseModel):
    """Everything the dashboard shows. Recomputed on every request, never stored."""

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
