"""The two HTML pages. Their assets are served from /static."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

STATIC_DIR = Path(__file__).resolve().parents[2] / "static"

router = APIRouter(include_in_schema=False)


@router.get("/")
def landing() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@router.get("/app")
def planner() -> FileResponse:
    return FileResponse(STATIC_DIR / "app.html")
