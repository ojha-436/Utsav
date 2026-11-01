"""Combine a skeleton with the event, today's date and saved progress into a Plan."""

from collections.abc import Iterable
from datetime import date

from app.models import EventInput, PhotoIdea, Plan, PlanSkeleton, PlanSource, SpendEntry, Timeline
from app.planning.budget import allocate
from app.planning.sanitize import ensure_contingency
from app.planning.timeline import schedule_tasks, schedule_vendors, vendor_item_id
from app.planning.tracking import completion_pct, spend_tracking


def assemble_plan(
    event: EventInput,
    skeleton: PlanSkeleton,
    today: date,
    generated_from: PlanSource = "ai",
    done_ids: set[str] = frozenset(),
    spend: list[SpendEntry] | None = None,
    photo_ideas: Iterable[PhotoIdea] = (),
) -> Plan:
    """Computes the full plan: exact budget, dated timeline, vendor bookings and tracking.

    Args:
        event: The user's inputs.
        skeleton: The plan skeleton (from Gemini, a default, or a saved event).
        today: Today's date in IST, used to move overdue items to today.
        generated_from: Whether the skeleton came from the AI or the default plan.
        done_ids: Ticked task and vendor ids; ids no longer in the plan are ignored.
        spend: Spend entries for saved events; None for guests (no tracking).
        photo_ideas: Ideas from uploaded photos, newest first.
    """
    budget = allocate(
        event.budget_inr, ensure_contingency(skeleton.budget_categories), event.guest_count, event.event_type
    )
    tasks = schedule_tasks(event.event_date, skeleton.tasks, today, done_ids)
    item_ids = [t.id for t in skeleton.tasks] + [vendor_item_id(v.category_key) for v in skeleton.vendors]
    return Plan(
        event=event,
        title=skeleton.title,
        summary=skeleton.summary,
        generated_from=generated_from,
        budget=budget,
        timeline=Timeline(
            tasks=tasks,
            short_notice=any(t.status == "compressed" for t in tasks),
            completion_pct=completion_pct(item_ids, done_ids),
        ),
        vendors=schedule_vendors(event.event_date, skeleton.vendors, today, done_ids),
        ideas=skeleton.ideas,
        photo_ideas=list(photo_ideas),
        tracking=None if spend is None else spend_tracking(budget.lines, spend),
    )
