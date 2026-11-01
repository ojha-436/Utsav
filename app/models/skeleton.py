"""The plan skeleton: Gemini's suggestion and the source of truth for every saved plan.

`PlanSkeleton` is strict and is what the API accepts and stores. The `*Draft`
models carry the same fields with plain types only; they are Gemini's response
schema and are repaired into a `PlanSkeleton` by `app.planning.sanitize`.
"""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.models.common import IdeaKind, Slug, Strict


class BudgetCategory(Strict):
    """A budget category with a relative weight (rupees are computed later)."""

    key: Slug
    label: str = Field(min_length=1, max_length=60)
    weight: int = Field(ge=1, le=100)
    essential: bool
    note: str = Field(default="", max_length=160)


class Task(Strict):
    """A task due `days_before` the event (negative means after it)."""

    id: Slug
    title: str = Field(min_length=1, max_length=100)
    category_key: Slug
    days_before: int = Field(ge=-30, le=540)


class Vendor(Strict):
    """A vendor type to book, when to book it and what to ask."""

    category_key: Slug
    role: str = Field(min_length=1, max_length=60)
    questions_to_ask: list[Annotated[str, StringConstraints(min_length=1, max_length=120)]] = Field(
        min_length=1, max_length=5
    )
    book_by_days_before: int = Field(ge=0, le=540)


class Idea(Strict):
    """A personalised idea for the event."""

    title: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=300)
    kind: IdeaKind


class PlanSkeleton(Strict):
    """The validated plan skeleton. Ids and keys are unique within each list."""

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
    """Base for Gemini's response models: plain types, extra fields ignored."""

    model_config = ConfigDict(extra="ignore")


class BudgetCategoryDraft(Draft):
    """Unvalidated BudgetCategory."""

    key: str
    label: str
    weight: int
    essential: bool
    note: str = ""


class TaskDraft(Draft):
    """Unvalidated Task."""

    id: str
    title: str
    category_key: str
    days_before: int


class VendorDraft(Draft):
    """Unvalidated Vendor."""

    category_key: str
    role: str
    questions_to_ask: list[str]
    book_by_days_before: int


class IdeaDraft(Draft):
    """Unvalidated Idea."""

    title: str
    description: str
    kind: str


class SkeletonDraft(Draft):
    """Gemini's response schema; repaired into a PlanSkeleton by planning.sanitize."""

    title: str
    summary: str
    budget_categories: list[BudgetCategoryDraft]
    tasks: list[TaskDraft]
    vendors: list[VendorDraft]
    ideas: list[IdeaDraft]
