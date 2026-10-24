"""P46: pannello amici.

I controlli del pannello nel browser (contatore e lista, richiesta di amicizia con il
codice CSRF e request_id, accetta e rimuovi, "indietro" ed Esc) li fa, sul pannello
React, tests/frontend2/test_spa_amici.py, e il limite della chat tests/frontend/test_spa_chat.py.
Al lotto 9b-2 sono andati via, con il codice vecchio, anche i controlli sui suoi file:
niente testo inserito come HTML lo controlla tests/frontend/test_base.py su tutti i
file di frontend/src/, niente inviti nel pannello test_spa_amici.py.
Qui resta, nel browser, sulle pagine React: niente pannello al tavolo né senza login.
Se né Chrome né Edge sono installati, o manca il build della SPA, i controlli nel
browser si saltano. Non serve MySQL.
"""

import pytest

from app import create_app
from tests.browser import TEST_COOKIE, Browser, FakeUser, find_browser, running_server
from tests.spa import table_path

ME = 12   # nei dati finti l'utente collegato è Mario, 12


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
