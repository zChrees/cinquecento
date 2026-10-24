"""P43: immagini degli avatar.

Controlla il "Fatto quando" di SCALETTA.md (P43): ogni avatar di
app/services/avatars.py ha la sua immagine (app/static/img/avatars/<codice>.svg);
chi non ne ha scelto uno vede l'iniziale; il peso totale è sotto 300 KB.
Controlla anche che frontend/src/game/SeatAvatar.tsx (l'avatar al tavolo React, dal
passo 8a) conosca gli stessi codici del server, che i componenti usino Avatar.tsx o
SeatAvatar.tsx invece di calcolare l'iniziale da sé, che navbar e pannello statistiche
della home React mostrino l'immagine o l'iniziale, e che al tavolo di prova
(/game/prova?demo=2v2) le immagini si carichino e un codice fuori elenco mostri
l'iniziale. Nel browser: Chrome o Edge senza finestra (tests/browser.py); senza
browser, o senza il build della SPA, quei controlli si saltano.
Avatar.tsx non ha una copia: si fida dei codici che il server ha già
controllato (P17). Non serve MySQL.
"""

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from flask_login import login_user

from app import create_app
from app.services.avatars import AVATARS
from tests.browser import TEST_COOKIE, Browser, find_browser, running_server
from tests.browser import FakeUser as BrowserUser
from tests.spa import needs_spa, table_path

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "app" / "static"
AVATAR_DIR = STATIC / "img" / "avatars"
SEAT_AVATAR_TSX = ROOT / "frontend" / "src" / "game" / "SeatAvatar.tsx"
SVG_NS = "{http://www.w3.org/2000/svg}"


@pytest.fixture
def app():
    return create_app("testing")

# --- File delle immagini -----------------------------------------------------


def test_una_immagine_per_ogni_codice_e_nessuna_in_piu():
    files = {p.stem for p in AVATAR_DIR.glob("*.svg")}
    assert files == set(AVATARS)
    assert {p.name for p in AVATAR_DIR.iterdir()} == {f"{code}.svg" for code in AVATARS}


def test_peso_totale_sotto_300_kb():
    total = sum(p.stat().st_size for p in AVATAR_DIR.glob("*.svg"))
    assert total < 300 * 1024, total


@pytest.mark.parametrize("code", sorted(AVATARS))
def test_svg_valido_quadrato_e_senza_risorse_esterne(code):
    text = (AVATAR_DIR / f"{code}.svg").read_text(encoding="utf-8")
    root = ET.fromstring(text)   # un SVG non valido (per esempio "--" in un commento) non si legge
    assert root.tag == f"{SVG_NS}svg"
    assert root.get("viewBox") == "0 0 64 64"
    # Tutto disegnato dentro il file: niente immagini o font da fuori (CSP, P32)
    assert "href=" not in text and "http://" not in text.replace("http://www.w3.org/2000/svg", "")
    assert "<script" not in text and "<image" not in text and "<text" not in text
    for comment in re.findall(r"<!--(.*?)-->", text, flags=re.DOTALL):
        assert "--" not in comment


def test_immagini_servite(app):
    client = app.test_client()
    for code in AVATARS:
        response = client.get(f"/static/img/avatars/{code}.svg")
        assert response.status_code == 200, code
        assert response.mimetype == "image/svg+xml"
        response.close()


# --- Copie dell'elenco dei codici ---------------------------------------------


def test_seat_avatar_tsx_conosce_gli_stessi_codici_del_server():
    # Passo 8a: la terza copia dell'elenco, per l'avatar al tavolo React (codice fuori
    # elenco → iniziale); si legge come testo, senza Node
    code = SEAT_AVATAR_TSX.read_text(encoding="utf-8")
    found = re.search(r"export const AVATAR_CODES: readonly string\[\] = \[(.*?)\];", code, flags=re.DOTALL)
    assert found, "AVATAR_CODES non trovato in SeatAvatar.tsx"
    assert re.findall(r"'([^']+)'", found.group(1)) == list(AVATARS)


def test_componenti_usano_avatar_tsx():
    # Un solo posto decide immagine o iniziale: nessun componente la ricalcola da sé.
    # Dal lotto 9b-2 i componenti React: Avatar.tsx fuori dal tavolo, SeatAvatar.tsx al tavolo
    components = ROOT / "frontend" / "src" / "components"
    for name in ("FriendRows.tsx", "ModeModal.tsx", "QueueOverlay.tsx", "Navbar.tsx", "StatsSheet.tsx"):
        code = (components / name).read_text(encoding="utf-8")
        assert "import { Avatar } from './Avatar';" in code, name
        assert "charAt(0).toUpperCase()" not in code and "slice(0, 1).toUpperCase()" not in code, name
    game = SEAT_AVATAR_TSX.parent
    assert "import { SeatAvatar } from './SeatAvatar';" in (game / "Table.tsx").read_text(encoding="utf-8")
    for path in sorted(game.glob("*.tsx")):
        if path.name != "SeatAvatar.tsx":
            code = path.read_text(encoding="utf-8")
            assert "charAt(0).toUpperCase()" not in code and "slice(0, 1).toUpperCase()" not in code, path.name


