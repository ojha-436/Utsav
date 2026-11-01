import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def safe_settings(**overrides) -> Settings:
    """Settings that can never reach a real model or database."""
    return Settings(store="memory", gemini_api_key="", use_vertexai=False, **overrides)


@pytest.fixture
def client():
    return TestClient(create_app(safe_settings()), raise_server_exceptions=False)
