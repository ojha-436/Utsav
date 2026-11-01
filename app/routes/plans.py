"""Open planning endpoints (login optional). The browser holds the skeleton between calls."""
from datetime import date

from fastapi import APIRouter, Depends

from app.ai.client import AIClient
from app.ai.service import generate_skeleton, refine_skeleton
from app.deps import get_ai, get_today, rate_limit_ai
from app.models import GenerateRequest, PlanResponse, RefineRequest, validate_event_date
from app.planning.assemble import assemble_plan

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
