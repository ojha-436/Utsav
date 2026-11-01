"""Progress and spending on a saved event: tick items, log and remove spend."""

import uuid

from fastapi import APIRouter

from app.auth import UserDep
from app.deps import NowDep, StoreDep, TodayDep
from app.errors import InvalidInput, NotFound
from app.limits import MAX_SPEND_ENTRIES
from app.models import EventResponse, SpendCreate, SpendEntry, TaskToggle
from app.planning.sanitize import ensure_contingency
from app.planning.timeline import vendor_item_id
from app.routes.common import EventIdDep, to_response
from app.store import EventRecord

router = APIRouter(prefix="/api/events")


@router.patch("/{event_id}/tasks/{task_id}", response_model=EventResponse)
def toggle_item(
    body: TaskToggle, task_id: str, event_id: EventIdDep, uid: UserDep, store: StoreDep, today: TodayDep, now: NowDep
) -> EventResponse:
    """Ticks or unticks a timeline task or a vendor checklist item."""

    def apply(record: EventRecord) -> None:
        item_ids = {t.id for t in record.skeleton.tasks} | {
            vendor_item_id(v.category_key) for v in record.skeleton.vendors
        }
        if task_id not in item_ids:
            raise NotFound("Task not found")
        if body.done:
            record.progress[task_id] = now
        else:
            record.progress.pop(task_id, None)

    return to_response(store.update(uid, event_id, apply), today)


@router.post("/{event_id}/spend", status_code=201, response_model=EventResponse)
def add_spend(
    body: SpendCreate, event_id: EventIdDep, uid: UserDep, store: StoreDep, today: TodayDep, now: NowDep
) -> EventResponse:
    """Logs spending against one of the plan's budget categories."""

    def apply(record: EventRecord) -> None:
        if body.category_key not in {c.key for c in ensure_contingency(record.skeleton.budget_categories)}:
            raise InvalidInput("Pick one of this plan's budget categories")
        if len(record.spend) >= MAX_SPEND_ENTRIES:
            raise InvalidInput("This event already has the maximum number of spend entries")
        record.spend.append(
            SpendEntry(id=uuid.uuid4().hex, category_key=body.category_key, amount=body.amount, note=body.note, at=now)
        )

    return to_response(store.update(uid, event_id, apply), today)


@router.delete("/{event_id}/spend/{entry_id}", response_model=EventResponse)
def delete_spend(entry_id: str, event_id: EventIdDep, uid: UserDep, store: StoreDep, today: TodayDep) -> EventResponse:
    """Removes a spend entry."""

    def apply(record: EventRecord) -> None:
        remaining = [entry for entry in record.spend if entry.id != entry_id]
        if len(remaining) == len(record.spend):
            raise NotFound("Spend entry not found")
        record.spend = remaining

    return to_response(store.update(uid, event_id, apply), today)
