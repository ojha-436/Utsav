"""The computed plan returned to the browser. Recalculated on every read, never stored."""

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.common import HexColour, ItemStatus, PlanSource, Slug, Strict
from app.models.event import EventInput
from app.models.skeleton import Idea


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
