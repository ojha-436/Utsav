"""Progress and spend against the plan."""

from collections import defaultdict

from app.models import BudgetLine, SpendEntry, Tracking, TrackingLine


def completion_pct(item_ids: list[str], done_ids: set[str]) -> int:
    """Share of current items that are done. Ids no longer in the plan are ignored."""
    if not item_ids:
        return 0
    done = sum(1 for item_id in item_ids if item_id in done_ids)
    return round(100 * done / len(item_ids))


def spend_tracking(lines: list[BudgetLine], spend: list[SpendEntry]) -> Tracking:
    actual: dict[str, int] = defaultdict(int)
    for entry in spend:
        actual[entry.category_key] += entry.amount
    planned_keys = {line.key for line in lines}
    return Tracking(
        lines=[
            TrackingLine(
                key=line.key,
                label=line.label,
                planned=line.amount,
                actual=actual[line.key],
                variance=line.amount - actual[line.key],
            )
            for line in lines
        ],
        other_actual=sum(amount for key, amount in actual.items() if key not in planned_keys),
    )
