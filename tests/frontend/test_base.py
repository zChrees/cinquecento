"""P19: base grafica comune (la pagina della SPA, base.html delle pagine di errore, CSS di base).

Controlla le regole di P19 e di CLAUDE.md ("Pagine web"):
meta viewport, un solo script, risorse esterne solo da Google Fonts (elenco in
docs/prototipo/LEGGIMI.md), colori scritti a mano solo in variables.css e uguali al
prototipo, testo mai inserito come HTML, niente alert / confirm / prompt.
Le pagine sono della SPA: la <head> comune è frontend/index.html, il codice è in
frontend/src/, e base.html serve solo alle pagine di errore (errors/404.html e
500.html). I messaggi del server (flash) li disegna FlashList.tsx: li provano
test_auth.py (forma) e test_pagine_accesso.py (nel browser, con il ruolo giusto).
Non serve MySQL.
"""

import re
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from app import create_app

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "app" / "static"
TEMPLATES = ROOT / "app" / "templates"
SPA_INDEX = ROOT / "frontend" / "index.html"
SPA_SRC = ROOT / "frontend" / "src"
VARIABLES = STATIC / "css" / "base" / "variables.css"
PROTOTYPE_CSS = ROOT / "docs" / "prototipo" / "prototipo.css"

# Google Fonts: font Fredoka e Nunito (docs/prototipo/LEGGIMI.md, "Risorse esterne"); le icone sono nel progetto (D40)
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
def spa():
    """frontend/index.html senza i commenti HTML <!-- ... -->, che non contano."""
    return re.sub(r"<!--.*?-->", "", SPA_INDEX.read_text(encoding="utf-8"), flags=re.DOTALL)


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
    """Il codice senza i commenti /* ... */ e senza le righe di commento // (non tocca "https://")."""
    code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
    return re.sub(r"^\s*//.*$", "", code, flags=re.MULTILINE)


def _sources():
    """I file TypeScript e React del frontend."""
    return sorted(path for path in SPA_SRC.rglob("*") if path.suffix in (".ts", ".tsx"))


# --- La pagina della SPA ---------------------------------------------------------


def test_pagina_in_italiano_con_meta_viewport(spa):
    assert '<html lang="it">' in spa
    assert re.search(r'<meta name="viewport" content="width=device-width, initial-scale=1[^"]*">', spa)
    assert "<title>Cinquecento</title>" in spa


def test_un_solo_script(spa):
    # Il punto di partenza di React; dopo il build Vite lo sostituisce con il file tradotto
    scripts = re.findall(r"<script\b[^>]*>", spa)
    assert scripts == ['<script type="module" src="/src/main.tsx">']


def test_risorse_esterne_solo_da_google_fonts(spa):
    urls = re.findall(r'(?:href|src)="(https?://[^"]+)"', spa)
    assert urls, "frontend/index.html carica i font"
    for url in urls:
        parts = urlsplit(url)
        assert f"{parts.scheme}://{parts.netloc}" in ALLOWED_ORIGINS, url


def test_i_css_della_spa_esistono(app, spa):
    client = app.test_client()
    paths = re.findall(r'href="(/static/[^"]+)"', spa)
    assert any(path.startswith("/static/css/base/") for path in paths)
    for path in paths:
        response = client.get(path)
        assert response.status_code == 200, path
        response.close()


def test_senza_login_nessun_utente_e_codice_csrf(app):
    # Al posto degli attributi data-user-* e del meta csrf-token di base.html (contratto
    # 1.5), la SPA prende utente e codice CSRF da GET /api/auth/session
    data = app.test_client().get("/api/auth/session").get_json()["data"]
    assert data["user"] is None and data["csrf_token"]


# --- base.html (solo le pagine di errore) ----------------------------------------


def test_base_ridotta_senza_script_ne_navbar():
    base = _template_text(TEMPLATES / "base.html")
    assert '<html lang="it">' in base and 'name="viewport"' in base
    assert "<script" not in base and "navbar" not in base and "include" not in base
    # Gli unici template rimasti sono base.html e le due pagine di errore
    names = [path.relative_to(TEMPLATES).as_posix() for path in _templates()]
    assert names == ["base.html", "errors/404.html", "errors/500.html"]


def test_i_css_di_base_html_esistono(app):
    client = app.test_client()
    for name in re.findall(r"filename='(css/[^']+)'", (TEMPLATES / "base.html").read_text(encoding="utf-8")):
        response = client.get(f"/static/{name}")
        assert response.status_code == 200, name
        response.close()


def test_pagine_estendono_base_senza_stile_ne_script_scritti_dentro():
    for path in _templates():
        text = _template_text(path)
        name = path.relative_to(TEMPLATES).as_posix()
        assert "<style" not in text, name
        assert not re.search(r"<script\b(?![^>]*\bsrc=)", text), f"{name}: script scritto nella pagina"
        assert not re.search(r"\sstyle=", text), f"{name}: attributo style"
        if name != "base.html":
            assert '{% extends "base.html" %}' in text, name


def test_risorse_esterne_solo_in_base_html_e_nella_spa():
    # Risorse caricate dalla pagina (fogli di stile, script, immagini); i link normali
    # (<a href>, per esempio la licenza nei crediti, P40) sono ammessi
    for path in _templates():
        if path.name == "base.html":
            continue
        assert not re.search(r'(?:<link\b[^>]*\bhref|\bsrc)="https?://', _template_text(path)), path.name
    for path in _sources():
        code = _strip_js_comments(path.read_text(encoding="utf-8"))
        assert not re.search(r"""(?:href|src)=\{?["'`]https?://(?!creativecommons\.org)""", code), path.name


# --- Il codice -------------------------------------------------------------------


def test_codice_senza_html_ne_finestre_del_browser():
    files = _sources()
    assert files
    for path in files:
        code = _strip_js_comments(path.read_text(encoding="utf-8"))
        for forbidden in ("dangerouslySetInnerHTML", "innerHTML", "outerHTML", "insertAdjacentHTML", "document.write"):
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
