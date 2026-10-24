"""Passo 7a della migrazione: la home React (frontend/src/pages/HomePage.tsx), dal passo 7d su /.

Controlla:
- / c'è ovunque e accetta solo ?demo=rientro, che vale solo in sviluppo e nei test
  (altrove 404);
- nel browser, a 390×844 e 1280×720, anche con ?demo=rientro (l'avviso "Hai una
  partita in corso"), la cascata di carte dello sfondo e la CSP che non blocca niente
  (fino al lotto 9b-1 qui c'era anche il confronto, elemento per elemento, con la home
  Jinja: tolto con la home Jinja, scelta 2 del passo 9);
- senza login: il numero degli online da GET /api/online, nessun collegamento al tempo
  reale, una carta-pulsante apre "Accedi o registrati", la CSP non blocca niente;
- con il login: il numero da home:status ("1 giocatore online", al singolare), una
  carta-pulsante apre la carta-modal, e con ?demo=rientro
  l'avviso di rientro prende il posto di "giocatori online".
Il login è quello finto di running_server (FakeUser): la pagina non scrive nel database.
Senza browser, o senza il build della SPA, i controlli nel browser si saltano.
"""

import json

import pytest

from app import create_app
from app.realtime.presence import presence
from tests.browser import TEST_COOKIE, Browser, FakeUser, find_browser, running_server
from tests.spa import needs_spa

PAGE = "/"  # dal passo 7d (fino al 7c era /prova-home)
# Come test_csp.py: registra ogni risorsa bloccata dalla CSP
RECORD = (
    "window.__csp = [];"
    "document.addEventListener('securitypolicyviolation',"
    " e => window.__csp.push(e.effectiveDirective + ' ' + e.blockedURI));"
)
# READY: la home ha lo sfondo pieno e il numero degli online o l'avviso di rientro
READY = ("document.querySelector('h1') !== null"
         " && document.querySelectorAll('[data-bg-cards] > *').length > 0"
         " && (document.querySelector('[data-online]:not([hidden])') !== null"
         " || document.querySelector('[data-resume-slot]:not([hidden])') !== null)")
FLASHES = "[...document.querySelectorAll('[data-flash] .flash')].map((f) => [f.dataset.flashKind, f.textContent.trim()])"


@pytest.fixture(scope="module")
def app():
    needs_spa()
    return create_app("testing")


@pytest.fixture(scope="module")
def server(app):
    # Con il cookie di prova risulta collegato Mario; senza, nessun login
    with running_server(app, FakeUser("Mario")) as url:
        yield url


@pytest.fixture
def browser(server, tmp_path):
    b = Browser(find_browser(), tmp_path / "chrome")
    b.send("Page.enable")  # senza, lo script qui sotto non parte con le pagine nuove
    b.send("Page.addScriptToEvaluateOnNewDocument", source=RECORD)
    yield b
    b.close()


def _login(browser, server):
    browser.send("Network.setCookie", name=TEST_COOKIE[0], value=TEST_COOKIE[1], url=server)


# --- Flask -------------------------------------------------------------------


def test_rientro_finto_solo_in_sviluppo_e_nei_test(app, server, monkeypatch):
    client = app.test_client()
    assert client.get(PAGE).status_code == 200
    assert client.get(f"{PAGE}?demo=rientro").status_code == 200
    # P22: un ?demo= diverso da rientro è un indirizzo sbagliato (fino al lotto 9b-1 lo
    # controllava per la home Jinja anche test_pagina_home.py, con coda e vuoto)
    for query in ("?demo=altro", "?demo=coda", "?demo=", "?demo=RIENTRO"):
        assert client.get(f"{PAGE}{query}").status_code == 404, query
    # /prova-home non è più una rotta (dal lotto 9d un indirizzo senza rotta dà la SPA,
    # dove React dice "Pagina non trovata": non più 404)
    assert "/prova-home" not in {rule.rule for rule in app.url_map.iter_rules()}
    # Nella demo e in produzione la home c'è, ma senza ?demo=
    monkeypatch.setitem(app.config, "ENV_NAME", "demo")
    assert client.get(PAGE).status_code == 200
    assert client.get(f"{PAGE}?demo=rientro").status_code == 404


# --- Nel browser ---------------------------------------------------------------


@pytest.mark.parametrize("size", [(390, 844), (1280, 720)])
@pytest.mark.parametrize("query", ["", "?demo=rientro"])
def test_sfondo_pieno_e_csp_pulita(browser, server, size, query):
    width, height = size
    browser.open(f"{server}{PAGE}{query}", width, height, READY)
    assert browser.js("document.querySelectorAll('[data-bg-cards] *').length") >= 8
    assert browser.js("window.__csp") == []


