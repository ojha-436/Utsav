import pytest
from fastapi import Depends
from fastapi.testclient import TestClient

from app.auth import optional_user, require_user
from app.main import create_app
from tests.factories import fake_verify, safe_settings


@pytest.fixture
def auth_app_client():
    app = create_app(safe_settings())
    app.state.verify_token = fake_verify

    @app.get("/opt")
    def opt(uid: str | None = Depends(optional_user)):
        return {"uid": uid}

    @app.get("/req")
    def req(uid: str = Depends(require_user)):
        return {"uid": uid}

    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize("headers,opt,req", [
    ({}, 200, 401),
    ({"Authorization": "Bearer u1"}, 200, 200),
    ({"Authorization": "Bearer nope"}, 401, 401),
    ({"Authorization": "Basic u1"}, 401, 401),
])
def test_auth_dependencies(auth_app_client, headers, opt, req):
    assert auth_app_client.get("/opt", headers=headers).status_code == opt
    assert auth_app_client.get("/req", headers=headers).status_code == req
    if req == 401:
        assert auth_app_client.get("/req", headers=headers).json()["error"]["code"] == "unauthorized"


def test_uid_comes_from_token(auth_app_client):
    assert auth_app_client.get("/req", headers={"Authorization": "Bearer u2"}).json() == {"uid": "u2"}
