from types import SimpleNamespace

import httpx
import pytest
from google.auth import exceptions as auth_exceptions
from google.genai import errors as genai_errors
from pydantic import BaseModel

from app.ai.client import GeminiClient, NullAI
from app.errors import AIUnavailable
from app.models import Source


class FakeModels:
    def __init__(self, script):
        self.script, self.calls = list(script), []

    def generate_content(self, **kw):
        self.calls.append(kw)
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def resp(text, chunks=None):
    return SimpleNamespace(
        text=text, candidates=[SimpleNamespace(grounding_metadata=SimpleNamespace(grounding_chunks=chunks))]
    )


def web(uri, title):
    return SimpleNamespace(web=SimpleNamespace(uri=uri, title=title))


def err(code):
    return genai_errors.APIError(code, {"error": {"code": code, "message": "x", "status": "X"}})


class Out(BaseModel):
    n: int


def make(*script):
    m = FakeModels(script)
    return GeminiClient("k", "primary", "fallback", sdk=SimpleNamespace(models=m), sleep=lambda s: None), m


def test_structured_success():
    c, m = make(resp('{"n": 1}'))
    assert c.structured(system="s", prompt="p", schema=Out) == Out(n=1)
    assert m.calls[0]["model"] == "primary"


def test_retry_then_fallback():
    c, m = make(err(503), err(429), resp('{"n": 2}'))
    assert c.structured(system="s", prompt="p", schema=Out).n == 2
    assert [k["model"] for k in m.calls] == ["primary", "primary", "fallback"]


def test_exhausted_or_client_error_raises():
    with pytest.raises(AIUnavailable):
        make(err(503), err(503), err(503))[0].structured(system="s", prompt="p", schema=Out)
    c, m = make(err(400))
    with pytest.raises(AIUnavailable):
        c.structured(system="s", prompt="p", schema=Out)
    assert len(m.calls) == 1


def test_timeout_is_retried():
    assert make(httpx.TimeoutException("t"), resp('{"n": 1}'))[0].structured(system="s", prompt="p", schema=Out).n == 1


def test_repair_once():
    c, m = make(resp("not json"), resp('{"n": 3}'))
    assert c.structured(system="s", prompt="p", schema=Out).n == 3
    assert "failed validation" in str(m.calls[1]["contents"])
    with pytest.raises(AIUnavailable):
        make(resp("{}"), resp("nope"))[0].structured(system="s", prompt="p", schema=Out)


def test_grounded_sources_only_from_metadata():
    c, m = make(
        resp(
            "see https://evil.example",
            [web("https://a.in", "A"), web("javascript:x", "bad"), SimpleNamespace(web=None)],
        )
    )
    g = c.grounded(system="s", prompt="p")
    assert g.sources == [Source(title="A", uri="https://a.in")]
    assert m.calls[0]["config"].tools[0].google_search is not None
    assert make(SimpleNamespace(text="t", candidates=[]))[0].grounded(system="s", prompt="p").sources == []


def test_vision_sends_image_part():
    c, m = make(resp('{"n": 4}'))
    c.vision(system="s", prompt="p", image=b"img", mime="image/png", schema=Out)
    assert any(getattr(getattr(p, "inline_data", None), "data", None) == b"img" for p in m.calls[0]["contents"])


def test_null_ai_raises():
    with pytest.raises(AIUnavailable):
        NullAI().structured(system="s", prompt="p", schema=Out)


def test_grounded_reports_whether_search_ran():
    with_queries = SimpleNamespace(
        text="t",
        candidates=[
            SimpleNamespace(
                grounding_metadata=SimpleNamespace(grounding_chunks=None, web_search_queries=["caterers in Jaipur"])
            )
        ],
    )
    assert make(with_queries)[0].grounded(system="s", prompt="p").searched is True
    assert make(resp("t", [web("https://a.in", "A")]))[0].grounded(system="s", prompt="p").searched is True
    assert make(SimpleNamespace(text="t", candidates=[]))[0].grounded(system="s", prompt="p").searched is False


@pytest.mark.parametrize(
    "exc",
    [
        httpx.ConnectError("down"),
        httpx.RemoteProtocolError("reset"),
        auth_exceptions.RefreshError("token refresh failed"),
    ],
)
def test_transport_and_auth_errors_are_transient(exc):
    assert make(exc, resp('{"n": 5}'))[0].structured(system="s", prompt="p", schema=Out).n == 5
    with pytest.raises(AIUnavailable):
        make(exc, exc, exc)[0].structured(system="s", prompt="p", schema=Out)
