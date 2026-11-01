"""Application factory: wires settings, services, middleware and routes together."""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.auth import firebase_verifier
from app.config import Settings
from app.handlers import install_error_handlers
from app.limits import AI_REQUESTS_PER_WINDOW, PHOTO_UPLOADS_PER_WINDOW, RATE_WINDOW_SECONDS
from app.logs import configure_logging
from app.middleware import install_middleware
from app.ratelimit import RateLimiter
from app.routes import events, meta, pages, photos, plans, tracking
from app.wiring import build_ai, build_store


def create_app(settings: Settings | None = None) -> FastAPI:
    """Builds the FastAPI app. Tests pass safe settings; production reads the environment."""
    settings = settings or Settings()
    configure_logging()
    app = FastAPI(title="Utsav", docs_url=None, redoc_url=None, openapi_url=None)

    # Runtime services live on app.state so tests can swap them.
    app.state.settings = settings
    app.state.ai = build_ai(settings)
    app.state.store = build_store(settings)
    app.state.verify_token = firebase_verifier(settings.gcp_project)
    app.state.ai_limiter = RateLimiter(AI_REQUESTS_PER_WINDOW, RATE_WINDOW_SECONDS)
    app.state.photo_limiter = RateLimiter(PHOTO_UPLOADS_PER_WINDOW, RATE_WINDOW_SECONDS)

    install_error_handlers(app)
    install_middleware(app, settings.max_body_bytes)
    for module in (meta, plans, events, tracking, photos, pages):
        app.include_router(module.router)
    app.mount("/static", StaticFiles(directory=pages.STATIC_DIR), name="static")
    return app


app = create_app()
