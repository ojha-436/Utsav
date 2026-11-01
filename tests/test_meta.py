def test_healthz(client):
    r = client.get("/api/healthz")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_config_exposes_only_public_firebase_fields(client):
    r = client.get("/api/config")
    assert set(r.json()) == {"firebaseApiKey", "firebaseAuthDomain", "projectId"}
