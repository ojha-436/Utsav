"""In-memory token-bucket rate limiting (fine for a few Cloud Run instances)."""

import threading
import time
from collections.abc import Callable

from starlette.requests import Request

from app.errors import RateLimited

_MAX_KEYS = 10_000


class RateLimiter:
    """Allows `capacity` calls per `per_seconds` for each key, refilling continuously."""

    def __init__(self, capacity: int, per_seconds: float, clock: Callable[[], float] = time.monotonic) -> None:
        """Allows `capacity` requests per `per_seconds`; `clock` is injectable for tests."""
        self._capacity = capacity
        self._per_seconds = per_seconds
        self._refill_per_second = capacity / per_seconds
        self._clock = clock
        self._buckets: dict[str, tuple[float, float]] = {}  # key -> (tokens, last_seen)
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        """Takes one token for `key`. Raises RateLimited when none are left."""
        now = self._clock()
        with self._lock:
            if len(self._buckets) > _MAX_KEYS:
                self._buckets = {k: v for k, v in self._buckets.items() if now - v[1] < self._per_seconds}
            tokens, last = self._buckets.get(key, (self._capacity, now))
            tokens = min(self._capacity, tokens + (now - last) * self._refill_per_second)
            if tokens < 1:
                self._buckets[key] = (tokens, now)
                raise RateLimited("Too many requests; please wait a minute and try again")
            self._buckets[key] = (tokens - 1, now)


def client_ip(request: Request) -> str:
    """Cloud Run appends the real client IP as the last X-Forwarded-For entry."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"
