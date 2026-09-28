"""P32: la CSP (intestazione Content-Security-Policy di app/__init__.py) non blocca
niente nelle pagine vere.

Nel browser (Chrome o Edge senza finestra, tests/browser.py), con il server vero: prima
che la pagina si carichi si registrano gli eventi `securitypolicyviolation`, che il
browser lancia per ogni risorsa bloccata dalla CSP (script, stili, font, immagini,
connessioni, anche il websocket). Home (con il collegamento in tempo reale), tavolo
di prova e registrazione: nessuna violazione. Una violazione fatta apposta si vede,
così una lista vuota vuol dire davvero "niente bloccato".
Se né Chrome né Edge sono installati il test si salta.
"""

import pytest

from app import create_app
from tests.browser import TEST_COOKIE, Browser, FakeUser, find_browser, running_server

RECORD = (
    "window.__csp = [];"
    "document.addEventListener('securitypolicyviolation',"
    " e => window.__csp.push(e.effectiveDirective + ' ' + e.blockedURI));"
)
PAGES = [
    # (indirizzo, condizione JS di pagina pronta)
    ("/", "document.querySelector('[data-online-count]')?.textContent === '1'"),  # home:status arrivato
    ("/game/prova?demo=1v1", "document.querySelector('[data-table]') !== null"),
    ("/auth/register", "document.querySelector('form') !== null"),
]


@pytest.fixture(scope="module")
def browser(tmp_path_factory):
    path = find_browser()  # se manca, il test si salta da qui
    app = create_app("testing")
    with running_server(app, FakeUser("Mario")) as url:
        b = Browser(path, tmp_path_factory.mktemp("chrome"))
        b.send("Network.setCookie", name=TEST_COOKIE[0], value=TEST_COOKIE[1], url=url)
        b.send("Page.enable")  # senza, lo script qui sotto non parte con le pagine nuove
        b.send("Page.addScriptToEvaluateOnNewDocument", source=RECORD)
        try:
            yield b, url
        finally:
            b.close()


@pytest.mark.parametrize(("path", "ready"), PAGES)
def test_la_csp_non_blocca_niente(browser, path, ready):
    b, url = browser
    b.open(f"{url}{path}", 390, 844, ready=ready)
    assert b.js("window.__csp") == [], path


def test_una_violazione_si_vede(browser):
    b, url = browser
    b.open(f"{url}/auth/register", 390, 844)
    # Uno script scritto dentro la pagina: la CSP lo blocca e lo segnala
    b.js("const s = document.createElement('script'); s.textContent = 'window.__eseguito = 1';"
         " document.body.append(s)")
    b.wait_js("window.__csp.length > 0", "violazione segnalata")
    assert b.js("window.__eseguito") is None
    assert b.js("window.__csp")[0].startswith("script-src")
