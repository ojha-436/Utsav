"""What the user tells us about their event, and the rule for when it may take place."""

from datetime import date, timedelta

from pydantic import Field

from app.errors import InvalidInput
from app.models.common import EventType, Strict, Vibe

MAX_EVENT_DAYS_AHEAD = 1096
# Outer sanity bounds for any event date, so date arithmetic can never overflow.
EARLIEST_EVENT_DATE = date(2000, 1, 1)
LATEST_EVENT_DATE = date(2100, 12, 31)


class EventInput(Strict):
    """The details the user enters in the wizard."""

    event_type: EventType
    event_date: date = Field(ge=EARLIEST_EVENT_DATE, le=LATEST_EVENT_DATE)
    guest_count: int = Field(ge=1, le=5000)
    budget_inr: int = Field(ge=1000, le=100_000_000)
    city: str = Field(min_length=2, max_length=80)
    vibe: list[Vibe] = Field(default_factory=list, max_length=5)
    notes: str = Field(default="", max_length=500)


def validate_event_date(event_date: date, today: date) -> None:
    """New or changed events must be after today and at most ~3 years out."""
    if not today < event_date <= today + timedelta(days=MAX_EVENT_DAYS_AHEAD):
        raise InvalidInput("event_date must be after today and within 3 years")
