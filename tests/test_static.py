import re
from pathlib import Path

import pytest


def test_pages_served(client):
    assert "Utsav" in client.get("/").text
    app_html = client.get("/app").text
    for hook in ['id="wizard"', 'id="dashboard"', 'id="refine-form"', 'role="tablist"', 'id="alert"']:
        assert hook in app_html


def test_static_assets_served(client):
    r = client.get("/static/js/main.js")
    assert r.status_code == 200
    assert "javascript" in r.headers["content-type"]


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


def test_login_dialog_and_pinned_firebase_sdk():
    assert '<dialog id="login-dialog"' in Path("static/app.html").read_text()
    js = Path("static/js/auth.js").read_text()
    assert "https://www.gstatic.com/firebasejs/10.14.1/firebase-auth.js" in js


@pytest.mark.parametrize("page", ["static/index.html", "static/app.html"])
def test_pages_have_an_accessible_theme_toggle(page):
    html = Path(page).read_text()
    head = html[: html.index("</head>")]
    assert '<script src="/static/js/theme.js"></script>' in head  # runs before paint, so no flash of the wrong theme
    assert re.search(r'<button type="button" class="theme-toggle" data-theme-toggle aria-pressed="false"', html)
    assert 'name="color-scheme" content="light dark"' in head


def test_dark_theme_tokens_cover_every_colour_token():
    css = Path("static/css/app.css").read_text()
    light = css[css.index(":root {") : css.index("}", css.index(":root {"))]
    dark_start = css.index(':root[data-theme="dark"] {')
    dark = css[dark_start : css.index("}", dark_start)]
    colour_tokens = set(re.findall(r"(--[a-z0-9-]+):\s*#", light))
    assert colour_tokens
    assert colour_tokens <= set(re.findall(r"(--[a-z0-9-]+):", dark))
    assert "color-scheme: dark" in dark


def test_no_hard_coded_white_text():
    # Text colours must come from tokens so they flip with the theme.
    assert not re.search(r"(?<!-)color:\s*#fff", Path("static/css/app.css").read_text())
