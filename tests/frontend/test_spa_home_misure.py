"""Passo 7d della migrazione: le misure della home React (/), come test_pagina_home.py (P22).

Gli stessi controlli di misura che test_pagina_home.py faceva sulla home Jinja, ora
sulla home React (frontend/src/pages/HomePage.tsx), nel browser (Chrome o Edge senza
finestra, tests/browser.py), con il login finto di running_server (FakeUser):
- la home non scorre alle misure di docs/prototipo/LEGGIMI.md (NO_SCROLL_SIZES): carte-
  pulsante sotto la navbar e dentro lo schermo, spazio di stato e titoli senza
  sovrapporsi alle carte;
- con l'avviso "Hai una partita in corso" (?demo=rientro) la home non scorre e l'avviso
  non copre le carte;
- le carte dello sfondo passano dietro a titoli e carte-pulsante;
- la carta-modal, in tutte e quattro le modalità e alle misure di MODAL_SIZES, entra
  nello schermo, non scorre, ha ogni parte dentro la cornice e nell'ordine, "Gioca"
  compreso, e la X non copre il titolo.
Gli altri controlli di test_pagina_home.py (coda, CPU, scelta dell'avversario, finestra
di accesso, avviso di rientro, online al singolare) li fanno già test_spa_home.py,
test_spa_home_coda.py e test_spa_home_inviti.py; "Gira il telefono" (P116) ha il suo
file, test_gira_telefono.py.
Non serve MySQL: GET /api/friends/ e GET /api/stats/me li risponde il browser con i dati di
esempio di app/static/dev/ (Browser.routes), così la lista degli amici da invitare è
piena come nella home Jinja con i dati finti (la carta più alta).
Senza browser, o senza il build della SPA, i controlli si saltano.
"""

import json
import time
from pathlib import Path

import pytest

from app import create_app
from tests.browser import TEST_COOKIE, Browser, FakeUser, find_browser, running_server
from tests.spa import needs_spa

ROOT = Path(__file__).resolve().parents[2]
DEV = ROOT / "app" / "static" / "dev"
TILES = [("veloce", "1v1"), ("veloce", "2v2"), ("amico", "1v1"), ("amico", "2v2")]
WAIT = 10

# Misure controllate nel prototipo (docs/prototipo/LEGGIMI.md); P116: niente telefono in
# orizzontale (844×390, 667×375), dove la pagina è coperta dall'avviso "Gira il telefono"
NO_SCROLL_SIZES = [(360, 640), (375, 667), (390, 844), (412, 915), (768, 1024),
                   (1280, 720), (1440, 900), (1920, 1080)]
MODAL_SIZES = [(1920, 1080), (1440, 900), (1366, 657), (1536, 730), (360, 560), (360, 640),
               (390, 844), (412, 915)]
RESUME_SIZES = [(1440, 900), (360, 640), (768, 1024)]

# Risposte finte (forma del contratto: {"ok": true, "data": ...}) con i dati di esempio
FRIENDS = json.loads((DEV / "amici_esempio.json").read_text(encoding="utf-8"))["GET /api/friends/"]
STATS = {key: value for key, value in json.loads((DEV / "statistiche_esempio.json").read_text(encoding="utf-8")).items()
         if not key.startswith("_")}
ROUTES = {
    "*/api/friends/": lambda _request: (200, {"ok": True, "data": FRIENDS}),
    "*/api/stats/me": lambda _request: (200, {"ok": True, "data": STATS}),
}

# Come test_csp.py: registra ogni risorsa bloccata dalla CSP
RECORD = (
    "window.__csp = [];"
    "document.addEventListener('securitypolicyviolation',"
    " e => window.__csp.push(e.effectiveDirective + ' ' + e.blockedURI));"
)
CONNECTED = "document.querySelector('[data-friends-panel]')?.dataset.connection === 'connected'"
# READY: la cascata dello sfondo, il numero degli online (o l'avviso di rientro) e il
# collegamento al tempo reale
READY = ("document.querySelector('[data-bg-cards]')?.children.length > 0"
         " && (document.querySelector('[data-online]:not([hidden])') !== null"
         " || document.querySelector('[data-resume-slot]:not([hidden])') !== null)"
         f" && {CONNECTED}")
MODAL = "document.querySelector('[data-mode-modal]')"

