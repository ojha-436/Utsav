"""FastAPI dependencies. Runtime objects live on app.state so tests can swap them."""

from datetime import UTC, date, datetime
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import Depends, Request

from app.ai.client import AIClient
from app.ratelimit import client_ip
from app.store import EventStore

IST = ZoneInfo("Asia/Kolkata")


def today_in_ist(now: datetime) -> date:
    """The calendar date in India at the given instant."""
    return now.astimezone(IST).date()


def get_today() -> date:
    """Users plan in India; the server runs in UTC."""
    return today_in_ist(datetime.now(UTC))


def get_now() -> datetime:
    """The current instant, timezone-aware (UTC)."""
    return datetime.now(UTC)


def get_ai(request: Request) -> AIClient:
    """The app's Gemini client (swapped for a fake in tests)."""
    ai: AIClient = request.app.state.ai
    return ai


def get_store(request: Request) -> EventStore:
    """The app's event store (in-memory in tests, Firestore in production)."""
    store: EventStore = request.app.state.store
    return store


def rate_limit_ai(request: Request) -> None:
    """Applies the per-IP limit for the open AI endpoints."""
    request.app.state.ai_limiter.check(client_ip(request))


# Annotated aliases keep route signatures short: `today: TodayDep`.
TodayDep = Annotated[date, Depends(get_today)]
NowDep = Annotated[datetime, Depends(get_now)]
AIDep = Annotated[AIClient, Depends(get_ai)]
StoreDep = Annotated[EventStore, Depends(get_store)]
