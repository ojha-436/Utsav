from datetime import timedelta

import pytest
from pydantic import ValidationError

from app.errors import InvalidInput
from app.models import EventInput, PlanSkeleton, SkeletonDraft, validate_event_date
from tests.factories import TODAY, event_input, skeleton_dict


@pytest.mark.parametrize("field,value", [
    ("guest_count", 0), ("guest_count", 5001), ("budget_inr", 999), ("budget_inr", 100_000_001),
    ("city", "J"), ("city", "x" * 81), ("notes", "x" * 501), ("vibe", ["grand"] * 6),
    ("vibe", ["disco"]), ("event_type", "funeral"),
])
def test_event_input_rejects_out_of_bounds(field, value):
    with pytest.raises(ValidationError):
        EventInput(**event_input(**{field: value}))


def test_event_input_valid_and_forbids_extra():
    assert EventInput(**event_input()).city == "Jaipur"
    with pytest.raises(ValidationError):
        EventInput(**event_input(uid="u2"))


@pytest.mark.parametrize("delta,ok", [(0, False), (1, True), (1096, True), (1097, False)])
def test_validate_event_date_window(delta, ok):
    def call():
        validate_event_date(TODAY + timedelta(days=delta), TODAY)

    if ok:
        call()
    else:
        pytest.raises(InvalidInput, call)


def test_skeleton_bounds():
    PlanSkeleton(**skeleton_dict())
    for bad in (skeleton_dict(n_tasks=41), skeleton_dict(n_tasks=4)):
        with pytest.raises(ValidationError):
            PlanSkeleton(**bad)
    s = skeleton_dict()
    s["tasks"][0]["days_before"] = -31
    with pytest.raises(ValidationError):
        PlanSkeleton(**s)
    s = skeleton_dict()
    s["budget_categories"][0]["key"] = "Bad Key"
    with pytest.raises(ValidationError):
        PlanSkeleton(**s)


def test_draft_accepts_unbounded_values():
    s = skeleton_dict(n_tasks=50)
    s["budget_categories"][0]["weight"] = 250
    assert len(SkeletonDraft(**s).tasks) == 50
