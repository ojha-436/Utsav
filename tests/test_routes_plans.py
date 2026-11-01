from datetime import UTC, date, datetime

import pytest

from app.deps import today_in_ist
from app.errors import AIUnavailable
from app.models import SkeletonDraft
from tests.factories import TODAY, event_input, skeleton_dict
from tests.fakes import FakeAI


def test_today_is_ist():
    assert today_in_ist(datetime(2026, 11, 1, 20, 0, tzinfo=UTC)) == date(2026, 11, 2)


def gen(c, **kw):
    return c.post("/api/plans/generate", json={"input": event_input(**kw)})


def test_generate_ok(make_client):
    r = gen(make_client(ai=FakeAI(structured=SkeletonDraft(**skeleton_dict()))))
    assert r.status_code == 200 and r.json()["plan"]["generated_from"] == "ai"
    assert sum(l["amount"] for l in r.json()["plan"]["budget"]["lines"]) == 1_200_000


def test_generate_rejects_today(make_client):
    assert gen(make_client(), event_date=str(TODAY)).json()["error"]["code"] == "invalid_input"


def test_generate_default_when_ai_down(make_client):
    assert gen(make_client(ai=FakeAI(structured=AIUnavailable("x")))).json()["plan"]["generated_from"] == "default"


def refine(c, **body):
    return c.post("/api/plans/refine", json={"input": event_input(), "skeleton": skeleton_dict(), "instruction": "add a DJ"} | body)


def test_refine_ok_and_502(make_client):
    ok = refine(make_client(ai=FakeAI(structured=SkeletonDraft(**skeleton_dict(title="With DJ")))))
    assert ok.json()["skeleton"]["title"] == "With DJ"
    r = refine(make_client(ai=FakeAI(structured=AIUnavailable("x"))))
    assert r.status_code == 502 and r.json()["error"]["code"] == "ai_unavailable"


@pytest.mark.parametrize("instruction", ["", "x" * 301])
def test_refine_instruction_bounds(make_client, instruction):
    assert refine(make_client(), instruction=instruction).status_code == 422


def test_refine_rejects_tampered_skeleton(make_client):
    assert refine(make_client(), skeleton=skeleton_dict(n_tasks=41)).status_code == 422


def test_refine_allows_past_event(make_client):
    c = make_client(ai=FakeAI(structured=SkeletonDraft(**skeleton_dict())))
    assert refine(c, input=event_input(event_date="2026-10-01")).status_code == 200


def test_script_text_returned_verbatim(make_client):
    r = gen(make_client(ai=FakeAI(structured=SkeletonDraft(**skeleton_dict(title="<script>alert(1)</script>")))))
    assert r.json()["plan"]["title"] == "<script>alert(1)</script>"


def test_ai_endpoints_rate_limited(make_client):
    c = make_client()
    codes = [gen(c).status_code for _ in range(11)]
    assert codes[:10] == [200] * 10 and codes[10] == 429


def test_calendar_endpoint(client):
    r = client.post("/api/calendar.ics", json={"input": event_input(), "skeleton": skeleton_dict()})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/calendar")
    assert 'filename="utsav-plan.ics"' in r.headers["content-disposition"] and "BEGIN:VEVENT" in r.text


def test_calendar_rejects_tampered_skeleton(client):
    r = client.post("/api/calendar.ics", json={"input": event_input(), "skeleton": skeleton_dict(n_tasks=41)})
    assert r.status_code == 422
