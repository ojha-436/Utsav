from datetime import date, timedelta

import pytest

from app.models import EventInput, PlanSkeleton, SkeletonDraft
from app.planning.assemble import assemble_plan
from app.planning.defaults import default_skeleton
from app.planning.sanitize import sanitize_skeleton
from tests.factories import TODAY, event_input, skeleton_dict


@pytest.mark.parametrize("et", ["wedding", "birthday", "community"])
def test_default_skeleton_valid_consistent_and_idempotent(et):
    s = default_skeleton(et)
    keys = {c.key for c in s.budget_categories}
    assert "contingency" in keys
    assert all(t.category_key in keys for t in s.tasks) and all(v.category_key in keys for v in s.vendors)
    assert sanitize_skeleton(SkeletonDraft(**s.model_dump())) == s


def test_community_default_covers_permissions():
    assert any("permission" in t.title.lower() for t in default_skeleton("community").tasks)


def test_assemble_guest_plan():
    p = assemble_plan(EventInput(**event_input()), PlanSkeleton(**skeleton_dict()), TODAY)
    assert p.tracking is None and p.photo_ideas == [] and p.generated_from == "ai"
    assert sum(l.amount for l in p.budget.lines) == 1_200_000 and p.timeline.completion_pct == 0


def test_assemble_with_progress_and_spend():
    p = assemble_plan(EventInput(**event_input()), PlanSkeleton(**skeleton_dict()), TODAY,
                      done_ids={"book-venue", "vendor-venue", "ghost"}, spend=[])
    assert p.tracking is not None and p.timeline.completion_pct == 20  # 2 of 8 tasks + 2 vendors


def test_assemble_short_notice():
    e = EventInput(**event_input(event_date=str(TODAY + timedelta(days=3))))
    assert assemble_plan(e, PlanSkeleton(**skeleton_dict()), TODAY).timeline.short_notice


def test_assemble_after_event_passed():
    p = assemble_plan(EventInput(**event_input()), PlanSkeleton(**skeleton_dict()), date(2027, 3, 1))
    assert all(t.due >= date(2027, 3, 1) for t in p.timeline.tasks if t.status != "done")


def test_assemble_adds_contingency_when_client_skeleton_lacks_it():
    p = assemble_plan(EventInput(**event_input()), PlanSkeleton(**skeleton_dict(drop_contingency=True)), TODAY)
    assert p.budget.lines[-1].key == "contingency" and sum(l.amount for l in p.budget.lines) == 1_200_000
