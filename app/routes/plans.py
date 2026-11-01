"""Open planning endpoints (sign-in optional). The browser holds the skeleton between calls."""

from contextlib import suppress
from datetime import datetime

from fastapi import APIRouter, Depends, Response

from app.ai.service import find_vendors, generate_skeleton, refine_skeleton
from app.auth import OptionalUserDep
from app.deps import AIDep, NowDep, StoreDep, TodayDep, rate_limit_ai
from app.errors import NotFound, Unauthorized
from app.limits import VENDOR_CACHE_TTL
from app.models import (
    CalendarRequest,
    GenerateRequest,
    PlanResponse,
    RefineRequest,
    VendorRequest,
    VendorResponse,
    validate_event_date,
)
from app.planning.assemble import assemble_plan
from app.planning.ics import build_calendar
from app.routes.common import event_id_param
from app.store import EventRecord, EventStore, VendorCache

router = APIRouter(prefix="/api", dependencies=[Depends(rate_limit_ai)])


@router.post("/plans/generate", response_model=PlanResponse)
def generate(body: GenerateRequest, ai: AIDep, today: TodayDep) -> PlanResponse:
    """A new plan for the event (the built-in plan if Gemini is unavailable)."""
    validate_event_date(body.input.event_date, today)
    skeleton, source = generate_skeleton(ai, body.input, today)
    return PlanResponse(skeleton=skeleton, plan=assemble_plan(body.input, skeleton, today, source))


@router.post("/plans/refine", response_model=PlanResponse)
def refine(body: RefineRequest, ai: AIDep, today: TodayDep) -> PlanResponse:
    """The plan revised by a plain-language instruction."""
    skeleton = refine_skeleton(ai, body.input, body.skeleton, body.instruction, today)
    return PlanResponse(skeleton=skeleton, plan=assemble_plan(body.input, skeleton, today))


@router.post("/calendar.ics")
def calendar(body: CalendarRequest, today: TodayDep, now: NowDep) -> Response:
    """The plan's open tasks and bookings as a downloadable .ics file."""
    plan = assemble_plan(body.input, body.skeleton, today, done_ids=set(body.done_ids))
    return Response(
        build_calendar(plan.event, plan.title, plan.timeline.tasks, plan.vendors, now),
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="utsav-plan.ics"'},
    )


@router.post("/vendors", response_model=VendorResponse)
def vendors(body: VendorRequest, uid: OptionalUserDep, ai: AIDep, store: StoreDep, now: NowDep) -> VendorResponse:
    """Real local vendors via Google Search grounding; cached for 24 h on a saved event."""
    owned = _owned_event(body, uid, store)
    if owned is not None:
        cached = _fresh_cache(owned[1], body.category_keys, now)
        if cached is not None:
            return cached

    result = find_vendors(ai, body.input, body.category_keys)
    if owned is not None and result.items:
        owner, record = owned
        cache = VendorCache(
            fetched_at=now, category_keys=body.category_keys, items=result.items, sources=result.sources
        )
        _save_cache(store, owner, record.id, cache)
    return result


def _owned_event(body: VendorRequest, uid: str | None, store: EventStore) -> tuple[str, EventRecord] | None:
    """The signed-in owner and the saved event a vendor search belongs to, if any."""
    if body.event_id is None:
        return None
    if uid is None:
        raise Unauthorized("Sign in to use your saved event")
    return uid, store.get(uid, event_id_param(body.event_id))


def _fresh_cache(record: EventRecord, category_keys: list[str], now: datetime) -> VendorResponse | None:
    """The cached vendors if they cover the same categories and are under 24 hours old."""
    cache = record.vendor_cache
    if cache and set(cache.category_keys) == set(category_keys) and now - cache.fetched_at < VENDOR_CACHE_TTL:
        return VendorResponse(items=cache.items, sources=cache.sources)
    return None


def _save_cache(store: EventStore, uid: str, event_id: str, cache: VendorCache) -> None:
    """Writes only the cache onto the current record; the search may have taken 10-20 s."""
    with suppress(NotFound):  # deleted during the search; the results are still worth showing
        store.update(uid, event_id, lambda current: setattr(current, "vendor_cache", cache))
