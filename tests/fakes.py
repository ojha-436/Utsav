"""Test doubles for the AI boundary."""
from app.errors import AIUnavailable


class FakeAI:
    """Stands in for GeminiClient. Each slot is a value, an Exception to raise,
    or a list consumed one item per call. Records (method, kwargs) per call."""

    def __init__(self, structured=None, grounded=None, vision=None):
        self._slots = {"structured": structured, "grounded": grounded, "vision": vision}
        self.calls: list[tuple[str, dict]] = []

    def _next(self, method: str, kwargs: dict):
        self.calls.append((method, kwargs))
        slot = self._slots[method]
        item = slot.pop(0) if isinstance(slot, list) else slot
        if item is None:
            raise AIUnavailable(f"FakeAI.{method} not scripted")
        if isinstance(item, Exception):
            raise item
        return item

    def structured(self, **kwargs):
        return self._next("structured", kwargs)

    def grounded(self, **kwargs):
        return self._next("grounded", kwargs)

    def vision(self, **kwargs):
        return self._next("vision", kwargs)