# --- Navbar e pannello statistiche, nel browser ------------------------------


# AVATARS_SHOWN: l'avatar della navbar e quello del pannello statistiche
AVATARS_SHOWN = """[document.querySelector('[data-part="navbar"] .avatar'), document.querySelector('#stats .avatar')]
  .map((a) => ({ cls: a.className, code: a.dataset.avatar ?? null, aria: a.getAttribute('aria-hidden'),
                 text: a.querySelector('img') ? null : a.textContent,
                 img: a.querySelector('img') ? { cls: a.querySelector('img').className,
                   src: a.querySelector('img').getAttribute('src'), alt: a.querySelector('img').alt } : null }))"""


def _shown_avatars(tmp_path, avatar):
    """Gli avatar di navbar e pannello statistiche della home React, per l'utente mario."""
    needs_spa()
    user = BrowserUser("mario")
    user.avatar = avatar
    with running_server(create_app("testing"), user) as url:
        browser = Browser(find_browser(), tmp_path / "chrome")
        try:
            browser.send("Network.setCookie", name=TEST_COOKIE[0], value=TEST_COOKIE[1], url=url)
            browser.open(f"{url}/", 390, 844, "document.querySelector('#stats .avatar') !== null"
                         " && document.querySelector('[data-friends-panel]')?.dataset.connection === 'connected'",
                         timeout=60)
            return browser.js(AVATARS_SHOWN)
        finally:
            browser.close()


def test_navbar_e_statistiche_con_l_immagine(tmp_path):
    navbar, stats = _shown_avatars(tmp_path, "re_denari")
    img = {"cls": "avatar__img", "src": "/static/img/avatars/re_denari.svg", "alt": ""}
    assert navbar == {"cls": "avatar avatar--img", "code": "re_denari", "aria": "true", "text": None, "img": img}
    assert stats == {"cls": "avatar avatar--big avatar--img", "code": "re_denari", "aria": "true", "text": None, "img": img}


def test_senza_avatar_resta_l_iniziale(tmp_path):
    navbar, stats = _shown_avatars(tmp_path, None)
    assert navbar == {"cls": "avatar", "code": None, "aria": "true", "text": "M", "img": None}
    assert stats == {"cls": "avatar avatar--big", "code": None, "aria": "true", "text": "M", "img": None}

def test_impostazioni_ricevono_tutti_gli_avatar(app):
    # Dal passo 6 della migrazione la pagina è della SPA: l'elenco lo dà GET /api/profile/avatars
    # (un'immagine per scelta la controlla tests/frontend2/test_spa_impostazioni.py nel browser)
    with app.test_request_context("/api/profile/avatars"):
        login_user(BrowserUser("Mario"))
        body = app.view_functions["profile_api.avatars"]()
    assert body["ok"] is True
    assert body["data"]["avatars"] == [{"code": code, "name": name} for code, name in AVATARS.items()]
    for code in AVATARS:
        assert (AVATAR_DIR / f"{code}.svg").is_file(), code


# --- Nel browser: il tavolo di prova ------------------------------------------


@pytest.fixture(scope="module")
def server():
    with running_server(create_app("testing"), BrowserUser("Mario", 12)) as url:
        yield url


@pytest.fixture
def browser(server, tmp_path):
    b = Browser(find_browser(), tmp_path / "chrome")
    b.send("Network.setCookie", name=TEST_COOKIE[0], value=TEST_COOKIE[1], url=server)
    yield b
    b.close()


SEATS = """[...document.querySelectorAll('.seat')].map((seat) => {
  const avatar = seat.querySelector('.seat__avatar > .avatar');
  const img = avatar.querySelector('img');
  const box = avatar.getBoundingClientRect();
  const inner = img ? img.getBoundingClientRect() : null;
  return {
    name: seat.querySelector('.seat__name').textContent,
    code: avatar.dataset.avatar ?? null,
    text: img ? null : avatar.textContent,
    loaded: img ? img.complete && img.naturalWidth > 0 : null,
    fits: inner ? Math.abs(inner.width - box.width) < 1 && Math.abs(inner.height - box.height) < 1 : null,
    hidden: avatar.getAttribute('aria-hidden'),
  };
})"""


@pytest.mark.parametrize("size", [(360, 640), (1440, 900)])
def test_tavolo_con_immagini_e_iniziali(browser, server, size):
    browser.open(f"{server}{table_path('prova', demo='2v2')}", *size, "document.querySelectorAll('.seat').length === 4")
    browser.wait_js("[...document.querySelectorAll('.seat img.avatar__img')].every((i) => i.complete)",
                    "immagini degli avatar caricate")
    seats = {s["name"]: s for s in browser.js(SEATS)}
    # Rosalia ha "denari"; Giulia ha "cavallo_spade", che non è del set: iniziale
    assert seats["Rosalia"]["code"] == "denari"
    assert seats["Rosalia"]["loaded"] is True and seats["Rosalia"]["fits"] is True
    assert seats["Giulia"]["code"] is None and seats["Giulia"]["text"] == "G"
    assert seats["Mario (tu)"]["text"] == "M"
    assert all(s["hidden"] == "true" for s in seats.values())
