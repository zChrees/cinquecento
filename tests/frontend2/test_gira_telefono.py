"""P116: sul telefono in orizzontale l'avviso "Gira il telefono in verticale".

Controlla il "Fatto quando" di SCALETTA.md (P116): a misure di telefono in orizzontale
(844×390, 667×375, 640×360) l'avviso copre tutta la pagina, su ogni pagina (home,
tavolo, impostazioni, accesso, registrazione, pagina che non esiste), anche sopra una
finestra aperta (pannello amici); in verticale, sul tablet e da computer non c'è.
L'avviso c'è anche nell'HTML di ogni pagina: lo aggiungono frontend/index.html (le pagine
della SPA) e base.html (le pagine di errore).

Le pagine si aprono in Chrome o Edge senza finestra (tests/browser.py), con un utente di
prova (un cookie dei soli test) e senza MySQL. Se né Chrome né Edge sono installati i
controlli nel browser si saltano.
"""

import pytest

from app import create_app
from tests.browser import TEST_COOKIE, Browser, FakeUser, find_browser, running_server
from tests.spa import table_path

LANDSCAPE = [(844, 390), (667, 375), (640, 360)]
NOT_PHONE_LANDSCAPE = [(390, 844), (360, 640), (768, 1024), (1024, 768), (1280, 720)]
# TABLE: il tavolo di prova; l'indirizzo passa da table_path dentro il test (che lo salta
# senza il build della SPA), mai all'importazione del file
TABLE = "/game/prova?demo=1v1"
PAGES = [  # (indirizzo, con il login)
    ("/", True), (TABLE, True), ("/profile/settings", True),
    ("/auth/login", False), ("/auth/register", False), ("/non-esiste", False),
]

# L'avviso visibile e sopra tutto: al centro e negli angoli il punto più in alto è suo
COVER = """(() => {
  const notice = document.querySelector('[data-rotate-notice]');
  const box = notice.getBoundingClientRect();
  const points = [[innerWidth / 2, innerHeight / 2], [2, 2], [innerWidth - 2, 2], [2, innerHeight - 2],
                  [innerWidth - 2, innerHeight - 2]];
  return {
    shown: getComputedStyle(notice).display !== 'none',
    box: [box.left, box.top, box.right, box.bottom],
    on_top: points.every(([x, y]) => notice.contains(document.elementFromPoint(x, y))),
    text: notice.textContent.replace(/\\s+/g, ' ').trim(),
    w: innerWidth, h: innerHeight,
  };
})()"""


@pytest.fixture(scope="module")
def server():
    with running_server(create_app("testing"), FakeUser("Mario", 12)) as url:
        yield url


@pytest.fixture
def browser(server, tmp_path):
    b = Browser(find_browser(), tmp_path / "chrome")
    yield b
    b.close()


# Nelle pagine della SPA il collegamento lo dice il pannello amici di React
CONNECTED = "document.querySelector('[data-friends-panel]')?.dataset.connection === 'connected'"


def _open(browser, server, path, logged, size):
    if logged:
        browser.send("Network.setCookie", name=TEST_COOKIE[0], value=TEST_COOKIE[1], url=server)
    url = path
    if path == TABLE:
        url = table_path("prova", demo="1v1")
    browser.open(server + url, *size, "document.querySelector('[data-rotate-notice]') !== null")
    if logged and path != TABLE:  # la prova del tavolo non si collega
        # Con il login la pagina si collega al tempo reale: prima di cambiarla o di chiudere il
        # browser si aspetta il collegamento, altrimenti blocca il server del file dopo (P58, P62)
        browser.wait_js(CONNECTED, f"collegamento al tempo reale ({path})")


@pytest.mark.parametrize(("path", "logged"), PAGES)
def test_in_orizzontale_l_avviso_copre_la_pagina(browser, server, path, logged):
    for size in LANDSCAPE:
        _open(browser, server, path, logged, size)
        cover = browser.js(COVER)
        assert cover["shown"] and cover["on_top"], (path, size, cover)
        assert cover["box"] == [0, 0, size[0], size[1]], (path, size, cover)
        assert cover["text"] == ("screen_rotation Gira il telefono in verticale "
                                 "Cinquecento si gioca con il telefono in verticale."), cover


@pytest.mark.parametrize(("path", "logged"), [("/", True), (TABLE, True), ("/auth/login", False)])
def test_in_verticale_sul_tablet_e_da_computer_niente(browser, server, path, logged):
    for size in NOT_PHONE_LANDSCAPE:
        _open(browser, server, path, logged, size)
        assert browser.js(COVER)["shown"] is False, (path, size)


def test_anche_sopra_una_finestra_aperta(browser, server):
    # Il pannello amici è un <dialog> (livello più alto della pagina): girando il telefono si nasconde
    _open(browser, server, "/", True, (390, 844))
    browser.click("[data-friends-button]")
    assert browser.js("document.getElementById('friends').open") is True
    browser.send("Emulation.setDeviceMetricsOverride", width=844, height=390, deviceScaleFactor=1, mobile=False)
    browser.wait_js("innerWidth === 844", "telefono girato")
    # Con una finestra aperta il resto della pagina è inerte (elementFromPoint dà <html>): si
    # controlla che l'avviso si veda, e che finestra e sfondo scuro siano spariti
    cover = browser.js(COVER)
    assert cover["shown"] and cover["box"] == [0, 0, 844, 390], cover
    assert browser.js("getComputedStyle(document.getElementById('friends')).visibility") == "hidden"
    assert browser.js("getComputedStyle(document.getElementById('friends'), '::backdrop').backgroundColor")         == "rgba(0, 0, 0, 0)"
    # Di nuovo in verticale il pannello è ancora lì, aperto
    browser.send("Emulation.setDeviceMetricsOverride", width=390, height=844, deviceScaleFactor=1, mobile=False)
    browser.wait_js("innerWidth === 390", "telefono in verticale")
    assert browser.js(COVER)["shown"] is False
    assert browser.js("getComputedStyle(document.getElementById('friends')).visibility") == "visible"
