"""P40: navbar, pannello statistiche, finestra "Accedi o registrati", immagini delle carte.

Controlla il "Fatto quando" di SCALETTA.md (P40): la navbar ha avatar, nome del
gioco e pulsante amici; ogni pulsante con sola icona ha un'etichetta accessibile;
il pannello statistiche ha Impostazioni, Esci e i crediti delle immagini (D37), che
ci sono anche nella finestra "Accedi o registrati" (D39). Controlla anche che le
immagini di app/static/img/cards-bg/ siano quelle del prototipo.
Dal lotto 9b-2 della migrazione la navbar è quella React (Navbar.tsx, StatsSheet.tsx,
LoginPrompt.tsx): la pagina la disegna la SPA nel browser (Chrome o Edge senza
finestra, tests/browser.py), e i controlli guardano l'HTML che ne esce, lo stesso di
prima (fino al 9b-2 si leggeva il template della home Jinja). Senza browser, o senza
il build della SPA, quei controlli si saltano.
Non serve MySQL: l'utente con il login è finto (running_server con FakeUser).
"""

import hashlib
import json
import re
from pathlib import Path

import pytest

from app import create_app
from tests.browser import TEST_COOKIE, Browser, FakeUser, find_browser, running_server
from tests.spa import needs_spa

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "app" / "static"
CARDS = STATIC / "img" / "cards-bg"
PROTOTYPE_IMG = ROOT / "docs" / "prototipo" / "img"
SUITS = ("bastoni", "coppe", "denari", "spade")
SPA_INDEX = ROOT / "frontend" / "index.html"
# Pagina pronta: senza login i due pulsanti "Accedi", con il login il pulsante delle
# statistiche e il collegamento al tempo reale (un test con il login lo aspetta, P58)
GUEST_READY = "document.querySelectorAll('[data-login-prompt]').length === 2"
USER_READY = ("document.querySelector('[data-open-stats]') !== null"
              " && document.querySelector('[data-friends-panel]')?.dataset.connection === 'connected'")
PAGE_HTML = "document.documentElement.outerHTML"


def _page(tmp_path, username, logged):
    """L'HTML della home React disegnata nel browser, con o senza il login di `username`."""
    needs_spa()
    with running_server(create_app("testing"), FakeUser(username)) as url:
        browser = Browser(find_browser(), tmp_path / f"chrome-{logged}")
        try:
            ready = GUEST_READY
            if logged:
                browser.send("Network.setCookie", name=TEST_COOKIE[0], value=TEST_COOKIE[1], url=url)
                ready = USER_READY
            browser.open(f"{url}/", 390, 844, ready, timeout=60)
            return browser.js(PAGE_HTML)
        finally:
            browser.close()


@pytest.fixture(scope="module")
def guest_home(tmp_path_factory):
    return _page(tmp_path_factory.mktemp("guest"), "mario", logged=False)


@pytest.fixture(scope="module")
def user_home(tmp_path_factory):
    return _page(tmp_path_factory.mktemp("user"), "mario", logged=True)


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


def test_nome_utente_inserito_come_testo(tmp_path):
    html = _page(tmp_path, "<b>x", logged=True)
    navbar = _navbar(html)
    assert "<b>x" not in navbar
    assert "&lt;b&gt;x" in navbar


# --- Pannello statistiche ----------------------------------------------------


def test_pannello_statistiche_con_impostazioni_esci_e_crediti(user_home):
    sheet = _stats_dialog(user_home)
    assert "data-animated" in sheet and "data-stats-body" in sheet
    assert 'href="/profile/settings"' in sheet and "Impostazioni" in sheet
    # Esci: un pulsante di un modulo, non un link (un altro sito non può far uscire
    # l'utente). Dal lotto 9c il modulo non va al server da solo: niente action né
    # campo csrf_token, la richiesta POST /api/auth/logout la manda la pagina
    # (provata in test_spa.py, test_esci_manda_la_richiesta_e_ricarica_la_home)
    logout = re.search(r'<form class="sheet__logout">.*?</form>', sheet, flags=re.DOTALL)
    assert logout, "Esci deve essere un modulo"
    assert "<input" not in logout.group(0)
    assert re.search(r'<button\b[^>]*type="submit"[^>]*data-logout=""', logout.group(0))
    assert "Esci" in logout.group(0)
    # Crediti delle immagini (D37)
    credits = re.search(r'<p class="sheet__credits".*?</p>', sheet, flags=re.DOTALL).group(0)
    text = " ".join(re.sub(r"<[^>]+>", "", credits).split())
    assert text == "Immagini delle carte: Matsoftware, CC BY-SA 3.0, da Wikimedia Commons"
    assert 'href="https://creativecommons.org/licenses/by-sa/3.0/deed.it"' in credits
    assert 'rel="noopener"' in credits


