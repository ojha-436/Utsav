"""Turn weighted budget categories into whole-rupee lines that sum exactly."""

from fractions import Fraction

from app.models import Budget, BudgetCategory, BudgetLine, EventType, PlanWarning
from app.planning.sanitize import CONTINGENCY_KEY

CONTINGENCY_MIN_PERCENT = 5
PER_GUEST_FLOOR = {"wedding": 1500, "birthday": 400, "community": 150}


def _largest_remainder(total: int, categories: list[BudgetCategory]) -> dict[str, int]:
    """Split `total` by weight; leftover rupees go to the largest fractions, earlier first on ties."""
    weight_sum = sum(c.weight for c in categories)
    exact = [Fraction(total * c.weight, weight_sum) for c in categories]
    floors = [int(e) for e in exact]
    leftover = total - sum(floors)
    by_remainder = sorted(range(len(categories)), key=lambda i: (-(exact[i] - floors[i]), i))
    for i in by_remainder[:leftover]:
        floors[i] += 1
    return {c.key: amount for c, amount in zip(categories, floors, strict=True)}


def allocate(total: int, categories: list[BudgetCategory], guest_count: int, event_type: EventType) -> Budget:
    contingency = next((c for c in categories if c.key == CONTINGENCY_KEY), None)
    if contingency is None:
        raise ValueError("categories must include a contingency line")

    floor = -(-total * CONTINGENCY_MIN_PERCENT // 100)
    exact_contingency = Fraction(total * contingency.weight, sum(c.weight for c in categories))
    if exact_contingency < floor:
        rest = [c for c in categories if c.key != CONTINGENCY_KEY]
        amounts = _largest_remainder(total - floor, rest) | {CONTINGENCY_KEY: floor}
    else:
        amounts = _largest_remainder(total, categories)

    lines = [
        BudgetLine(
            key=c.key,
            label=c.label,
            amount=amounts[c.key],
            percent=round(amounts[c.key] * 100 / total, 1),
            per_guest=round(amounts[c.key] / guest_count),
            essential=c.essential,
        )
        for c in categories
    ]
    per_guest = round(total / guest_count)
    warnings = []
    if total < PER_GUEST_FLOOR[event_type] * guest_count:
        warnings.append(
            PlanWarning(
                code="low_per_guest",
                message=(
                    f"₹{per_guest} per guest is tight for a {event_type}; consider fewer guests or a larger budget."
                ),
            )
        )
    return Budget(total=total, per_guest=per_guest, lines=lines, warnings=warnings)
