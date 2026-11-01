"""The only module that talks to Gemini.

Owns timeouts, retry, the fallback model, JSON validation with one repair
attempt, and extracting grounding sources. Prompts and user text are never
logged.
"""
import logging
import time
from dataclasses import dataclass, field
from typing import Protocol, TypeVar

import httpx
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel, ValidationError

from app.errors import AIUnavailable
from app.models import Source

try:  # google-genai accepts either httpx or its fork httpx2
    import httpx2

    _TIMEOUTS: tuple[type[Exception], ...] = (httpx.TimeoutException, httpx2.TimeoutException)
except ImportError:
    _TIMEOUTS = (httpx.TimeoutException,)

log = logging.getLogger("utsav.ai")
T = TypeVar("T", bound=BaseModel)


@dataclass
class GroundedText:
    text: str
    sources: list[Source] = field(default_factory=list)
    searched: bool = True  # False when the model answered without running Google Search


class AIClient(Protocol):
    def structured(self, *, system: str, prompt: str, schema: type[T], timeout_s: float = 30) -> T: ...

    def grounded(self, *, system: str, prompt: str, timeout_s: float = 45) -> GroundedText: ...

    def vision(self, *, system: str, prompt: str, image: bytes, mime: str, schema: type[T], timeout_s: float = 30) -> T: ...


class NullAI:
    """Used when no Gemini credentials are configured; every call degrades gracefully upstream."""

    def structured(self, **_):
        raise AIUnavailable("AI is not configured")

    def grounded(self, **_):
        raise AIUnavailable("AI is not configured")

    def vision(self, **_):
        raise AIUnavailable("AI is not configured")


class GeminiClient:
    def __init__(self, api_key: str, model: str, fallback_model: str, sdk=None, sleep=time.sleep):
        self._sdk = sdk or genai.Client(api_key=api_key)
        self._attempts = (model, model, fallback_model)
        self._sleep = sleep

    def structured(self, *, system: str, prompt: str, schema: type[T], timeout_s: float = 30) -> T:
        return self._json_call([prompt], self._config(system, timeout_s, schema=schema), schema)

    def vision(self, *, system: str, prompt: str, image: bytes, mime: str, schema: type[T], timeout_s: float = 30) -> T:
        contents = [types.Part.from_bytes(data=image, mime_type=mime), prompt]
        return self._json_call(contents, self._config(system, timeout_s, schema=schema), schema)

    def grounded(self, *, system: str, prompt: str, timeout_s: float = 45) -> GroundedText:
        tools = [types.Tool(google_search=types.GoogleSearch())]
        resp = self._generate([prompt], self._config(system, timeout_s, tools=tools))
        sources = _sources(resp)
        return GroundedText(text=resp.text or "", sources=sources, searched=bool(sources) or _ran_search(resp))

    @staticmethod
    def _config(system: str, timeout_s: float, schema=None, tools=None) -> types.GenerateContentConfig:
        return types.GenerateContentConfig(
            system_instruction=system,
            http_options=types.HttpOptions(timeout=int(timeout_s * 1000)),
            response_mime_type="application/json" if schema else None,
            response_schema=schema,
            tools=tools,
        )

    def _generate(self, contents: list, config: types.GenerateContentConfig):
        for attempt, model in enumerate(self._attempts):
            if attempt == 1:
                self._sleep(1.0)
            try:
                return self._sdk.models.generate_content(model=model, contents=contents, config=config)
            except genai_errors.APIError as exc:
                if exc.code != 429 and exc.code < 500:
                    raise AIUnavailable("The AI service rejected the request") from exc
                log.warning("gemini transient error", extra={"model": model, "status": exc.code})
            except _TIMEOUTS:
                log.warning("gemini timeout", extra={"model": model})
        raise AIUnavailable("The AI service is busy; please try again")

    def _json_call(self, contents: list, config: types.GenerateContentConfig, schema: type[T]) -> T:
        resp = self._generate(contents, config)
        try:
            return schema.model_validate_json(resp.text or "")
        except ValueError as exc:  # pydantic's ValidationError is a ValueError
            problem = str(exc)[:500]
        repair = f"Your previous output failed validation: {problem}. Return only corrected JSON."
        resp = self._generate([*contents, repair], config)
        try:
            return schema.model_validate_json(resp.text or "")
        except (ValidationError, ValueError) as exc:
            raise AIUnavailable("The AI returned an unusable answer") from exc


def _sources(resp) -> list[Source]:
    """Citation links come only from grounding metadata, never from model text."""
    try:
        chunks = resp.candidates[0].grounding_metadata.grounding_chunks or []
    except (AttributeError, IndexError, TypeError):
        return []
    sources = []
    for chunk in chunks:
        web = getattr(chunk, "web", None)
        uri = getattr(web, "uri", None) or ""
        if uri.startswith(("http://", "https://")):
            sources.append(Source(title=getattr(web, "title", None) or uri, uri=uri))
    return sources


def _ran_search(resp) -> bool:
    """Gemini sometimes omits source chunks even after searching; the queries still show it searched."""
    try:
        return bool(resp.candidates[0].grounding_metadata.web_search_queries)
    except (AttributeError, IndexError, TypeError):
        return False
