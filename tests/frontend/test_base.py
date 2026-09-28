"""P19: base grafica comune (base.html, CSS di base, finestra di conferma, messaggi).

Controlla le regole di SCALETTA.md (P19) e di CLAUDE.md ("Pagine web"):
meta viewport, un solo script di pagina, risorse esterne solo da Google Fonts
(elenco in docs/prototipo/LEGGIMI.md), colori scritti a mano solo in
variables.css e uguali al prototipo, testo mai inserito come HTML, niente
alert / confirm / prompt.
Non serve MySQL. Comando (finché P6 non aggiunge il runner): python -m pytest tests/frontend
"""

import re
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from flask import flash, render_template

from app import create_app

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "app" / "static"
TEMPLATES = ROOT / "app" / "templates"
VARIABLES = STATIC / "css" / "base" / "variables.css"
PROTOTYPE_CSS = ROOT / "docs" / "prototipo" / "prototipo.css"

# Google Fonts: font Fredoka e Nunito, icone Material Symbols (docs/prototipo/LEGGIMI.md, "Risorse esterne")
ALLOWED_ORIGINS = {"https://fonts.googleapis.com", "https://fonts.gstatic.com"}

# Colori scritti a mano: #abc, #aabbcc, rgb(), hsl() e simili, nomi di colore
COLOR_LITERAL = re.compile(
    r"#[0-9a-fA-F]{3,8}\b"
    r"|\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch)\("
    r"|(?<![-\w])(?:white|black|red|green|blue|yellow|orange|purple|gray|grey|pink|brown)(?![-\w])"
)


@pytest.fixture
def app():
    return create_app("testing")


@pytest.fixture
def home(app):
    response = app.test_client().get("/")
    assert response.status_code == 200
    return response.get_data(as_text=True)


def _strip_css_comments(text):
    return re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)


def _root_variables(css):
    """Le variabili del primo blocco :root { ... } di un CSS, con gli spazi normalizzati."""
    block = re.search(r":root\s*\{(.*?)\n\}", _strip_css_comments(css), flags=re.DOTALL).group(1)
    return {
        name: " ".join(value.split())
        for name, value in re.findall(r"(--[\w-]+)\s*:\s*(.*?);", block, flags=re.DOTALL)
    }


def _templates():
    return sorted(TEMPLATES.rglob("*.html"))


def _template_text(path):
    """Il testo di un template senza i commenti Jinja {# ... #}, che non arrivano alla pagina."""
    return re.sub(r"\{#.*?#\}", "", path.read_text(encoding="utf-8"), flags=re.DOTALL)


def _strip_js_comments(code):
    """Il codice JS senza i commenti /* ... */ e senza le righe di commento // (non tocca "https://")."""
    code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
    return re.sub(r"^\s*//.*$", "", code, flags=re.MULTILINE)


# --- La pagina ---------------------------------------------------------------


def test_pagina_in_italiano_con_meta_viewport(home):
    assert '<html lang="it">' in home
    assert re.search(r'<meta name="viewport" content="width=device-width, initial-scale=1[^"]*">', home)
    assert "<title>Cinquecento</title>" in home


def test_al_massimo_uno_script_di_pagina(home):
    scripts = re.findall(r"<script\b[^>]*>", home)
    assert len(scripts) <= 1
    for tag in scripts:
        assert 'type="module"' in tag
        assert re.search(r'src="/static/js/pages/[\w-]+\.js"', tag), tag


def test_risorse_esterne_solo_da_google_fonts(home):
    urls = re.findall(r'(?:href|src)="(https?://[^"]+)"', home)
    assert urls, "base.html carica font e icone"
    for url in urls:
        parts = urlsplit(url)
        assert f"{parts.scheme}://{parts.netloc}" in ALLOWED_ORIGINS, url


