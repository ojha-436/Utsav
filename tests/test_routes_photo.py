from datetime import UTC, datetime

import pytest

from app.ai.service import PhotoIdeasDraft
from app.errors import AIUnavailable
from app.models import SpendEntry
from app.ratelimit import RateLimiter
from tests.factories import AUTH_U1, AUTH_U2, event_input, skeleton_dict
from tests.fakes import FakeAI

JPEG = b"\xff\xd8\xff\xe0" + b"0" * 64
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64
WEBP = b"RIFF\0\0\0\0WEBPVP8 " + b"0" * 64
IDEAS = PhotoIdeasDraft(ideas=[{"title": "Marigold arch", "description": "d", "palette": ["#f4a300"]}])


def save_event(c):
    return c.post("/api/events", json={"input": event_input(), "skeleton": skeleton_dict()}, headers=AUTH_U1).json()["id"]


def setup(make_client, n=1):
    ai = FakeAI(vision=[IDEAS] * n)
    c = make_client(ai=ai)
    return c, ai, save_event(c)


def upload(c, eid, data, ctype="image/jpeg", headers=AUTH_U1):
    return c.post(f"/api/events/{eid}/photo-ideas", files={"image": ("x.jpg", data, ctype)}, headers=headers)


@pytest.mark.parametrize("data,mime", [(JPEG, "image/jpeg"), (PNG, "image/png"), (WEBP, "image/webp")])
def test_accepts_by_magic_bytes(make_client, data, mime):
    c, ai, eid = setup(make_client)
    r = upload(c, eid, data)
    assert r.status_code == 200 and r.json()["plan"]["photo_ideas"][0]["title"] == "Marigold arch"
    assert ai.calls[-1][1]["mime"] == mime


def test_rejections(make_client):
    c, ai, eid = setup(make_client)
    assert upload(c, eid, JPEG, headers={}).status_code == 401
    assert upload(c, eid, JPEG, headers=AUTH_U2).status_code == 404
    assert upload(c, eid, b"GIF89a" + b"0" * 64).json()["error"]["code"] == "unsupported_media_type"
    assert upload(c, eid, b"\xff\xd8\xff" + b"0" * 5_000_000).status_code == 413
    assert ai.calls == []


def test_photo_rate_limit(make_client):
    c, _, eid = setup(make_client, n=6)
    assert [upload(c, eid, JPEG).status_code for _ in range(6)][-1] == 429


def test_keeps_newest_20(make_client):
    c, _, eid = setup(make_client, n=21)
    c.app.state.photo_limiter = RateLimiter(100, 60)
    for _ in range(21):
        r = upload(c, eid, JPEG)
    assert len(r.json()["plan"]["photo_ideas"]) == 20


def test_ai_failure_502(make_client):
    c = make_client(ai=FakeAI(vision=AIUnavailable("x")))
    eid = save_event(c)
    assert upload(c, eid, JPEG).status_code == 502



def test_photo_ideas_keep_spend_logged_during_the_upload(make_client):
    holder = {}
    entry = SpendEntry(id="s1", category_key="venue", amount=5000, at=datetime(2026, 11, 1, tzinfo=UTC))

    def read_photo_while_user_logs_spend(_kwargs):
        holder["store"].update("u1", holder["eid"], lambda rec: rec.spend.append(entry))
        return IDEAS

    c = make_client(ai=FakeAI(vision=read_photo_while_user_logs_spend))
    holder.update(store=c.app.state.store, eid=save_event(c))
    r = upload(c, holder["eid"], JPEG)
    assert r.status_code == 200 and [e["id"] for e in r.json()["spend"]] == ["s1"]
    assert len(r.json()["plan"]["photo_ideas"]) == 1
