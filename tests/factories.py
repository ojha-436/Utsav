"""Shared test data. Plain dicts so tests can tweak them before validation."""
from datetime import date

TODAY = date(2026, 11, 1)

_CATEGORIES = [("venue", "Venue", 25), ("catering", "Catering", 35), ("decor", "Decor", 30), ("contingency", "Contingency", 10)]
_TASK_KEYS = ["venue", "catering", "decor"]


def event_input(**overrides) -> dict:
    base = {
        "event_type": "wedding",
        "event_date": "2027-02-14",
        "guest_count": 300,
        "budget_inr": 1_200_000,
        "city": "Jaipur",
        "vibe": ["traditional"],
        "notes": "",
    }
    return base | overrides


def skeleton_dict(n_tasks: int = 8, drop_contingency: bool = False, **overrides) -> dict:
    categories = [
        {"key": key, "label": label, "weight": weight, "essential": True, "note": ""}
        for key, label, weight in _CATEGORIES
        if not (drop_contingency and key == "contingency")
    ]
    tasks = [{"id": "book-venue", "title": "Book the venue", "category_key": "venue", "days_before": 180}]
    tasks += [
        {"id": f"task-{i}", "title": f"Task {i}", "category_key": _TASK_KEYS[i % 3], "days_before": max(7, 180 - i * 20)}
        for i in range(1, n_tasks)
    ]
    base = {
        "title": "Asha & Rohan's Wedding",
        "summary": "A traditional Jaipur wedding for 300 guests.",
        "budget_categories": categories,
        "tasks": tasks,
        "vendors": [
            {"category_key": "venue", "role": "Venue manager", "questions_to_ask": ["Is our date free?"], "book_by_days_before": 150},
            {"category_key": "catering", "role": "Caterer", "questions_to_ask": ["Can we book a tasting?", "Per-plate price?"], "book_by_days_before": 120},
        ],
        "ideas": [
            {"title": "Marigold mandap", "description": "Fresh marigold strings around the mandap.", "kind": "decor"},
            {"title": "Rajasthani thali", "description": "A live dal-baati-churma counter.", "kind": "food"},
            {"title": "Royal heritage", "description": "Haveli-inspired colours and lanterns.", "kind": "theme"},
        ],
    }
    return base | overrides
