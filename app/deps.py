"""FastAPI dependencies. Runtime objects live on app.state so tests can swap them."""
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from fastapi import Request

from app.ai.client import AIClient
from app.ratelimit import client_ip

IST = ZoneInfo("Asia/Kolkata")


def today_in_ist(now: datetime) -> date:
    return now.astimezone(IST).date()


def get_today() -> date:
    """Users plan in India; the server runs in UTC."""
    return today_in_ist(datetime.now(UTC))


def get_now() -> datetime:
    return datetime.now(UTC)


def get_ai(request: Request) -> AIClient:
    return request.app.state.ai


def rate_limit_ai(request: Request) -> None:
    request.app.state.ai_limiter.check(client_ip(request))
