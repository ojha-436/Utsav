"""Repair a Gemini skeleton draft into a valid PlanSkeleton.

The model is asked for well-formed output, but this module never trusts it:
it normalises ids, clamps numbers, drops duplicates and guarantees the
categories every later step relies on.
"""

import re
from typing import get_args

from app.models import (
    BudgetCategory,
    Idea,
    IdeaKind,
    PlanSkeleton,
    SkeletonDraft,
    Task,
    Vendor,
)

CONTINGENCY_KEY = "contingency"
OTHER_KEY = "other"

MAX_CATEGORIES = 12
MAX_TASKS = 40
MAX_VENDORS = 12
MAX_IDEAS = 10
MAX_QUESTIONS = 5
_IDEA_KINDS: dict[str, IdeaKind] = {kind: kind for kind in get_args(IdeaKind)}


class SkeletonInvalid(ValueError):
    """The draft is too thin to repair into a usable plan."""


def slugify(text: str, max_len: int = 40) -> str:
    """A lowercase, hyphenated id of at most `max_len` characters ("item" if nothing is left)."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:max_len].strip("-")
    return slug or "item"


def _cut(text: str, max_len: int) -> str:
    return text.strip()[:max_len].strip()


def ensure_contingency(categories: list[BudgetCategory]) -> list[BudgetCategory]:
    """Every plan keeps a contingency line; budget allocation depends on it."""
    if any(c.key == CONTINGENCY_KEY for c in categories):
        return categories
    return [*categories, BudgetCategory(key=CONTINGENCY_KEY, label="Contingency", weight=1, essential=True)]


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def _categories(draft: SkeletonDraft) -> list[BudgetCategory]:
    seen: set[str] = set()
    picked = []
    for c in draft.budget_categories:
        key = slugify(c.key or c.label)
        if key in seen:
            continue
        seen.add(key)
        picked.append((key, c))
        if len(picked) == MAX_CATEGORIES:
            break
    if len(picked) < 3:
        raise SkeletonInvalid("fewer than 3 budget categories")
    all_zero = all(c.weight <= 0 for _, c in picked)
    return [
        BudgetCategory(
            key=key,
            label=_cut(c.label, 60) or key.replace("-", " ").title(),
            weight=1 if all_zero else _clamp(c.weight, 1, 100),
            essential=c.essential,
            note=_cut(c.note, 160),
        )
        for key, c in picked
    ]


def _tasks(draft: SkeletonDraft, known: set[str]) -> list[Task]:
    seen: set[str] = set()
    tasks = []
    for t in draft.tasks:
        task_id, title = slugify(t.id or t.title), _cut(t.title, 100)
        if task_id in seen or not title:
            continue
        seen.add(task_id)
        key = slugify(t.category_key)
        tasks.append(
            Task(
                id=task_id,
                title=title,
                category_key=key if key in known else OTHER_KEY,
                days_before=_clamp(t.days_before, -30, 540),
            )
        )
        if len(tasks) == MAX_TASKS:
            break
    if len(tasks) < 5:
        raise SkeletonInvalid("fewer than 5 tasks")
    return tasks


def _vendors(draft: SkeletonDraft, known: set[str]) -> list[Vendor]:
    seen: set[str] = set()
    vendors = []
    for v in draft.vendors:
        key = slugify(v.category_key)
        key = key if key in known else OTHER_KEY
        role = _cut(v.role, 60)
        questions = [q for q in (_cut(q, 120) for q in v.questions_to_ask) if q][:MAX_QUESTIONS]
        if key in seen or not role or not questions:
            continue
        seen.add(key)
        vendors.append(
            Vendor(
                category_key=key,
                role=role,
                questions_to_ask=questions,
                book_by_days_before=_clamp(v.book_by_days_before, 0, 540),
            )
        )
        if len(vendors) == MAX_VENDORS:
            break
    return vendors


def _ideas(draft: SkeletonDraft) -> list[Idea]:
    ideas = []
    for i in draft.ideas:
        title, description = _cut(i.title, 80), _cut(i.description, 300)
        if not title or not description:
            continue
        kind = i.kind.strip().lower()
        ideas.append(Idea(title=title, description=description, kind=_IDEA_KINDS.get(kind, "theme")))
        if len(ideas) == MAX_IDEAS:
            break
    if len(ideas) < 3:
        raise SkeletonInvalid("fewer than 3 ideas")
    return ideas


def sanitize_skeleton(draft: SkeletonDraft) -> PlanSkeleton:
    """Repairs Gemini's draft into a valid PlanSkeleton.

    Normalises ids, clamps numbers, drops duplicates, remaps unknown categories to
    "other" and guarantees a contingency category.

    Raises:
        SkeletonInvalid: if too few categories, tasks or ideas are left to make a plan.
    """
    categories = _categories(draft)
    known = {c.key for c in categories}
    tasks = _tasks(draft, known)
    vendors = _vendors(draft, known)
    ideas = _ideas(draft)

    used = {t.category_key for t in tasks} | {v.category_key for v in vendors}
    if OTHER_KEY in used and OTHER_KEY not in known:
        categories.append(BudgetCategory(key=OTHER_KEY, label="Other", weight=1, essential=False))

    return PlanSkeleton(
        title=_cut(draft.title, 80) or "Your event plan",
        summary=_cut(draft.summary, 400),
        budget_categories=ensure_contingency(categories),
        tasks=tasks,
        vendors=vendors,
        ideas=ideas,
    )
