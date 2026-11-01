"""Health check and the public Firebase web config."""

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api")


@router.get("/healthz")
def healthz() -> dict:
    """Liveness check for Cloud Run."""
    return {"status": "ok"}


@router.get("/config")
def public_config(request: Request) -> dict:
    """Firebase web config. These values are public by design."""
    settings = request.app.state.settings
    return {
        "firebaseApiKey": settings.firebase_api_key,
        "firebaseAuthDomain": settings.firebase_auth_domain,
        "projectId": settings.gcp_project,
    }
