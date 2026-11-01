"""Saved events: list, create, read, update and delete. Every lookup is scoped to the token's uid."""

from fastapi import APIRouter, Response

from app.auth import UserDep
from app.deps import StoreDep, TodayDep
from app.models import CreateEventRequest, EventResponse, EventSummary, UpdateEventRequest, validate_event_date
from app.routes.common import EventIdDep, event_id_param, to_response  # noqa: F401  (event_id_param is re-exported)
from app.store import EventRecord

router = APIRouter(prefix="/api/events")


@router.get("", response_model=list[EventSummary])
def list_events(uid: UserDep, store: StoreDep) -> list[EventSummary]:
    """The signed-in user's events, most recently updated first."""
    return [
        EventSummary(
            id=r.id,
            title=r.skeleton.title,
            event_type=r.input.event_type,
            event_date=r.input.event_date,
            updated_at=r.updated_at,
        )
        for r in store.list(uid)
    ]


@router.post("", status_code=201, response_model=EventResponse)
def create_event(body: CreateEventRequest, uid: UserDep, store: StoreDep, today: TodayDep) -> EventResponse:
    """Saves a plan; the event date must be in the future."""
    validate_event_date(body.input.event_date, today)
    return to_response(store.create(uid, body.input, body.skeleton, body.generated_from), today)


@router.get("/{event_id}", response_model=EventResponse)
def get_event(event_id: EventIdDep, uid: UserDep, store: StoreDep, today: TodayDep) -> EventResponse:
    """One saved event with its plan recomputed for today."""
    return to_response(store.get(uid, event_id), today)


@router.put("/{event_id}", response_model=EventResponse)
def update_event(
    body: UpdateEventRequest, event_id: EventIdDep, uid: UserDep, store: StoreDep, today: TodayDep
) -> EventResponse:
    """Replaces the skeleton after a refine; the input changes only when the user edits it."""

    def apply(record: EventRecord) -> None:
        if body.input is not None:
            if body.input.event_date != record.input.event_date:
                validate_event_date(body.input.event_date, today)
            if body.input != record.input:
                record.vendor_cache = None  # vendor results depend on city, size and budget
            record.input = body.input
        record.skeleton = body.skeleton
        record.generated_from = "ai"
        record.version += 1

    return to_response(store.update(uid, event_id, apply), today)


@router.delete("/{event_id}", status_code=204)
def delete_event(event_id: EventIdDep, uid: UserDep, store: StoreDep) -> Response:
    """Deletes a saved event."""
    store.delete(uid, event_id)
    return Response(status_code=204)