# Misure della home: rettangoli di navbar, spazio di stato, titoli e carte-pulsante
MEASURE_HOME = """(() => {
  const box = (e) => { const r = e.getBoundingClientRect(); return {top: r.top, bottom: r.bottom, left: r.left, right: r.right}; };
  const visible = (e) => e.getClientRects().length > 0;
  const main = document.querySelector('main');
  const status = [...document.querySelectorAll('[data-status-slot] > *')].filter(visible);
  return {
    vw: innerWidth, vh: innerHeight,
    scrollW: document.documentElement.scrollWidth, scrollH: document.documentElement.scrollHeight,
    mainScroll: main.scrollHeight, mainClient: main.clientHeight,
    navbar: box(document.querySelector('[data-part="navbar"]')),
    status: status.map(box),
    titles: [...document.querySelectorAll('.mode-section__title')].map(box),
    tiles: [...document.querySelectorAll('[data-tile]')].map(box),
  };
})()"""

# Misure della carta-modal: faccia, parti visibili del corpo nell'ordine, X e titolo
MEASURE_MODAL = """(() => {
  const box = (e) => { const r = e.getBoundingClientRect(); return {top: r.top, bottom: r.bottom, left: r.left, right: r.right}; };
  const dialog = document.querySelector('[data-mode-modal]');
  const parts = [...dialog.querySelector('.mode-modal__body').children].filter((e) => e.getClientRects().length > 0);
  return {
    vw: innerWidth, vh: innerHeight,
    face: box(dialog.querySelector('.mode-modal__face')),
    parts: parts.map((e) => ({name: e.className || e.tagName, ...box(e)})),
    close: box(dialog.querySelector('.mode-modal__close')),
    title: box(dialog.querySelector('.mode-modal__title')),
    play: box(dialog.querySelector('[data-play]')),
    faceScroll: dialog.querySelector('.mode-modal__face').scrollHeight,
    faceClient: dialog.querySelector('.mode-modal__face').clientHeight,
  };
})()"""

FRAME = 14   # cornice doppia della faccia: 10 px dal bordo più 4 px di spessore
EPS = 0.5


@pytest.fixture(scope="module")
def server():
    needs_spa()
    # Con il cookie di prova risulta collegato Mario (utente finto, niente database)
    with running_server(create_app("testing"), FakeUser("Mario")) as url:
        yield url


@pytest.fixture(scope="module")
def browser(server, tmp_path_factory):
    b = Browser(find_browser(), tmp_path_factory.mktemp("chrome"), routes=dict(ROUTES))
    b.send("Network.setCookie", name=TEST_COOKIE[0], value=TEST_COOKIE[1], url=server)
    b.send("Page.enable")  # senza, lo script qui sotto non parte con le pagine nuove
    b.send("Page.addScriptToEvaluateOnNewDocument", source=RECORD)
    # Prima apertura: la prima volta si scaricano font e icone (poi restano in FONT_CACHE)
    b.open(f"{server}/", 390, 844, READY, timeout=100)
    yield b
    b.close()


def _open(browser, url, width, height):
    browser.open(url, width, height, READY, timeout=60)


def _overlap(a, b):
    return a["left"] < b["right"] - EPS and b["left"] < a["right"] - EPS \
        and a["top"] < b["bottom"] - EPS and b["top"] < a["bottom"] - EPS


def _click(browser, selector):
    browser.js(f"document.querySelector({json.dumps(selector)}).click()")


def _open_modal(browser, kind, mode):
    """Apre la carta-modal. Con un amico aspetta la lista degli amici da invitare: la
    carta disegna quella che c'è quando si apre, e GET /api/friends/ può arrivare dopo; se è
    ancora vuota la chiude e la riapre (conta il tempo, non i tentativi)."""
    deadline = time.monotonic() + WAIT
    while True:
        _click(browser, f'[data-tile][data-kind="{kind}"][data-mode="{mode}"]')
        browser.wait_js(f"{MODAL}?.open === true", f"apertura della carta-modal {kind} {mode}")
        if kind != "amico" or browser.js(f"{MODAL}.querySelectorAll('[data-invite-user]').length > 0"):
            return
        if time.monotonic() > deadline:
            pytest.fail("la carta 'Gioca con un amico' non mostra gli amici online", pytrace=False)
        _close_modal(browser)
        time.sleep(0.1)


def _close_modal(browser):
    # Nella home React la carta-modal chiusa non c'è più nella pagina
    _click(browser, ".mode-modal__close")
    browser.wait_js(f"{MODAL} === null", "chiusura della carta-modal")


