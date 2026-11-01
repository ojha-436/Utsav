from datetime import date

from app.models import Task, Vendor
from app.planning.timeline import schedule_tasks, schedule_vendors

EVENT = date(2027, 2, 14)


def t(task_id, days):
    return Task(id=task_id, title=task_id, category_key="venue", days_before=days)


def test_due_dates_and_sorting():
    out = schedule_tasks(EVENT, [t("b", 30), t("a", 90), t("thanks", -7)], date(2026, 11, 1), set())
    assert [(x.id, x.due, x.status) for x in out] == [
        ("a", date(2026, 11, 16), "upcoming"),
        ("b", date(2027, 1, 15), "upcoming"),
        ("thanks", date(2027, 2, 21), "upcoming"),
    ]


def test_past_task_compressed_to_today_and_due_today():
    [x] = schedule_tasks(EVENT, [t("a", 90)], date(2026, 12, 1), set())
    assert (x.original_due, x.due, x.status) == (date(2026, 11, 16), date(2026, 12, 1), "compressed")
    assert schedule_tasks(EVENT, [t("a", 90)], date(2026, 11, 16), set())[0].status == "due_today"


def test_done_never_compressed():
    [x] = schedule_tasks(EVENT, [t("a", 90)], date(2026, 12, 1), {"a"})
    assert (x.status, x.due) == ("done", date(2026, 11, 16))


def test_stable_order_when_due_dates_tie():
    out = schedule_tasks(EVENT, [t("z", 120), t("y", 100)], date(2026, 12, 1), set())
    assert [x.id for x in out] == ["z", "y"]


def test_leap_day():
    assert schedule_tasks(date(2028, 3, 1), [t("a", 1)], date(2027, 1, 1), set())[0].due == date(2028, 2, 29)


def test_vendor_book_by():
    v = Vendor(category_key="catering", role="Caterer", questions_to_ask=["Tasting?"], book_by_days_before=120)
    [x] = schedule_vendors(EVENT, [v], date(2026, 11, 1), set())
    assert (x.id, x.original_book_by, x.book_by, x.status) == (
        "vendor-catering",
        date(2026, 10, 17),
        date(2026, 11, 1),
        "compressed",
    )
