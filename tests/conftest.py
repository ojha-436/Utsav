import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.factories import safe_settings


@pytest.fixture
def client():
    return TestClient(create_app(safe_settings()), raise_server_exceptions=False)