def _check_home(m, where):
    assert m["scrollW"] <= m["vw"] and m["scrollH"] <= m["vh"], (where, m)
    assert m["mainScroll"] <= m["mainClient"] + 1, f"{where}: il contenuto della home esce dalla pagina"
    assert len(m["tiles"]) == 4 and len(m["status"]) == 1, (where, m)
    for tile in m["tiles"]:
        assert tile["top"] >= m["navbar"]["bottom"] - EPS, (where, tile)
        assert tile["bottom"] <= m["vh"] + EPS and tile["left"] >= -EPS and tile["right"] <= m["vw"] + EPS, \
            (where, tile)
    for block in m["titles"] + m["status"]:
        assert block["top"] >= m["navbar"]["bottom"] - EPS and block["bottom"] <= m["vh"] + EPS, (where, block)
        for tile in m["tiles"]:
            assert not _overlap(block, tile), (where, block, tile)


@pytest.mark.parametrize("size", NO_SCROLL_SIZES, ids=lambda s: f"{s[0]}x{s[1]}")
def test_la_home_non_scorre(browser, server, size):
    width, height = size
    _open(browser, f"{server}/", width, height)
    m = browser.js(MEASURE_HOME)
    _check_home(m, f"{width}x{height}")
    assert len(m["titles"]) == 2, m
    assert browser.js("window.__csp") == []


@pytest.mark.parametrize("size", RESUME_SIZES, ids=lambda s: f"{s[0]}x{s[1]}")
def test_con_l_avviso_di_rientro_la_home_non_scorre(browser, server, size):
    width, height = size
    _open(browser, f"{server}/?demo=rientro", width, height)
    browser.wait_js("document.querySelector('[data-resume]') !== null", "avviso di rientro")
    assert browser.js("document.querySelector('[data-online]').hidden") is True
    _check_home(browser.js(MEASURE_HOME), f"rientro a {width}x{height}")


def test_sfondo_dietro_a_titoli_e_carte(browser, server):
    _open(browser, f"{server}/", 1440, 900)
    result = browser.js("""(() => {
      const deco = document.querySelector('[data-bg-cards]');
      const hit = (e) => { const r = e.getBoundingClientRect();
        return document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2); };
      return {
        cards: deco.children.length,
        zIndex: getComputedStyle(deco).zIndex,
        tiles: [...document.querySelectorAll('[data-tile]')].every((t) => t.contains(hit(t))),
        titles: [...document.querySelectorAll('.mode-section__title')].every((t) => t.contains(hit(t))),
      };
    })()""")
    assert result["cards"] >= 8 and result["zIndex"] == "-1"
    assert result["tiles"] and result["titles"], result


@pytest.mark.parametrize("size", MODAL_SIZES, ids=lambda s: f"{s[0]}x{s[1]}")
def test_la_carta_modal_contiene_tutto(browser, server, size):
    width, height = size
    _open(browser, f"{server}/", width, height)
    for kind, mode in TILES:
        _open_modal(browser, kind, mode)
        m = browser.js(MEASURE_MODAL)
        where = f"{kind} {mode} a {width}x{height}"
        face = m["face"]
        assert face["top"] >= -EPS and face["bottom"] <= m["vh"] + EPS, where
        assert face["left"] >= -EPS and face["right"] <= m["vw"] + EPS, where
        assert m["faceScroll"] <= m["faceClient"], f"{where}: la faccia scorre"
        inner = {"top": face["top"] + FRAME, "bottom": face["bottom"] - FRAME,
                 "left": face["left"] + FRAME, "right": face["right"] - FRAME}
        names = [p["name"] for p in m["parts"]]
        assert "btn btn--primary btn--big" in names, f"{where}: manca Gioca"
        if kind == "amico":
            assert "invite" in names, f"{where}: manca la lista degli amici"
        for part in m["parts"]:
            assert part["top"] >= inner["top"] - EPS and part["bottom"] <= inner["bottom"] + EPS, (where, part)
            assert part["left"] >= inner["left"] - EPS and part["right"] <= inner["right"] + EPS, (where, part)
        for before, after in zip(m["parts"], m["parts"][1:]):
            assert before["bottom"] <= after["top"] + EPS, (where, before["name"], after["name"])
        assert not _overlap(m["close"], m["title"]), f"{where}: la X copre il titolo"
        _close_modal(browser)
