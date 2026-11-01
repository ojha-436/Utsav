"""Builds the runtime services (AI client, event store) from settings."""

from google import genai

from app.ai.client import AIClient, GeminiClient, NullAI
from app.config import Settings
from app.store import EventStore, FirestoreEventStore, InMemoryEventStore


def build_ai(settings: Settings) -> AIClient:
    """Vertex AI with the service account when enabled, else an API key, else no AI."""
    if settings.use_vertexai:
        sdk = genai.Client(vertexai=True, project=settings.gcp_project, location=settings.gemini_location)
        return GeminiClient("", settings.gemini_model, settings.gemini_fallback_model, sdk=sdk)
    if settings.gemini_api_key:
        return GeminiClient(settings.gemini_api_key, settings.gemini_model, settings.gemini_fallback_model)
    return NullAI()


def build_store(settings: Settings) -> EventStore:
    """Firestore in production; an in-memory store for local development and tests."""
    if settings.store == "firestore":
        from google.cloud import firestore  # imported lazily so tests never need Google credentials

        return FirestoreEventStore(firestore.Client(project=settings.gcp_project or None))
    return InMemoryEventStore()
