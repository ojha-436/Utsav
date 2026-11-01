"""Helpers shared by the saved-event routes."""

import re
from datetime import date
from typing import Annotated

from fastapi import Depends

from app.errors import NotFound
from app.models import EventResponse, Plan
from app.planning.assemble import assemble_plan
from app.store import EventRecord

# Firestore auto-ids and our uuid hex ids are both alphanumeric; anything else can't exist.
_EVENT_ID = re.compile(r"^[A-Za-z0-9]{1,64}$")


def event_id_param(event_id: str) -> str:
    """Validates the {event_id} path segment; malformed ids are simply not found."""
    if not _EVENT_ID.match(event_id):
        raise NotFound("Event not found")
    return event_id


EventIdDep = Annotated[str, Depends(event_id_param)]


def record_plan(record: EventRecord, today: date) -> Plan:
    """Recomputes the plan for a saved event, including progress, spend and photo ideas."""
    return assemble_plan(
        record.input,
        record.skeleton,
        today,
        record.generated_from,
        set(record.progress),
        record.spend,
        record.photo_ideas,
    )


def to_response(record: EventRecord, today: date) -> EventResponse:
    return EventResponse(
        id=record.id,
        version=record.version,
        skeleton=record.skeleton,
        plan=record_plan(record, today),
        spend=record.spend,
    )
