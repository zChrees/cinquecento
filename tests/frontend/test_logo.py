"""P42: logo nella navbar e icona della scheda del browser.

Controlla il "Fatto quando" di SCALETTA.md (P42): il logo si vede nitido attorno
ai 40 px di altezza su telefono e computer e il tocco porta alla home; in più
l'icona della scheda (SVG, con le copie PNG) è collegata in base.html, è un SVG
valido e usa solo i colori della palette. Il controllo nel browser (Chrome o Edge
senza finestra, tests/browser.py) si salta se nessuno dei due è installato.
"""

import re
import struct
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from app import create_app
from tests.browser import Browser, find_browser, running_server

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "app" / "static"
IMG = STATIC / "img"
VARIABLES = STATIC / "css" / "base" / "variables.css"
ICONS = {
    "img/favicon.svg": ('rel="icon"', 'type="image/svg+xml"'),
    "img/favicon-32.png": ('rel="icon"', 'sizes="32x32"'),
    "img/apple-touch-icon.png": ('rel="apple-touch-icon"',),
}


@pytest.fixture
def app():
    return create_app("testing")


def _home(app):
    response = app.test_client().get("/")
    html = response.get_data(as_text=True)
    response.close()
    return html


def _png_size(path):
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", path.name
    return struct.unpack(">II", data[16:24])


# --- Icona della scheda --------------------------------------------------------------


def test_icone_collegate_in_base_html_e_servite(app):
    html = _home(app)
    client = app.test_client()
    for path, attrs in ICONS.items():
        link = re.search(rf'<link [^>]*href="/static/{re.escape(path)}"[^>]*>', html)
        assert link, path
        for attr in attrs:
            assert attr in link.group(0), (path, attr)
        response = client.get(f"/static/{path}")
        assert response.status_code == 200, path
        response.close()


def test_svg_valido_con_i_colori_della_palette():
    text = (IMG / "favicon.svg").read_text(encoding="utf-8")
    root = ET.fromstring(text)  # un SVG non valido (per esempio "--" in un commento) non si vede
    assert root.tag == "{http://www.w3.org/2000/svg}svg" and root.get("viewBox") == "0 0 32 32"
    palette = {value.lower() for value in re.findall(r"#[0-9a-fA-F]{6}\b", VARIABLES.read_text(encoding="utf-8"))}
    used = {value.lower() for value in re.findall(r"#[0-9a-fA-F]{6}\b", text)}
    assert used and used <= palette, used - palette


def test_copie_png_con_le_misure_giuste():
    assert _png_size(IMG / "favicon-32.png") == (32, 32)
    assert _png_size(IMG / "apple-touch-icon.png") == (180, 180)


# --- Logo nella navbar ---------------------------------------------------------------


def test_logo_porta_alla_home_con_un_nome_accessibile(app):
    html = _home(app)
    logo = re.search(r'<a class="logo" href="([^"]+)" aria-label="([^"]+)">', html)
    assert logo and logo.group(1) == "/"
    assert logo.group(2) == "Cinquecento, torna alla home"
    assert '<span class="logo__text">Cinque<b>cento</b></span>' in html


@pytest.mark.parametrize(("size", "height"), [((360, 640), (30, 44)), ((1280, 800), (40, 52))],
                         ids=["telefono", "computer"])
def test_logo_nel_browser(tmp_path, size, height):
    with running_server(create_app("testing")) as url:
        browser = Browser(find_browser(), tmp_path / "chrome")
        try:
            browser.open(f"{url}/auth/login", *size, "document.querySelector('.logo') !== null")
            box = browser.js("""(() => { const logo = document.querySelector('.logo');
              const text = document.querySelector('.logo__text'); const b = logo.getBoundingClientRect();
              return { h: b.height, l: b.left, r: b.right, w: innerWidth,
                       clipped: text.scrollWidth > text.clientWidth + 1 }; })()""")
            assert height[0] <= box["h"] <= height[1], box
            assert box["l"] >= 0 and box["r"] <= box["w"] and not box["clipped"], box
            # Il tocco porta alla home
            browser.click(".logo")
            browser.wait_js("location.pathname === '/' && document.readyState === 'complete'", "home dopo il logo")
        finally:
            browser.close()
