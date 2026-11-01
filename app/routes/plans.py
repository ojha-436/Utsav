"""Open planning endpoints (login optional). The browser holds the skeleton between calls."""
from datetime import date, datetime

from fastapi import APIRouter, Depends, Response

from app.ai.client import AIClient
from app.ai.service import generate_skeleton, refine_skeleton
from app.deps import get_ai, get_now, get_today, rate_limit_ai
from app.models import CalendarRequest, GenerateRequest, PlanResponse, RefineRequest, validate_event_date
from app.planning.assemble import assemble_plan
from app.planning.ics import build_calendar

router = APIRouter(prefix="/api", dependencies=[Depends(rate_limit_ai)])


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
