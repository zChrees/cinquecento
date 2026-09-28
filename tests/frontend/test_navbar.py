"""P40: navbar, pannello statistiche, finestra "Accedi o registrati", immagini delle carte.

Controlla il "Fatto quando" di SCALETTA.md (P40): la navbar ha avatar, nome del
gioco e pulsante amici; ogni pulsante con sola icona ha un'etichetta accessibile;
il pannello statistiche ha i dati finti, Impostazioni, Esci e i crediti delle
immagini (D37). Controlla anche che le immagini di app/static/img/cards-bg/
siano quelle del prototipo e che i file JS importati esistano.
Non serve MySQL: l'utente con il login è finto, passato direttamente al template.
"""

import hashlib
import json
import re
from pathlib import Path

import pytest
from flask import render_template

from app import create_app

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "app" / "static"
CARDS = STATIC / "img" / "cards-bg"
PROTOTYPE_IMG = ROOT / "docs" / "prototipo" / "img"
SUITS = ("bastoni", "coppe", "denari", "spade")


class FakeUser:
    """Utente con il login, con i nomi che base.html e la navbar leggono (P16)."""

    is_authenticated = True

    def __init__(self, username, avatar=None):
        self.username = username
        self.avatar = avatar

    def get_id(self):
        return "7"


@pytest.fixture
def app():
    return create_app("testing")


@pytest.fixture
def guest_home(app):
    response = app.test_client().get("/")
    assert response.status_code == 200
    return response.get_data(as_text=True)


def _render_logged_in(app, username):
    with app.test_request_context("/"):
        return render_template("main/index.html", current_user=FakeUser(username))


@pytest.fixture
def user_home(app):
    return _render_logged_in(app, "mario")


def _navbar(html):
    return re.search(r'<header class="navbar".*?</header>', html, flags=re.DOTALL).group(0)


def _stats_dialog(html):
    return re.search(r'<dialog class="sheet" id="stats".*?</dialog>', html, flags=re.DOTALL).group(0)


def _buttons(html):
    return re.findall(r"<button\b[^>]*>.*?</button>", html, flags=re.DOTALL)


def _has_accessible_name(button):
    """Un pulsante ha un nome se ha aria-label oppure testo che non sia solo icone nascoste."""
    if re.search(r'\baria-label="[^"]+"', button):
        return True
    inner = re.sub(r"<span[^>]*aria-hidden=\"true\"[^>]*>.*?</span>", "", button, flags=re.DOTALL)
    return bool(re.sub(r"<[^>]+>", "", inner).strip())


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --- Navbar ------------------------------------------------------------------


@pytest.mark.parametrize("fixture", ["guest_home", "user_home"])
def test_navbar_con_avatar_nome_e_amici(request, fixture):
    html = request.getfixturevalue(fixture)
    assert html.count('data-part="navbar"') == 1
    navbar = _navbar(html)
    assert 'class="navbar__account' in navbar
    assert 'class="avatar"' in navbar
    assert "Cinque<b>cento</b>" in navbar
    assert 'aria-label="Cinquecento, torna alla home"' in navbar
    assert 'class="navbar__friends' in navbar
    # La navbar viene prima del contenuto della pagina
    assert html.index('data-part="navbar"') < html.index('<main class="page')


@pytest.mark.parametrize("fixture", ["guest_home", "user_home"])
def test_ogni_pulsante_ha_un_nome_accessibile(request, fixture):
    html = request.getfixturevalue(fixture)
    buttons = _buttons(_navbar(html))
    if 'id="stats"' in html:
        buttons += _buttons(_stats_dialog(html))
    assert len(buttons) >= 2
    for button in buttons:
        assert _has_accessible_name(button), button


def test_senza_login_avatar_e_amici_aprono_la_finestra_di_accesso(guest_home):
    navbar = _navbar(guest_home)
    assert navbar.count("data-login-prompt") == 2
    assert 'aria-label="Accedi o registrati"' in navbar
    assert "data-open-stats" not in navbar
    # Senza login non c'è il pannello statistiche
    assert 'id="stats"' not in guest_home


def test_con_login_avatar_con_iniziale_e_pannello_statistiche(user_home):
    navbar = _navbar(user_home)
    assert "data-login-prompt" not in navbar
    assert "data-open-stats" in navbar and 'aria-controls="stats"' in navbar
    assert re.search(r'<span class="avatar" aria-hidden="true">M</span>', navbar)
    assert '<span class="navbar__label">mario</span>' in navbar
    assert user_home.count('id="stats"') == 1


def test_nome_utente_inserito_come_testo(app):
    html = _render_logged_in(app, "<b>x")
    assert "<b>x" not in html
    assert "&lt;b&gt;x" in html


# --- Pannello statistiche ----------------------------------------------------


