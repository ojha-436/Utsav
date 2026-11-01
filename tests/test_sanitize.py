import pytest

from app.models import SkeletonDraft
from app.planning.sanitize import SkeletonInvalid, sanitize_skeleton, slugify
from tests.factories import skeleton_dict


def test_slugify():
    assert slugify("Mehendi & Sangeet!") == "mehendi-sangeet"
    assert slugify("") == "item"
    assert len(slugify("a" * 100)) == 40


def test_duplicates_keep_first_and_vendor_dedupe():
    d = skeleton_dict()
    d["tasks"][1]["id"] = d["tasks"][0]["id"]
    d["vendors"].append({**d["vendors"][0], "role": "Second venue manager"})
    s = sanitize_skeleton(SkeletonDraft(**d))
    assert len({t.id for t in s.tasks}) == len(s.tasks) == 7
    assert [v.category_key for v in s.vendors].count(d["vendors"][0]["category_key"]) == 1


def test_unknown_category_moves_to_other():
    d = skeleton_dict()
    d["tasks"][0]["category_key"] = "fireworks"
    s = sanitize_skeleton(SkeletonDraft(**d))
    assert s.tasks[0].category_key == "other"
    assert any(c.key == "other" and c.weight == 1 for c in s.budget_categories)


def test_weights_and_contingency():
    d = skeleton_dict(drop_contingency=True)
    for c in d["budget_categories"]:
        c["weight"] = 0
    s = sanitize_skeleton(SkeletonDraft(**d))
    assert {c.weight for c in s.budget_categories} == {1}
    assert s.budget_categories[-1].key == "contingency"


def test_clamps_and_truncates():
    d = skeleton_dict(n_tasks=50)
    d["budget_categories"][0]["weight"] = 250
    d["tasks"][0]["days_before"] = 900
    d["tasks"][0]["title"] = "x" * 200
    s = sanitize_skeleton(SkeletonDraft(**d))
    assert s.budget_categories[0].weight == 100
    assert len(s.tasks) == 40
    assert s.tasks[0].days_before == 540
    assert len(s.tasks[0].title) == 100


def test_too_few_tasks_raises():
    with pytest.raises(SkeletonInvalid):
        sanitize_skeleton(SkeletonDraft(**skeleton_dict(n_tasks=3)))
