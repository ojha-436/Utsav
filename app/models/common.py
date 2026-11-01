"""Shared field types and the strict base model used by every input model."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints

EventType = Literal["wedding", "birthday", "community"]
Vibe = Literal["traditional", "modern", "eco", "intimate", "grand", "budget-friendly", "outdoor", "themed"]
IdeaKind = Literal["theme", "decor", "food", "activity", "favour"]
ItemStatus = Literal["done", "compressed", "due_today", "upcoming"]
PlanSource = Literal["ai", "default"]

Slug = Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9-]{0,39}$")]
ItemId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9-]{0,47}$")]
HexColour = Annotated[str, StringConstraints(pattern=r"^#[0-9a-f]{6}$")]


class Strict(BaseModel):
    """Rejects unknown fields and trims surrounding whitespace from strings."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
