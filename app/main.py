from fastapi import FastAPI

from app.config import Settings
from app.routes import meta


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(title="Utsav", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = settings
    app.include_router(meta.router)
    return app


app = create_app()
