from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.errors import RateLimited
from app.main import create_app
from app.models import EventInput
from app.ratelimit import RateLimiter, client_ip
from tests.factories import safe_settings


def test_security_headers_and_request_id(client):
    for path in ["/api/healthz", "/api/nope", "/"]:
        h = client.get(path).headers
        assert h["x-content-type-options"] == "nosniff"
        assert "frame-ancestors 'none'" in h["content-security-policy"]
        assert h["referrer-policy"] == "strict-origin-when-cross-origin"
        assert h["x-request-id"]


def test_404_shape(client):
    assert client.get("/api/nope").json()["error"]["code"] == "not_found"


def test_validation_and_internal_error_shapes():
    app = create_app(safe_settings())

    @app.post("/_v")
    def v(body: EventInput):
        return {}

    @app.get("/_boom")
    def boom():
        raise RuntimeError("secret-detail")

    c = TestClient(app, raise_server_exceptions=False)
    assert c.post("/_v", json={}).json()["error"]["code"] == "invalid_input"
    r = c.get("/_boom")
    assert r.status_code == 500
    assert "secret-detail" not in r.text
    assert r.json()["error"]["code"] == "internal"
    assert r.headers["x-content-type-options"] == "nosniff"


def test_body_limit(client):
    r = client.post("/api/healthz", content=b"x", headers={"content-length": "6000001"})
    assert r.status_code == 413
    assert r.json()["error"]["code"] == "payload_too_large"


def test_rate_limiter_refills_per_key():
    now = [0.0]
    rl = RateLimiter(2, 60, clock=lambda: now[0])
    rl.check("a")
    rl.check("a")
    with pytest.raises(RateLimited):
        rl.check("a")
    rl.check("b")
    now[0] = 30.0
    rl.check("a")


def test_client_ip_uses_rightmost_forwarded_for():
    req = SimpleNamespace(headers={"x-forwarded-for": "6.6.6.6, 1.2.3.4"}, client=SimpleNamespace(host="9.9.9.9"))
    assert client_ip(req) == "1.2.3.4"


def test_request_log_has_no_body(client, capsys):
    client.post("/api/healthz", json={"notes": "SECRET-NOTE"})
    out = capsys.readouterr().out
    assert '"path": "/api/healthz"' in out
    assert "SECRET-NOTE" not in out


def test_chunked_body_over_limit_is_413():
    c = TestClient(create_app(safe_settings(max_body_bytes=1000)), raise_server_exceptions=False)

    def chunks():
        for _ in range(10):
            yield b"x" * 500

    r = c.post("/api/calendar.ics", content=chunks(), headers={"content-type": "application/json"})
    assert r.status_code == 413
    assert r.json()["error"]["code"] == "payload_too_large"
