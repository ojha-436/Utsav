"""Inspiration photo → decor ideas with colour palettes, on a saved event."""

from fastapi import APIRouter, File, Request, UploadFile

from app.ai.service import photo_ideas
from app.auth import UserDep
from app.deps import AIDep, StoreDep, TodayDep
from app.errors import PayloadTooLarge, UnsupportedMedia
from app.limits import MAX_IMAGE_BYTES, MAX_PHOTO_IDEAS_KEPT
from app.models import EventResponse
from app.routes.common import EventIdDep, to_response
from app.store import EventRecord

router = APIRouter(prefix="/api/events")


def sniff_image(data: bytes) -> str | None:
    """Image type from its magic bytes; the declared content type is never trusted."""
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


@router.post("/{event_id}/photo-ideas", response_model=EventResponse)
def add_photo_ideas(
    request: Request,
    event_id: EventIdDep,
    uid: UserDep,
    store: StoreDep,
    ai: AIDep,
    today: TodayDep,
    image: UploadFile = File(...),
) -> EventResponse:
    """Adds decor ideas from an uploaded inspiration photo (JPEG, PNG or WebP, at most 5 MB)."""
    # Limit and ownership are checked before the upload is read or Gemini is called.
    request.app.state.photo_limiter.check(uid)
    record = store.get(uid, event_id)
    data = image.file.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise PayloadTooLarge("Images must be 5 MB or smaller")
    mime = sniff_image(data)
    if mime is None:
        raise UnsupportedMedia("Upload a JPEG, PNG or WebP image")
    ideas = photo_ideas(ai, record.input, data, mime)

    def apply(current: EventRecord) -> None:  # re-read: the user may have changed things during the AI call
        current.photo_ideas = (ideas + current.photo_ideas)[:MAX_PHOTO_IDEAS_KEPT]

    return to_response(store.update(uid, event_id, apply), today)
