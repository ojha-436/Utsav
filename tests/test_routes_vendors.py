import json
from datetime import UTC, datetime, timedelta

import pytest

from app.ai.client import GroundedText
from app.ai.service import VENDOR_FALLBACK_MESSAGE
from app.deps import get_now
from app.errors import AIUnavailable
from app.models import Source
from tests.factories import AUTH_U1, AUTH_U2, event_input, save_event, skeleton_dict
from tests.fakes import FakeAI

VENDOR = {"category_key": "catering", "name": "Spice Route", "why": "Rajasthani thali", "source_index": 0}
VJSON = "```json\n" + json.dumps({"vendors": [VENDOR]}) + "\n```"


def vend(c, headers=None, **kw):
    return c.post(
        "/api/vendors", json={"input": event_input(), "category_keys": ["catering"]} | kw, headers=headers or {}
    )


def grounded_ai(n=5):
    return FakeAI(grounded=[GroundedText(VJSON, [Source(title="A", uri="https://a.in")])] * n)


def test_guest_vendors(make_client):
    r = vend(make_client(ai=grounded_ai())).json()
    assert r["items"][0]["name"] == "Spice Route"
    assert r["sources"][0]["uri"] == "https://a.in"


def test_vendor_failure_message(make_client):
    assert vend(make_client(ai=FakeAI(grounded=AIUnavailable("x")))).json()["message"] == VENDOR_FALLBACK_MESSAGE


@pytest.mark.parametrize("keys", [[], ["a", "b", "c", "d", "e"]])
def test_category_bounds(client, keys):
    assert vend(client, category_keys=keys).status_code == 422


def test_cache_within_24h(make_client):
    ai = grounded_ai()
    c = make_client(ai=ai)
    eid = save_event(c)
    t = [datetime(2026, 11, 1, 10, tzinfo=UTC)]
    c.app.dependency_overrides[get_now] = lambda: t[0]
    vend(c, AUTH_U1, event_id=eid)
    t[0] += timedelta(hours=23)
    assert vend(c, AUTH_U1, event_id=eid).json()["items"][0]["name"] == "Spice Route"
    assert len(ai.calls) == 1
    t[0] += timedelta(hours=2)
    vend(c, AUTH_U1, event_id=eid)
    assert len(ai.calls) == 2


def test_cache_not_written_on_failure(make_client):
    ai = FakeAI(grounded=[AIUnavailable("x"), GroundedText(VJSON, [])])
    c = make_client(ai=ai)
    eid = save_event(c)
    assert vend(c, AUTH_U1, event_id=eid).json()["items"] == []
    assert vend(c, AUTH_U1, event_id=eid).json()["items"][0]["name"] == "Spice Route"
    assert len(ai.calls) == 2


def test_cache_cleared_when_event_input_changes(make_client):
    ai = grounded_ai()
    c = make_client(ai=ai)
    eid = save_event(c)
    vend(c, AUTH_U1, event_id=eid)
    c.put(
        f"/api/events/{eid}", json={"input": event_input(city="Udaipur"), "skeleton": skeleton_dict()}, headers=AUTH_U1
    )
    vend(c, AUTH_U1, event_id=eid, input=event_input(city="Udaipur"))
    assert len(ai.calls) == 2


def test_event_id_access(make_client):
    c = make_client(ai=grounded_ai())
    eid = save_event(c)
    assert vend(c, event_id=eid).status_code == 401
    assert vend(c, AUTH_U2, event_id=eid).status_code == 404


def test_vendor_cache_write_keeps_changes_made_during_the_search(make_client):
    holder = {}

    def search_while_user_ticks(_kwargs):
        holder["store"].update(
            "u1", holder["eid"], lambda rec: rec.progress.__setitem__("book-venue", datetime(2026, 11, 1, tzinfo=UTC))
        )
        return GroundedText(VJSON, [Source(title="A", uri="https://a.in")])

    c = make_client(ai=FakeAI(grounded=search_while_user_ticks))
    holder.update(store=c.app.state.store, eid=save_event(c))
    assert vend(c, AUTH_U1, event_id=holder["eid"]).json()["items"]
    record = c.app.state.store.get("u1", holder["eid"])
    assert "book-venue" in record.progress
    assert record.vendor_cache is not None
