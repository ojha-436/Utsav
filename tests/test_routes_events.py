from datetime import UTC, date, datetime

import pytest

from app.deps import get_today
from app.errors import NotFound
from app.routes.events import event_id_param
from tests.factories import AUTH_U1, AUTH_U2, TODAY, event_input, skeleton_dict


def create(c, headers=AUTH_U1, **inp):
    return c.post("/api/events", json={"input": event_input(**inp), "skeleton": skeleton_dict()}, headers=headers)


def test_requires_auth(client):
    assert client.get("/api/events").status_code == 401


def test_create_get_and_list(client):
    r = create(client)
    assert r.status_code == 201
    body = r.json()
    assert body["version"] == 1 and body["plan"]["tracking"] is not None
    assert client.get(f"/api/events/{body['id']}", headers=AUTH_U1).status_code == 200
    [summary] = client.get("/api/events", headers=AUTH_U1).json()
    assert set(summary) == {"id", "title", "event_type", "event_date", "updated_at"}


def test_create_rejects_today(client):
    assert create(client, event_date=str(TODAY)).status_code == 422


def test_create_keeps_default_source(client):
    r = client.post("/api/events", json={"input": event_input(), "skeleton": skeleton_dict(), "generated_from": "default"}, headers=AUTH_U1)
    assert r.json()["plan"]["generated_from"] == "default"


def test_cross_user_is_404(client):
    eid = create(client).json()["id"]
    for method in ("get", "delete"):
        assert getattr(client, method)(f"/api/events/{eid}", headers=AUTH_U2).status_code == 404
    assert client.put(f"/api/events/{eid}", json={"skeleton": skeleton_dict()}, headers=AUTH_U2).status_code == 404
    assert client.get("/api/events", headers=AUTH_U2).json() == []


def test_put_bumps_version_and_keeps_progress(client):
    eid = create(client).json()["id"]
    client.app.state.store.update("u1", eid, lambda rec: rec.progress.__setitem__("book-venue", datetime(2026, 11, 1, tzinfo=UTC)))
    r = client.put(f"/api/events/{eid}", json={"skeleton": skeleton_dict(title="Renamed")}, headers=AUTH_U1).json()
    assert r["version"] == 2 and r["plan"]["title"] == "Renamed"
    assert next(t for t in r["plan"]["timeline"]["tasks"] if t["id"] == "book-venue")["status"] == "done"


def test_put_changed_date_must_be_future(client):
    eid = create(client).json()["id"]
    body = {"input": event_input(event_date=str(TODAY)), "skeleton": skeleton_dict()}
    assert client.put(f"/api/events/{eid}", json=body, headers=AUTH_U1).status_code == 422


def test_get_after_event_date_passed(make_client):
    c = make_client()
    eid = create(c).json()["id"]
    c.app.dependency_overrides[get_today] = lambda: date(2027, 3, 1)
    assert c.get(f"/api/events/{eid}", headers=AUTH_U1).status_code == 200


def test_delete_and_bad_id(client):
    eid = create(client).json()["id"]
    assert client.delete(f"/api/events/{eid}", headers=AUTH_U1).status_code == 204
    assert client.get(f"/api/events/{eid}", headers=AUTH_U1).status_code == 404
    assert client.get("/api/events/bad.id!", headers=AUTH_U1).status_code == 404



@pytest.mark.parametrize("bad", ["__x__", "a_b", "a-b", "x" * 65, ""])
def test_event_id_rejects_ids_firestore_would_refuse(bad):
    with pytest.raises(NotFound):
        event_id_param(bad)
