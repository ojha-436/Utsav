"""AI features: prompt → Gemini → sanitise, with graceful degradation."""
import json
import logging
import re
from collections import Counter
from datetime import date

from pydantic import BaseModel, ValidationError

from app.ai.client import AIClient
from app.ai.prompts import SYSTEM_PLANNER, photo_prompt, refine_prompt, skeleton_prompt, vendors_prompt
from app.errors import AIUnavailable
from app.models import EventInput, PhotoIdea, PlanSkeleton, PlanSource, SkeletonDraft, VendorItem, VendorResponse
from app.planning.defaults import default_skeleton
from app.planning.sanitize import SkeletonInvalid, sanitize_skeleton

log = logging.getLogger("utsav.ai")

VENDOR_FALLBACK_MESSAGE = "Couldn't find local vendors right now — use the checklist questions when you contact vendors."
MAX_VENDORS_PER_CATEGORY = 3
MAX_PHOTO_IDEAS = 5
_HEX = re.compile(r"#[0-9a-fA-F]{6}")


class PhotoIdeaDraft(BaseModel):
    title: str
    description: str
    palette: list[str]


class PhotoIdeasDraft(BaseModel):
    ideas: list[PhotoIdeaDraft]


def generate_skeleton(ai: AIClient, event: EventInput, today: date) -> tuple[PlanSkeleton, PlanSource]:
    try:
        draft = ai.structured(system=SYSTEM_PLANNER, prompt=skeleton_prompt(event, today), schema=SkeletonDraft)
        return sanitize_skeleton(draft), "ai"
    except (AIUnavailable, SkeletonInvalid) as exc:
        log.warning("serving default plan", extra={"reason": type(exc).__name__})
        return default_skeleton(event.event_type), "default"


def refine_skeleton(ai: AIClient, event: EventInput, skeleton: PlanSkeleton, instruction: str, today: date) -> PlanSkeleton:
    draft = ai.structured(system=SYSTEM_PLANNER, prompt=refine_prompt(event, skeleton, instruction, today), schema=SkeletonDraft)
    try:
        return sanitize_skeleton(draft)
    except SkeletonInvalid as exc:
        raise AIUnavailable("The AI returned an incomplete plan; please try again") from exc


def extract_json(text: str) -> dict:
    fenced = re.search(r"```json\s*(.*?)```", text, re.DOTALL)
    candidate = fenced.group(1) if fenced else text[text.find("{"): text.rfind("}") + 1]
    data = json.loads(candidate)  # JSONDecodeError is a ValueError
    if not isinstance(data, dict):
        raise ValueError("expected a JSON object")
    return data


def _vendor_item(raw: object, n_sources: int) -> VendorItem | None:
    if not isinstance(raw, dict):
        return None
    index = raw.get("source_index")
    try:
        return VendorItem(
            category_key=str(raw.get("category_key", "")),
            name=str(raw.get("name") or "")[:100],
            why=str(raw.get("why") or "")[:200],
            area=str(raw["area"])[:80] if raw.get("area") else None,
            source_index=index if isinstance(index, int) and 0 <= index < n_sources else None,
        )
    except ValidationError:
        return None


def find_vendors(ai: AIClient, event: EventInput, category_keys: list[str]) -> VendorResponse:
    try:
        grounded = ai.grounded(system=SYSTEM_PLANNER, prompt=vendors_prompt(event, category_keys))
        raw_items = extract_json(grounded.text).get("vendors")
    except (AIUnavailable, ValueError):
        return VendorResponse(items=[], sources=[], message=VENDOR_FALLBACK_MESSAGE)
    if not grounded.searched:  # names without a search behind them may be invented
        return VendorResponse(items=[], sources=[], message=VENDOR_FALLBACK_MESSAGE)

    wanted, per_category, items = set(category_keys), Counter(), []
    for raw in raw_items if isinstance(raw_items, list) else []:
        item = _vendor_item(raw, len(grounded.sources))
        if item and item.category_key in wanted and per_category[item.category_key] < MAX_VENDORS_PER_CATEGORY:
            per_category[item.category_key] += 1
            items.append(item)
    if not items:
        return VendorResponse(items=[], sources=[], message=VENDOR_FALLBACK_MESSAGE)
    return VendorResponse(items=items, sources=grounded.sources)


def photo_ideas(ai: AIClient, event: EventInput, image: bytes, mime: str) -> list[PhotoIdea]:
    draft = ai.vision(system=SYSTEM_PLANNER, prompt=photo_prompt(event), image=image, mime=mime, schema=PhotoIdeasDraft)
    ideas = []
    for d in draft.ideas:
        palette = [c.strip().lower() for c in d.palette if _HEX.fullmatch(c.strip())][:6]
        title, description = d.title.strip()[:80], d.description.strip()[:300]
        if palette and title and description:
            ideas.append(PhotoIdea(title=title, description=description, palette=palette))
        if len(ideas) == MAX_PHOTO_IDEAS:
            break
    if not ideas:
        raise AIUnavailable("Couldn't read ideas from that photo; try another one")
    return ideas
