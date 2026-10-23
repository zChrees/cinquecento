"""P46: pannello amici.

Fino al lotto 9b-1 della migrazione questo file provava nel browser il pannello del
JavaScript vecchio (FriendsPanel.js, sulla home Jinja /vecchia-home): contatore e
lista, richiesta di amicizia con il codice CSRF e request_id, accetta e rimuovi,
"indietro" ed Esc. Da allora quei controlli li fa, sul pannello React,
tests/frontend2/test_spa_amici.py, e il limite della chat tests/frontend/test_spa_chat.py.
Qui restano:
- sul codice vecchio, fino al lotto 9b-2: il pulsante "Amici" collegato al pannello,
  i CSS del pannello in base.html, componenti che non inseriscono testo come HTML e
  senza inviti a partita;
- nel browser, sulle pagine React: niente pannello al tavolo né senza login.
Se né Chrome né Edge sono installati, o manca il build della SPA, i controlli nel
browser si saltano. Non serve MySQL.
"""

import re
from pathlib import Path

import pytest
from flask import render_template

from app import create_app
from tests.browser import TEST_COOKIE, Browser, FakeUser, find_browser, running_server
from tests.spa import table_path

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "app" / "static"
ME = 12   # nei dati finti l'utente collegato è Mario, 12


def _render_logged_in(app, path="/"):
    with app.test_request_context(path):
        return render_template("main/index.html", current_user=FakeUser("Mario", ME), demo_urls=None, demo_state=None)


def _friends_button(html):
    return re.search(r"<button[^>]*data-friends-button[^>]*>", html, flags=re.DOTALL).group(0)


# --- Pagina e file (codice vecchio, fino al lotto 9b-2) ----------------------------


def test_pulsante_amici_collegato_al_pannello():
    app = create_app("testing")
    button = _friends_button(_render_logged_in(app))
    assert 'aria-controls="friends"' in button and 'aria-haspopup="dialog"' in button
    assert 'data-friends-url="/friends/"' in button
    # La chat finta di P46 non c'è più (P48): nessun indirizzo di dati finti
    assert "data-chat-demo-url" not in button


def test_css_del_pannello_in_base_html():
    app = create_app("testing")
    html = _render_logged_in(app)
    client = app.test_client()
    for name in ("friends-panel", "chat"):
        path = f"/static/css/components/{name}.css"
        assert f'href="{path}"' in html, name
        response = client.get(path)
        assert response.status_code == 200, name
        response.close()


def test_componenti_solo_testo_e_niente_inviti():
    for name in ("FriendsPanel", "ChatWindow"):
        code = (STATIC / "js" / "components" / f"{name}.js").read_text(encoding="utf-8")
        for forbidden in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write"):
            assert forbidden not in code, (name, forbidden)
    panel = (STATIC / "js" / "components" / "FriendsPanel.js").read_text(encoding="utf-8")
    # Gli inviti a partita stanno solo nella carta-modal della home (decisione di P46)
    assert "Invita" not in panel and "invite:" not in panel
    layout = (STATIC / "js" / "core" / "layout.js").read_text(encoding="utf-8")
    assert "initFriendsPanel(document.querySelector('[data-friends-button]'))" in layout


# --- Nel browser -------------------------------------------------------------------


@pytest.fixture(scope="module")
def server():
    with running_server(create_app("testing"), FakeUser("Mario", ME)) as url:
        yield url


@pytest.fixture
def browser(server, tmp_path):
    b = Browser(find_browser(), tmp_path / "chrome")
    b.send("Network.setCookie", name=TEST_COOKIE[0], value=TEST_COOKIE[1], url=server)
    yield b
    b.close()


def test_niente_pannello_al_tavolo_ne_senza_login(browser, server):
    # Dal lotto 9b-1 sulle pagine React: il tavolo e la home senza login
    browser.open(f"{server}{table_path('prova', demo='1v1')}", 390, 844, "document.querySelector('[data-mode]') !== null")
    assert browser.js("document.querySelector('[data-friends-panel]')") is None
    browser.send("Network.deleteCookies", name=TEST_COOKIE[0], url=server)
    browser.open(f"{server}/", 390, 844, "document.querySelector(\"[data-login-prompt][aria-label^='Amici']\") !== null")
    assert browser.js("document.querySelector('[data-friends-panel]')") is None
    browser.click("[data-login-prompt][aria-label^='Amici']")
    browser.wait_js("document.querySelector('dialog.dialog[open]') !== null", "finestra di accesso")