def test_senza_login(browser, server):
    browser.open(f"{server}{PAGE}", 390, 844, READY)
    assert browser.js("document.title") == "Cinquecento"
    assert browser.js("window.__csp") == []
    # Il numero da GET /api/online (P82), quello vero del server
    count = presence.count()
    label = "giocatore online" if count == 1 else "giocatori online"
    assert browser.js("document.querySelector('[data-online-count]').textContent") == str(count)
    assert browser.js("document.querySelector('[data-online-label]').textContent") == label
    assert browser.js("document.querySelector('[data-resume-slot]').hidden") is True
    # Senza login la pagina non si collega al tempo reale
    browser.js("new Promise((r) => setTimeout(r, 500))")
    requests = browser.js("performance.getEntriesByType('resource').map((e) => e.name)")
    assert [name for name in requests if name.endswith("/api/online")], requests
    assert not [name for name in requests if "/socket.io/" in name], requests
    # Una carta-pulsante apre "Accedi o registrati" (P40), non l'avviso del 7a
    browser.click("[data-tile][data-kind='amico'][data-mode='2v2']")
    browser.wait_js("document.querySelector('dialog.dialog[open]') !== null", "finestra Accedi o registrati")
    assert browser.js("document.querySelector('dialog.dialog[open] h2').textContent") == "Accedi o registrati per giocare"
    assert browser.js(FLASHES) == []


def test_con_il_login(browser, server):
    _login(browser, server)
    one = ("document.querySelector('[data-online-count]')?.textContent === '1'"
           " && document.querySelector('[data-friends-panel]')?.dataset.connection === 'connected'")
    browser.open(f"{server}{PAGE}", 390, 844, f"{READY} && {one}", timeout=60)
    # home:status: io solo, al singolare (P120)
    assert browser.js("document.querySelector('[data-online-label]').textContent") == "giocatore online"
    assert browser.js("document.querySelector('[data-open-stats] .navbar__label').textContent") == "Mario"
    # Con il login una carta-pulsante apre la carta-modal, non "Accedi o registrati"
    # (carta-modal, coda e inviti: test_spa_home_coda.py e test_spa_home_inviti.py)
    browser.click("[data-tile][data-kind='amico'][data-mode='2v2']")
    browser.wait_js("document.querySelector('[data-mode-modal]')?.open === true", "carta-modal")
    assert browser.js("document.querySelector('dialog.dialog[open]')") is None
    assert browser.js("window.__csp") == []


def test_avviso_di_rientro_con_il_login(browser, server):
    _login(browser, server)
    ready = (f"{READY} && document.querySelector('[data-resume-link]') !== null"
             " && document.querySelector('[data-friends-panel]')?.dataset.connection === 'connected'")
    browser.open(f"{server}{PAGE}?demo=rientro", 390, 844, ready, timeout=60)
    # home:status vero (1 online) non sostituisce i dati finti
    browser.js("new Promise((r) => setTimeout(r, 500))")
    banner = browser.js("""(() => { const link = document.querySelector('[data-resume-link]');
      return { href: link.getAttribute('href'), game: document.querySelector('[data-resume]').dataset.resume,
               detail: link.querySelector('.resume__detail').textContent,
               text: link.textContent.replace(/\\s+/g, ' ').trim() }; })()""")
    assert banner == {"href": "/game/a1b2c3d4", "game": "a1b2c3d4", "detail": "1v1 a 500 punti",
                      "text": "playing_cardsHai una partita in corso1v1 a 500 puntiloginRientra"}
    assert browser.js("document.querySelector('[data-online]').hidden") is True
    assert browser.js("document.querySelector('[data-home]').dataset.demoState") == "rientro"


def test_carta_inclinata_sotto_il_mouse(browser, server):
    browser.open(f"{server}{PAGE}", 1280, 720, READY)
    # Con "riduci movimento" (acceso da Browser.open) la carta resta dritta
    tile = "[data-tile][data-kind='veloce'][data-mode='2v2']"
    box = browser.js(f"(() => {{ const r = document.querySelector({json.dumps(tile)}).getBoundingClientRect();"
                     " return [r.left, r.top, r.width, r.height]; })()")
    x, y = box[0] + box[2] * 0.9, box[1] + box[3] * 0.1
    browser.send("Input.dispatchMouseEvent", type="mouseMoved", x=x, y=y)
    tilt = f"document.querySelector({json.dumps(tile)}).style.getPropertyValue('--ry')"
    assert browser.js(tilt) == ""
    # Senza: verso destra e in alto (10 gradi al massimo)
    browser.send("Emulation.setEmulatedMedia", features=[{"name": "prefers-reduced-motion", "value": "no-preference"}])
    browser.send("Input.dispatchMouseEvent", type="mouseMoved", x=x - 1, y=y)
    browser.wait_js(f"{tilt} !== ''", "carta inclinata")
    values = browser.js(f"['--rx', '--ry', '--gx', '--gy'].map((n) => document.querySelector({json.dumps(tile)})"
                        ".style.getPropertyValue(n))")
    assert float(values[1].removesuffix("deg")) > 7 and float(values[0].removesuffix("deg")) > 7
    assert values[2].endswith("%") and values[3].endswith("%")
    # Il mouse esce: la carta torna dritta
    browser.send("Input.dispatchMouseEvent", type="mouseMoved", x=5, y=box[1] + box[3] + 40)
    browser.wait_js(f"{tilt} === ''", "carta di nuovo dritta")
