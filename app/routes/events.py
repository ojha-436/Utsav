"""Saved events (sign-in required). Every lookup is scoped to the token's uid."""
import re
import uuid
from datetime import date, datetime

from fastapi import APIRouter, Depends, Response

from app.auth import require_user
from app.deps import get_now, get_store, get_today
from app.errors import InvalidInput, NotFound
from app.models import (
    CreateEventRequest,
    EventResponse,
    EventSummary,
    Plan,
    SpendCreate,
    SpendEntry,
    TaskToggle,
    UpdateEventRequest,
    validate_event_date,
)
from app.planning.assemble import assemble_plan
from app.planning.sanitize import ensure_contingency
from app.planning.timeline import vendor_item_id
from app.store import EventRecord, EventStore

router = APIRouter(prefix="/api/events")
_EVENT_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
MAX_SPEND_ENTRIES = 500  # keeps each Firestore document well under its 1 MiB limit


def event_id_param(event_id: str) -> str:
    if not _EVENT_ID.match(event_id):
        raise NotFound("Event not found")
    return event_id


def record_plan(record: EventRecord, today: date) -> Plan:
    return assemble_plan(record.input, record.skeleton, today, record.generated_from,
                         set(record.progress), record.spend, record.photo_ideas)


def to_response(record: EventRecord, today: date) -> EventResponse:
    return EventResponse(id=record.id, version=record.version, skeleton=record.skeleton,
                         plan=record_plan(record, today), spend=record.spend)


@router.get("", response_model=list[EventSummary])
def list_events(uid: str = Depends(require_user), store: EventStore = Depends(get_store)) -> list[EventSummary]:
    return [
        EventSummary(id=r.id, title=r.skeleton.title, event_type=r.input.event_type,
                     event_date=r.input.event_date, updated_at=r.updated_at)
        for r in store.list(uid)
    ]


@router.post("", status_code=201, response_model=EventResponse)
def create_event(body: CreateEventRequest, uid: str = Depends(require_user),
                 store: EventStore = Depends(get_store), today: date = Depends(get_today)) -> EventResponse:
    validate_event_date(body.input.event_date, today)
    return to_response(store.create(uid, body.input, body.skeleton, body.generated_from), today)


@router.get("/{event_id}", response_model=EventResponse)
def get_event(event_id: str = Depends(event_id_param), uid: str = Depends(require_user),
              store: EventStore = Depends(get_store), today: date = Depends(get_today)) -> EventResponse:
    return to_response(store.get(uid, event_id), today)


@router.put("/{event_id}", response_model=EventResponse)
def update_event(body: UpdateEventRequest, event_id: str = Depends(event_id_param), uid: str = Depends(require_user),
                 store: EventStore = Depends(get_store), today: date = Depends(get_today)) -> EventResponse:
    record = store.get(uid, event_id)
    if body.input is not None:
        if body.input.event_date != record.input.event_date:
            validate_event_date(body.input.event_date, today)
        record.input = body.input
    record.skeleton = body.skeleton
    record.generated_from = "ai"
    record.version += 1
    return to_response(store.save(uid, record), today)


@router.delete("/{event_id}", status_code=204)
def delete_event(event_id: str = Depends(event_id_param), uid: str = Depends(require_user),
                 store: EventStore = Depends(get_store)) -> Response:
    store.delete(uid, event_id)
    return Response(status_code=204)


@router.patch("/{event_id}/tasks/{task_id}", response_model=EventResponse)
def toggle_item(body: TaskToggle, task_id: str, event_id: str = Depends(event_id_param), uid: str = Depends(require_user),
                store: EventStore = Depends(get_store), today: date = Depends(get_today),
                now: datetime = Depends(get_now)) -> EventResponse:
    """Tick or untick a timeline task or a vendor checklist item."""
    record = store.get(uid, event_id)
    item_ids = {t.id for t in record.skeleton.tasks} | {vendor_item_id(v.category_key) for v in record.skeleton.vendors}
    if task_id not in item_ids:
        raise NotFound("Task not found")
    if body.done:
        record.progress[task_id] = now
    else:
        record.progress.pop(task_id, None)
    return to_response(store.save(uid, record), today)


@router.post("/{event_id}/spend", status_code=201, response_model=EventResponse)
def add_spend(body: SpendCreate, event_id: str = Depends(event_id_param), uid: str = Depends(require_user),
              store: EventStore = Depends(get_store), today: date = Depends(get_today),
              now: datetime = Depends(get_now)) -> EventResponse:
    record = store.get(uid, event_id)
    if body.category_key not in {c.key for c in ensure_contingency(record.skeleton.budget_categories)}:
        raise InvalidInput("Pick one of this plan's budget categories")
    if len(record.spend) >= MAX_SPEND_ENTRIES:
        raise InvalidInput("This event already has the maximum number of spend entries")
    record.spend.append(SpendEntry(id=uuid.uuid4().hex, category_key=body.category_key,
                                   amount=body.amount, note=body.note, at=now))
    return to_response(store.save(uid, record), today)


@router.delete("/{event_id}/spend/{entry_id}", response_model=EventResponse)
def delete_spend(entry_id: str, event_id: str = Depends(event_id_param), uid: str = Depends(require_user),
                 store: EventStore = Depends(get_store), today: date = Depends(get_today)) -> EventResponse:
    record = store.get(uid, event_id)
    remaining = [entry for entry in record.spend if entry.id != entry_id]
    if len(remaining) == len(record.spend):
        raise NotFound("Spend entry not found")
    record.spend = remaining
    return to_response(store.save(uid, record), today)
