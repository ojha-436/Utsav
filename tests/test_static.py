import re
from pathlib import Path


def test_pages_served(client):
    assert "Utsav" in client.get("/").text
    app_html = client.get("/app").text
    for hook in ['id="wizard"', 'id="dashboard"', 'id="refine-form"', 'role="tablist"', 'id="alert"']:
        assert hook in app_html


def test_static_assets_served(client):
    r = client.get("/static/js/main.js")
    assert r.status_code == 200 and "javascript" in r.headers["content-type"]


def test_no_html_injection_sinks_in_js():
    files = list(Path("static/js").rglob("*.js"))
    assert files
    for f in files:
        text = f.read_text()
        for sink in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write"):
            assert sink not in text, f"{sink} in {f}"


def test_no_inline_scripts():
    for f in Path("static").glob("*.html"):
        assert not re.search(r"<script(?![^>]*\bsrc=)[^>]*>", f.read_text()), f