def test_pannello_statistiche_con_impostazioni_esci_e_crediti(user_home):
    sheet = _stats_dialog(user_home)
    assert "data-animated" in sheet and "data-stats-body" in sheet
    assert 'href="/profile/settings"' in sheet and "Impostazioni" in sheet
    # Esci: modulo POST con il token CSRF, non un link
    logout = re.search(r'<form class="sheet__logout" method="post" action="/auth/logout">.*?</form>', sheet, flags=re.DOTALL)
    assert logout, "Esci deve essere un modulo POST"
    assert re.search(r'<input type="hidden" name="csrf_token" value="[^"]+">', logout.group(0))
    assert "Esci" in logout.group(0)
    # Crediti delle immagini (D37)
    credits = re.search(r'<p class="sheet__credits".*?</p>', sheet, flags=re.DOTALL).group(0)
    text = " ".join(re.sub(r"<[^>]+>", "", credits).split())
    assert text == "Immagini delle carte: Matsoftware, CC BY-SA 3.0, da Wikimedia Commons"
    assert 'href="https://creativecommons.org/licenses/by-sa/3.0/deed.it"' in credits
    assert 'rel="noopener"' in credits


def test_dati_finti_delle_statistiche_raggiungibili(app, user_home):
    url = re.search(r'data-stats-url="([^"]+)"', user_home).group(1)
    assert url == "/static/dev/statistiche_esempio.json"
    response = app.test_client().get(url)
    assert response.status_code == 200
    data = json.loads(response.get_data(as_text=True))
    response.close()
    for key in ("games", "wins", "losses", "win_rate", "ratings"):
        assert key in data, key
    for mode in ("1v1", "2v2"):
        assert {"value", "games", "provisional"} <= data["ratings"][mode].keys()


# --- Script e stili ----------------------------------------------------------


def test_home_carica_home_js_che_avvia_il_layout(app, guest_home):
    assert re.search(r'<script type="module" src="/static/js/pages/home\.js"></script>', guest_home)
    home_js = (STATIC / "js" / "pages" / "home.js").read_text(encoding="utf-8")
    assert "from '../core/layout.js'" in home_js and "initLayout()" in home_js


def test_import_js_puntano_a_file_esistenti():
    files = sorted((STATIC / "js").rglob("*.js"))
    for path in files:
        for target in re.findall(r"from '(\.{1,2}/[^']+)'", path.read_text(encoding="utf-8")):
            assert (path.parent / target).resolve().is_file(), f"{path.name}: {target}"


def test_variabili_css_usate_esistono():
    defined = set(re.findall(r"(--[\w-]+)\s*:", (STATIC / "css" / "base" / "variables.css").read_text(encoding="utf-8")))
    for name in ("navbar.css", "stats-panel.css"):
        css = (STATIC / "css" / "components" / name).read_text(encoding="utf-8")
        local = set(re.findall(r"(--[\w-]+)\s*:", css))
        for used in set(re.findall(r"var\((--[\w-]+)", css)):
            assert used in defined or used in local, f"{name}: {used}"


def test_css_della_navbar_caricati(app, guest_home):
    client = app.test_client()
    for name in ("navbar.css", "stats-panel.css"):
        path = f"/static/css/components/{name}"
        assert f'href="{path}"' in guest_home
        response = client.get(path)
        assert response.status_code == 200
        response.close()


# --- Immagini delle carte ----------------------------------------------------


def test_immagini_uguali_al_prototipo():
    expected = {f"{who}-{suit}.webp" for who in ("asso", "cavallo", "re", "tre") for suit in SUITS}
    expected |= {f"asso-{suit}-figura.webp" for suit in SUITS}
    expected.add("dorso.webp")
    images = {p.name for p in CARDS.glob("*.webp")}
    assert images == expected
    for name in images:
        assert _sha(CARDS / name) == _sha(PROTOTYPE_IMG / name), name
    assert not (CARDS / "seme-denari.svg").exists()
    licence = (CARDS / "LICENZA.md").read_text(encoding="utf-8")
    assert "Matsoftware" in licence and "CC BY-SA 3.0" in licence and "Pubblico dominio" in licence


def test_immagini_del_logo_raggiungibili(app, guest_home):
    client = app.test_client()
    sources = set(re.findall(r'src="(/static/img/cards-bg/[^"]+)"', guest_home))
    assert sources == {
        "/static/img/cards-bg/dorso.webp",
        "/static/img/cards-bg/cavallo-coppe.webp",
        "/static/img/cards-bg/re-coppe.webp",
    }
    # Le figure che layout.js mette sulle carte del logo, seme per seme
    base = re.search(r'data-img-base="([^"]+)"', guest_home).group(1)
    assert base == "/static/img/cards-bg/"
    for suit in SUITS:
        for who in ("cavallo", "re"):
            response = client.get(f"{base}{who}-{suit}.webp")
            assert response.status_code == 200, (who, suit)
            response.close()
