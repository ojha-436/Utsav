from tests.factories import AUTH_U1, AUTH_U2, event_input, skeleton_dict


def new_event(c):
    return c.post("/api/events", json={"input": event_input(), "skeleton": skeleton_dict()}, headers=AUTH_U1).json()[
        "id"
    ]


def toggle(c, eid, tid, done, headers=AUTH_U1):
    return c.patch(f"/api/events/{eid}/tasks/{tid}", json={"done": done}, headers=headers)


def test_toggle_task_and_vendor(client):
    eid = new_event(client)
    assert toggle(client, eid, "book-venue", True).json()["plan"]["timeline"]["completion_pct"] == 10
    assert toggle(client, eid, "vendor-catering", True).json()["plan"]["timeline"]["completion_pct"] == 20
    assert toggle(client, eid, "book-venue", False).json()["plan"]["timeline"]["completion_pct"] == 10
    assert toggle(client, eid, "nope", True).status_code == 404


def test_toggle_requires_owner(client):
    eid = new_event(client)
    assert toggle(client, eid, "book-venue", True, headers=AUTH_U2).status_code == 404
    assert toggle(client, eid, "book-venue", True, headers={}).status_code == 401


def test_spend_add_bounds_and_delete(client):
    eid = new_event(client)
    r = client.post(
        f"/api/events/{eid}/spend", json={"category_key": "venue", "amount": 50_000, "note": "advance"}, headers=AUTH_U1
    )
    assert r.status_code == 201
    assert next(line for line in r.json()["plan"]["tracking"]["lines"] if line["key"] == "venue")["actual"] == 50_000
    [entry] = r.json()["spend"]
    assert entry["note"] == "advance"
    assert entry["amount"] == 50_000
    for bad in (
        {"category_key": "venue", "amount": 0},
        {"category_key": "venue", "amount": 100_000_001},
        {"category_key": "yacht", "amount": 5},
    ):
        assert client.post(f"/api/events/{eid}/spend", json=bad, headers=AUTH_U1).status_code == 422
    deleted = client.delete(f"/api/events/{eid}/spend/{entry['id']}", headers=AUTH_U1).json()
    assert deleted["plan"]["tracking"]["lines"][0]["actual"] == 0
    assert deleted["spend"] == []
    assert client.delete(f"/api/events/{eid}/spend/{entry['id']}", headers=AUTH_U1).status_code == 404


def test_spend_rolls_into_other_after_category_removed(client):
    eid = new_event(client)
    client.post(f"/api/events/{eid}/spend", json={"category_key": "decor", "amount": 7_000}, headers=AUTH_U1)
    sk = skeleton_dict()
    sk["budget_categories"] = [c for c in sk["budget_categories"] if c["key"] != "decor"]
    for t in sk["tasks"]:
        if t["category_key"] == "decor":
            t["category_key"] = "venue"
    r = client.put(f"/api/events/{eid}", json={"skeleton": sk}, headers=AUTH_U1).json()
    assert r["plan"]["tracking"]["other_actual"] == 7_000


def test_refine_dropping_task_ignores_orphan_progress(client):
    eid = new_event(client)
    toggle(client, eid, "book-venue", True)
    sk = skeleton_dict()
    sk["tasks"] = [t for t in sk["tasks"] if t["id"] != "book-venue"]
    r = client.put(f"/api/events/{eid}", json={"skeleton": sk}, headers=AUTH_U1)
    assert r.status_code == 200
    assert r.json()["plan"]["timeline"]["completion_pct"] == 0
