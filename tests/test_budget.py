import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.models import BudgetCategory
from app.planning.budget import allocate


def cats(*pairs):
    return [BudgetCategory(key=k, label=k.title(), weight=w, essential=True) for k, w in pairs]


def test_proportional_split_percent_and_per_guest():
    b = allocate(1_200_000, cats(("venue", 25), ("catering", 35), ("decor", 30), ("contingency", 10)), 300, "wedding")
    assert [line.amount for line in b.lines] == [300_000, 420_000, 360_000, 120_000]
    assert b.lines[0].percent == 25.0
    assert b.lines[0].per_guest == 1000
    assert b.per_guest == 4000


def test_largest_remainder_ties_go_to_earlier_categories():
    b = allocate(1002, cats(("a", 1), ("b", 1), ("c", 1), ("contingency", 1)), 2, "birthday")
    assert [line.amount for line in b.lines] == [251, 251, 250, 250]


def test_contingency_floor_is_five_percent_rounded_up():
    big = allocate(100_000, cats(("venue", 95), ("contingency", 1)), 50, "wedding")
    assert [line.amount for line in big.lines] == [95_000, 5_000]
    small = allocate(1001, cats(("venue", 99), ("contingency", 1)), 1, "birthday")
    assert [line.amount for line in small.lines] == [950, 51]


def test_missing_contingency_is_a_programming_error():
    with pytest.raises(ValueError):
        allocate(1000, cats(("venue", 1)), 1, "birthday")


@pytest.mark.parametrize(
    ("event_type", "ok_total"), [("wedding", 150_000), ("birthday", 40_000), ("community", 15_000)]
)
def test_low_per_guest_warning(event_type, ok_total):
    c = cats(("venue", 50), ("contingency", 50))
    assert allocate(ok_total, c, 100, event_type).warnings == []
    assert [w.code for w in allocate(ok_total - 1, c, 100, event_type).warnings] == ["low_per_guest"]


@settings(max_examples=200)
@given(
    total=st.integers(1000, 100_000_000),
    weights=st.lists(st.integers(1, 100), min_size=2, max_size=13),
    guests=st.integers(1, 5000),
)
def test_property_exact_sum_and_floor(total, weights, guests):
    c = cats(*[(f"c{i}", w) for i, w in enumerate(weights[:-1])], ("contingency", weights[-1]))
    lines = allocate(total, c, guests, "wedding").lines
    assert sum(line.amount for line in lines) == total
    assert all(line.amount >= 0 for line in lines)
    assert lines[-1].amount >= -(-total * 5 // 100)
