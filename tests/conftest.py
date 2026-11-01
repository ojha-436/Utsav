import pytest
from fastapi.testclient import TestClient

from app.deps import get_today
from app.main import create_app
from tests.factories import TODAY, safe_settings


@pytest.fixture
def make_client():
    def _make(ai=None, today=TODAY) -> TestClient:
        app = create_app(safe_settings())
        if ai is not None:
            app.state.ai = ai
        app.dependency_overrides[get_today] = lambda: today
        return TestClient(app, raise_server_exceptions=False)

    return _make


@pytest.fixture
def client(make_client):
    return make_client()
