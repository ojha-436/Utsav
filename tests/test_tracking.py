from datetime import UTC, datetime

from app.models import BudgetLine, SpendEntry
from app.planning.tracking import completion_pct, spend_tracking


def entry(key, amount):
    return SpendEntry(id=f"{key}-{amount}", category_key=key, amount=amount, at=datetime(2026, 11, 1, tzinfo=UTC))


def test_completion_pct_ignores_orphans():
    assert completion_pct(["a", "b", "c", "vendor-x"], {"a", "b", "ghost"}) == 50
    assert completion_pct([], {"a"}) == 0
    assert completion_pct(["a", "b", "c"], {"a"}) == 33
    assert completion_pct(["a", "b", "c"], {"a", "b"}) == 67


def test_spend_variance_and_other_bucket():
    lines = [
        BudgetLine(key="venue", label="Venue", amount=300_000, percent=25.0, per_guest=1000, essential=True),
        BudgetLine(key="catering", label="Catering", amount=420_000, percent=35.0, per_guest=1400, essential=True),
    ]
    spend = [entry("venue", 100_000), entry("venue", 250_000), entry("sangeet", 40_000)]
    tr = spend_tracking(lines, spend)
    expected = [("venue", 350_000, -50_000), ("catering", 0, 420_000)]
    assert [(line.key, line.actual, line.variance) for line in tr.lines] == expected
    assert tr.other_actual == 40_000
