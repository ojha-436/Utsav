"""Runtime settings, read from environment variables."""

from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Runtime configuration, read from environment variables."""

    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash"
    gemini_fallback_model: str = "gemini-2.5-flash"
    gemini_location: str = "global"
    use_vertexai: bool = False
    gcp_project: str = ""
    firebase_api_key: str = ""
    firebase_auth_domain: str = ""
    store: Literal["memory", "firestore"] = "memory"
    max_body_bytes: int = 6_000_000
