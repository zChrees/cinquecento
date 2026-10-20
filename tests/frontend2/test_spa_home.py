"""Passo 7a della migrazione: la home React (frontend/src/pages/HomePage.tsx) su /prova-home.

Controlla:
- /prova-home c'è solo in sviluppo e nei test (altrove 404) e accetta solo ?demo=rientro;
- nel browser, la stessa pagina della home Jinja (/): stessi elementi, classi, data-* e
  testi in <main>, e la stessa cascata di carte dello sfondo, a 390×844 e 1280×720,
  anche con ?demo=rientro (l'avviso "Hai una partita in corso");
- senza login: il numero degli online da GET /online, nessun collegamento al tempo
  reale, una carta-pulsante apre "Accedi o registrati", la CSP non blocca niente;
- con il login: il numero da home:status ("1 giocatore online", al singolare), una
  carta-pulsante mostra l'avviso provvisorio del 7a (ogni volta), e con ?demo=rientro
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

PAGE = "/prova-home"
# Come test_csp.py: registra ogni risorsa bloccata dalla CSP
RECORD = (
    "window.__csp = [];"
    "document.addEventListener('securitypolicyviolation',"
    " e => window.__csp.push(e.effectiveDirective + ' ' + e.blockedURI));"
)
# READY: la home (Jinja o React) ha lo sfondo pieno e il numero degli online o l'avviso di rientro
READY = ("document.querySelector('h1') !== null"
         " && document.querySelectorAll('[data-bg-cards] > *').length > 0"
         " && (document.querySelector('[data-online]:not([hidden])') !== null"
         " || document.querySelector('[data-resume-slot]:not([hidden])') !== null)")
# SIGNATURE: ogni elemento sotto `root` come "profondità tag attributi | testo proprio";
# gli attributi in ordine alfabetico (React e Jinja li scrivono in ordini diversi).
# Si saltano i data-demo-*-url della home Jinja (gli indirizzi dei dati finti, che la
# home React non usa) e, con `skip`, il contenuto degli elementi indicati.
SIGNATURE = """((selector, skip) => {
  const out = [];
  function walk(node, depth) {
    for (const child of node.children) {
      const attrs = [...child.attributes]
        .filter((a) => !(a.name.startsWith('data-demo-') && a.name.endsWith('-url')))
        .map((a) => `${a.name}=${a.value}`).sort();
      const text = [...child.childNodes].filter((n) => n.nodeType === 3)
        .map((n) => n.textContent.trim()).filter(Boolean).join(' ');
      out.push(`${depth} ${child.tagName} ${attrs.join(' ')} | ${text}`);
      if (!(skip && child.matches(skip))) walk(child, depth + 1);
    }
  }
  walk(document.querySelector(selector), 0);
  return out;
})"""
FLASHES = "[...document.querySelectorAll('[data-flash] .flash')].map((f) => [f.dataset.flashKind, f.textContent.trim()])"
PREVIEW = "La scelta della modalità arriva con il prossimo lotto della migrazione (7b)."


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


def _signature(browser, selector, skip=None):
    return browser.js(f"{SIGNATURE}({json.dumps(selector)}, {json.dumps(skip)})")


def _login(browser, server):
    browser.send("Network.setCookie", name=TEST_COOKIE[0], value=TEST_COOKIE[1], url=server)


# --- Flask -------------------------------------------------------------------


def test_solo_in_sviluppo_e_nei_test(app, server, monkeypatch):
    client = app.test_client()
    assert client.get(PAGE).status_code == 200
    assert client.get(f"{PAGE}?demo=rientro").status_code == 200
    assert client.get(f"{PAGE}?demo=altro").status_code == 404
    # Nella demo e in produzione la pagina non c'è
    monkeypatch.setitem(app.config, "ENV_NAME", "demo")
    assert client.get(PAGE).status_code == 404
    assert client.get(f"{PAGE}?demo=rientro").status_code == 404


# --- Nel browser ---------------------------------------------------------------


@pytest.mark.parametrize("size", [(390, 844), (1280, 720)])
@pytest.mark.parametrize("query", ["", "?demo=rientro"])
def test_stessa_pagina_della_home_jinja(browser, server, size, query):
    width, height = size
    browser.open(f"{server}/{query}", width, height, READY)
    old_main = _signature(browser, "main", "[data-bg-cards]")
    old_background = _signature(browser, "[data-bg-cards]")
    browser.open(f"{server}{PAGE}{query}", width, height, READY)
    assert _signature(browser, "main", "[data-bg-cards]") == old_main
    assert _signature(browser, "[data-bg-cards]") == old_background
    assert 8 <= len(old_background) and browser.js("window.__csp") == []


def test_senza_login(browser, server):
    browser.open(f"{server}{PAGE}", 390, 844, READY)
    assert browser.js("document.title") == "Cinquecento"
    assert browser.js("window.__csp") == []
    # Il numero da GET /online (P82), quello vero del server
    count = presence.count()
    label = "giocatore online" if count == 1 else "giocatori online"
    assert browser.js("document.querySelector('[data-online-count]').textContent") == str(count)
    assert browser.js("document.querySelector('[data-online-label]').textContent") == label
    assert browser.js("document.querySelector('[data-resume-slot]').hidden") is True
    # Senza login la pagina non si collega al tempo reale
    browser.js("new Promise((r) => setTimeout(r, 500))")
    requests = browser.js("performance.getEntriesByType('resource').map((e) => e.name)")
    assert [name for name in requests if name.endswith("/online")], requests
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
    # Le carte-pulsante, per ora, mostrano l'avviso provvisorio (la carta-modal arriva con il 7b)
    browser.click("[data-tile][data-kind='veloce'][data-mode='1v1']")
    browser.wait_js("document.querySelector('[data-flash] .flash') !== null", "avviso provvisorio")
    assert browser.js(FLASHES) == [["info", f"info{PREVIEW}"]]
    assert browser.js("document.querySelector('dialog.dialog[open]')") is None
    # Un secondo clic lo ripropone da capo (un elemento nuovo, che riparte con l'animazione)
    browser.js("window.__first = document.querySelector('[data-flash] .flash'); true")
    browser.click("[data-tile][data-kind='amico'][data-mode='1v1']")
    browser.wait_js("document.querySelector('[data-flash] .flash') !== window.__first", "avviso di nuovo")
    assert browser.js(FLASHES) == [["info", f"info{PREVIEW}"]]
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
    # Senza: verso destra e in alto, come initTilt di home.js (10 gradi al massimo)
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