def test_i_css_della_base_esistono(app, home):
    client = app.test_client()
    # base.html carica 11 CSS: 7 di P19, navbar.css e stats-panel.css (P40),
    # friends-panel.css e chat.css (P46); la home ne aggiunge altri suoi (P22),
    # che devono esistere anche loro
    base_css = re.findall(r"url_for\('static', filename='(css/[^']+)'\)", (TEMPLATES / "base.html").read_text(encoding="utf-8"))
    assert len(base_css) == 11
    paths = re.findall(r'href="(/static/[^"]+)"', home)
    css = [path for path in paths if path.startswith("/static/css/")]  # prima ci sono le icone (P42)
    assert css[:11] == [f"/static/{name}" for name in base_css]
    for path in paths:
        response = client.get(path)
        assert response.status_code == 200, path
        response.close()


def test_utente_non_collegato_e_csrf(home):
    # Contratto 1.5: attributi vuoti senza login, token CSRF sempre presente
    assert '<body data-user-id="" data-username="" data-avatar="">' in home
    token = re.search(r'<meta name="csrf-token" content="([^"]*)">', home)
    assert token and token.group(1)


def test_home_estende_la_base(home):
    assert 'class="page ' in home and 'data-page="home"' in home
    assert 'data-stato="ok"' in home


# --- Template e script -------------------------------------------------------


def test_pagine_estendono_base_senza_stile_ne_script_scritti_dentro():
    for path in _templates():
        text = _template_text(path)
        name = path.relative_to(TEMPLATES).as_posix()
        assert "<style" not in text, name
        assert not re.search(r"<script\b(?![^>]*\bsrc=)", text), f"{name}: script scritto nella pagina"
        assert not re.search(r"\sstyle=", text), f"{name}: attributo style"
        if name != "base.html" and not name.startswith("partials/"):
            assert '{% extends "base.html" %}' in text, name


def test_risorse_esterne_solo_in_base_html():
    # Risorse caricate dalla pagina (fogli di stile, script, immagini); i link normali
    # (<a href>, per esempio la licenza nei crediti, P40) sono ammessi
    for path in _templates():
        if path.name == "base.html":
            continue
        assert not re.search(r'(?:<link\b[^>]*\bhref|\bsrc)="https?://', _template_text(path)), path.name


def test_js_senza_html_ne_finestre_del_browser():
    files = sorted((STATIC / "js").rglob("*.js"))
    assert files
    for path in files:
        code = _strip_js_comments(path.read_text(encoding="utf-8"))
        for forbidden in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write"):
            assert forbidden not in code, f"{path.name}: {forbidden}"
        assert not re.search(r"(?<![\w.])(?:window\.)?(?:alert|confirm|prompt)\s*\(", code), path.name


# --- Colori ------------------------------------------------------------------


def test_colori_scritti_solo_in_variables_css():
    files = [p for p in sorted((STATIC / "css").rglob("*.css")) if p != VARIABLES]
    assert files
    for path in files:
        css = _strip_css_comments(path.read_text(encoding="utf-8"))
        found = COLOR_LITERAL.findall(css)
        assert not found, f"{path.relative_to(STATIC).as_posix()}: {found}"


def test_colori_uguali_al_prototipo():
    ours = _root_variables(VARIABLES.read_text(encoding="utf-8"))
    prototype = _root_variables(PROTOTYPE_CSS.read_text(encoding="utf-8"))
    assert prototype
    for name, value in prototype.items():
        assert ours.get(name) == value, name


# --- Messaggi del server -----------------------------------------------------


def test_messaggi_flash_come_testo(app):
    with app.test_request_context("/"):
        flash("<b>Benvenuto</b>", "success")
        flash("Password sbagliata", "error")
        flash("Accedi per continuare.", "info")
        flash("Senza categoria")
        html = render_template("partials/flash.html")
    assert "&lt;b&gt;Benvenuto&lt;/b&gt;" in html and "<b>" not in html
    kinds = re.findall(r'data-flash-kind="(\w+)"', html)
    assert kinds == ["success", "error", "info", "info"]
    assert html.count('role="alert"') == 1
    assert html.count('role="status"') == 3


def test_nessun_messaggio_nessun_contenitore(app):
    with app.test_request_context("/"):
        assert "data-flash" not in render_template("partials/flash.html")