def test_crediti_anche_nella_finestra_di_accesso(tmp_path):
    # D39: chi non ha fatto il login vede le carte nel logo, quindi anche la finestra
    # "Accedi o registrati" ha la riga dei crediti, uguale a quella del pannello
    needs_spa()
    with running_server(create_app("testing"), FakeUser("mario")) as url:
        browser = Browser(find_browser(), tmp_path / "chrome")
        try:
            browser.open(f"{url}/", 390, 844, GUEST_READY, timeout=60)
            browser.click("[data-login-prompt]")
            browser.wait_js("document.querySelector('dialog.dialog[open]') !== null", "finestra di accesso")
            credits = browser.js("""(() => {
              const d = document.querySelector('dialog.dialog[open]');
              const link = [...d.querySelectorAll('a')].find((a) => a.textContent === 'CC BY-SA 3.0');
              return { text: d.textContent.replace(/\\s+/g, ' '), href: link?.href ?? null, rel: link?.rel ?? null };
            })()""")
        finally:
            browser.close()
    assert "Immagini delle carte: Matsoftware, CC BY-SA 3.0, da Wikimedia Commons" in credits["text"]
    assert credits["href"] == "https://creativecommons.org/licenses/by-sa/3.0/deed.it"
    assert credits["rel"] == "noopener"


def test_statistiche_dal_server_e_forma_dell_esempio(user_home):
    # P30: il pannello chiede sempre i dati veri (GET /api/stats/me, provato in
    # tests/api/test_statistiche.py); il file di esempio resta come riferimento del contratto
    url = re.search(r'data-stats-url="([^"]+)"', user_home).group(1)
    assert url == "/api/stats/me"
    data = json.loads((STATIC / "dev" / "statistiche_esempio.json").read_text(encoding="utf-8"))
    for key in ("games", "wins", "losses", "draws", "win_rate", "ratings"):
        assert key in data, key
    for mode in ("1v1", "2v2"):
        assert {"value", "games", "provisional"} <= data["ratings"][mode].keys()


# --- Stili -------------------------------------------------------------------


def test_variabili_css_usate_esistono():
    defined = set(re.findall(r"(--[\w-]+)\s*:", (STATIC / "css" / "base" / "variables.css").read_text(encoding="utf-8")))
    for name in ("navbar.css", "stats-panel.css"):
        css = (STATIC / "css" / "components" / name).read_text(encoding="utf-8")
        local = set(re.findall(r"(--[\w-]+)\s*:", css))
        for used in set(re.findall(r"var\((--[\w-]+)", css)):
            assert used in defined or used in local, f"{name}: {used}"


def test_css_della_navbar_caricati():
    spa = SPA_INDEX.read_text(encoding="utf-8")
    client = create_app("testing").test_client()
    for name in ("navbar.css", "stats-panel.css"):
        path = f"/static/css/components/{name}"
        assert f'href="{path}"' in spa
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


def test_immagini_del_logo_raggiungibili(guest_home):
    client = create_app("testing").test_client()
    navbar = _navbar(guest_home)
    sources = set(re.findall(r'src="(/static/img/cards-bg/[^"]+)"', navbar))
    assert sources == {
        "/static/img/cards-bg/dorso.webp",
        "/static/img/cards-bg/cavallo-coppe.webp",
        "/static/img/cards-bg/re-coppe.webp",
    }
    # Le figure che Logo.tsx mette sulle carte del logo, seme per seme
    base = re.search(r'data-logo-cards="" data-img-base="([^"]+)"', navbar).group(1)
    assert base == "/static/img/cards-bg/"
    for suit in SUITS:
        for who in ("cavallo", "re"):
            response = client.get(f"{base}{who}-{suit}.webp")
            assert response.status_code == 200, (who, suit)
            response.close()
