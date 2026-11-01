"""Open planning endpoints (login optional). The browser holds the skeleton between calls."""
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Response

from app.ai.client import AIClient
from app.ai.service import find_vendors, generate_skeleton, refine_skeleton
from app.auth import optional_user
from app.deps import get_ai, get_now, get_store, get_today, rate_limit_ai
from app.errors import Unauthorized
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
from app.routes.events import event_id_param
from app.store import EventStore, VendorCache

router = APIRouter(prefix="/api", dependencies=[Depends(rate_limit_ai)])
VENDOR_CACHE_TTL = timedelta(hours=24)


@router.post("/plans/generate", response_model=PlanResponse)
def generate(body: GenerateRequest, ai: AIClient = Depends(get_ai), today: date = Depends(get_today)) -> PlanResponse:
    validate_event_date(body.input.event_date, today)
    skeleton, source = generate_skeleton(ai, body.input, today)
    return PlanResponse(skeleton=skeleton, plan=assemble_plan(body.input, skeleton, today, source))


@router.post("/plans/refine", response_model=PlanResponse)
def refine(body: RefineRequest, ai: AIClient = Depends(get_ai), today: date = Depends(get_today)) -> PlanResponse:
    skeleton = refine_skeleton(ai, body.input, body.skeleton, body.instruction, today)
    return PlanResponse(skeleton=skeleton, plan=assemble_plan(body.input, skeleton, today))


@router.post("/calendar.ics")
def calendar(body: CalendarRequest, today: date = Depends(get_today), now: datetime = Depends(get_now)) -> Response:
    plan = assemble_plan(body.input, body.skeleton, today, done_ids=set(body.done_ids))
    return Response(
        build_calendar(plan.event, plan.title, plan.timeline.tasks, plan.vendors, now),
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="utsav-plan.ics"'},
    )


@router.post("/vendors", response_model=VendorResponse)
def vendors(body: VendorRequest, uid: str | None = Depends(optional_user), ai: AIClient = Depends(get_ai),
            store: EventStore = Depends(get_store), now: datetime = Depends(get_now)) -> VendorResponse:
    """Real local vendors via Google Search grounding; cached for 24 h on a saved event."""
    record = None
    if body.event_id is not None:
        if uid is None:
            raise Unauthorized("Sign in to use your saved event")
        record = store.get(uid, event_id_param(body.event_id))
        cache = record.vendor_cache
        if cache and set(cache.category_keys) == set(body.category_keys) and now - cache.fetched_at < VENDOR_CACHE_TTL:
            return VendorResponse(items=cache.items, sources=cache.sources)

    result = find_vendors(ai, body.input, body.category_keys)
    if record is not None and result.items:
        record.vendor_cache = VendorCache(fetched_at=now, category_keys=body.category_keys,
                                          items=result.items, sources=result.sources)
        store.save(uid, record)
    return result
