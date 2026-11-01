import logging
import re
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from google import genai

from app.ai.client import AIClient, GeminiClient, NullAI
from app.auth import firebase_verifier
from app.config import Settings
from app.errors import AppError, PayloadTooLarge
from app.logs import configure_logging
from app.ratelimit import RateLimiter
from app.routes import meta, plans
from app.store import EventStore, FirestoreEventStore, InMemoryEventStore

log = logging.getLogger("utsav.http")
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self' https://www.gstatic.com https://apis.google.com; "
        "connect-src 'self' https://*.googleapis.com; frame-src https://*.firebaseapp.com https://accounts.google.com; "
        "img-src 'self' data: blob:; style-src 'self' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; "
        "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    ),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}
_REQUEST_ID = re.compile(r"^[A-Za-z0-9-]{8,64}$")
_HTTP_CODES = {404: "not_found", 405: "method_not_allowed"}


def error_response(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message}}, status_code=status)


def _install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    def app_error(_request: Request, exc: AppError):
        return error_response(exc.status, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    def validation_error(_request: Request, exc: RequestValidationError):
        first = exc.errors()[0]
        where = ".".join(str(part) for part in first["loc"] if part != "body")
        return error_response(422, "invalid_input", f"{where}: {first['msg']}" if where else first["msg"])

    @app.exception_handler(StarletteHTTPException)
    def http_error(_request: Request, exc: StarletteHTTPException):
        message = exc.detail if isinstance(exc.detail, str) else "Request failed"
        return error_response(exc.status_code, _HTTP_CODES.get(exc.status_code, "http_error"), message)


def _install_middleware(app: FastAPI, settings: Settings) -> None:
    @app.middleware("http")
    async def guard(request: Request, call_next):
        incoming = request.headers.get("x-request-id", "")
        request_id = incoming if _REQUEST_ID.match(incoming) else uuid.uuid4().hex
        started = time.perf_counter()
        length = request.headers.get("content-length", "")
        if length.isdigit() and int(length) > settings.max_body_bytes:
            exc = PayloadTooLarge("Request body is too large")
            response = error_response(exc.status, exc.code, exc.message)
        else:
            try:
                response = await call_next(request)
            except Exception:
                log.exception("unhandled error", extra={"request_id": request_id, "path": request.url.path})
                response = error_response(500, "internal", "Something went wrong.")
        response.headers.update(SECURITY_HEADERS)
        response.headers["X-Request-ID"] = request_id
        log.info("request", extra={
            "request_id": request_id, "method": request.method, "path": request.url.path,
            "status": response.status_code, "latency_ms": round((time.perf_counter() - started) * 1000, 1),
        })
        return response


def build_ai(settings: Settings) -> AIClient:
    """Vertex AI with the service account when enabled, else an API key, else no AI."""
    if settings.use_vertexai:
        sdk = genai.Client(vertexai=True, project=settings.gcp_project, location=settings.gemini_location)
        return GeminiClient("", settings.gemini_model, settings.gemini_fallback_model, sdk=sdk)
    if settings.gemini_api_key:
        return GeminiClient(settings.gemini_api_key, settings.gemini_model, settings.gemini_fallback_model)
    return NullAI()


def build_store(settings: Settings) -> EventStore:
    if settings.store == "firestore":
        from google.cloud import firestore

        return FirestoreEventStore(firestore.Client(project=settings.gcp_project or None))
    return InMemoryEventStore()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    configure_logging()
    app = FastAPI(title="Utsav", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = settings
    app.state.ai = build_ai(settings)
    app.state.store = build_store(settings)
    app.state.verify_token = firebase_verifier(settings.gcp_project)
    app.state.ai_limiter = RateLimiter(10, 60)
    app.state.photo_limiter = RateLimiter(5, 60)
    _install_error_handlers(app)
    _install_middleware(app, settings)
    app.include_router(meta.router)
    app.include_router(plans.router)
    _install_pages(app)
    return app


def _install_pages(app: FastAPI) -> None:
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def landing() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/app", include_in_schema=False)
    def planner() -> FileResponse:
        return FileResponse(STATIC_DIR / "app.html")


app = create_app()
