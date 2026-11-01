"""Turn "N days before the event" into real dates and statuses."""

from datetime import date, timedelta

from app.models import ItemStatus, ScheduledTask, ScheduledVendor, Task, Vendor


def vendor_item_id(category_key: str) -> str:
    return f"vendor-{category_key}"


def _place(original: date, today: date, done: bool) -> tuple[date, ItemStatus]:
    """Displayed date and status. Open items that are already late move to today."""
    if done:
        return original, "done"
    if original < today:
        return today, "compressed"
    if original == today:
        return today, "due_today"
    return original, "upcoming"


def schedule_tasks(event_date: date, tasks: list[Task], today: date, done_ids: set[str]) -> list[ScheduledTask]:
    scheduled = []
    for task in tasks:
        original = event_date - timedelta(days=task.days_before)
        due, status = _place(original, today, task.id in done_ids)
        scheduled.append(
            ScheduledTask(
                id=task.id,
                title=task.title,
                category_key=task.category_key,
                original_due=original,
                due=due,
                status=status,
            )
        )
    return sorted(scheduled, key=lambda s: s.due)  # sorted() is stable: ties keep input order


def schedule_vendors(event_date: date, vendors: list[Vendor], today: date, done_ids: set[str]) -> list[ScheduledVendor]:
    scheduled = []
    for vendor in vendors:
        item_id = vendor_item_id(vendor.category_key)
        original = event_date - timedelta(days=vendor.book_by_days_before)
        book_by, status = _place(original, today, item_id in done_ids)
        scheduled.append(
            ScheduledVendor(
                id=item_id,
                category_key=vendor.category_key,
                role=vendor.role,
                questions_to_ask=vendor.questions_to_ask,
                original_book_by=original,
                book_by=book_by,
                status=status,
            )
        )
    return sorted(scheduled, key=lambda s: s.book_by)
