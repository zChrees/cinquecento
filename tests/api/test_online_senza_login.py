"""P82: giocatori online veri nella home anche senza login (contratto 5.1).

- GET /api/online (fino al lotto 9c /online) risponde a tutti, anche senza login, con il solo numero degli utenti
  collegati (lo stesso di home:status) e senza cache.
- Nel browser, senza login: la home mostra il numero vero (anche 0), mai quello finto
  dei dati di prova (24); il numero si aggiorna quando qualcuno entra o esce; con la
  scheda nascosta la pagina smette di chiederlo e riprende quando torna visibile.
  Per non aspettare i 15 s veri, uno script nella pagina accorcia solo i timer da
  15 s (ONLINE_POLL_MS di pages/HomePage.tsx) a 0,3 s.
Non serve MySQL: chi è online lo sa presence.py, in memoria; i test aggiungono e
tolgono schede finte (utenti 9001 e 9002, che non esistono).
Se né Chrome né Edge sono installati, o manca il build della SPA, i controlli nel
browser si saltano. Fino al lotto 9b-1 si provava la home Jinja (home.js); da allora
la home React, su /.
"""

import json

import pytest

from app import create_app
from app.realtime.presence import presence
from tests.browser import Browser, find_browser, running_server
from tests.spa import needs_spa

FAKE_TABS = [(9001, "p82-a"), (9001, "p82-b"), (9002, "p82-c")]
DEMO_COUNT = "24"  # il numero finto di app/static/dev/home_esempio.json

# Prima della pagina: timer da 15 s accorciati, ogni numero mostrato e ogni GET /api/online
# ricordati, e document.hidden comandabile dal test. React disegna il numero dopo il
# caricamento: l'osservatore guarda tutta la pagina e ricorda il numero quando cambia
EARLY = """
(() => {
  const original = window.setTimeout;
  window.setTimeout = (fn, ms, ...rest) => original(fn, ms === 15000 ? 300 : ms, ...rest);
  window.__counts = [];
  window.__onlineRequests = 0;
  const fetchOriginal = window.fetch;
  window.fetch = (url, ...rest) => {
    if (String(url).endsWith('/api/online')) window.__onlineRequests += 1;
    return fetchOriginal(url, ...rest);
  };
  window.__hidden = false;
  Object.defineProperty(Document.prototype, 'hidden', { get: () => window.__hidden, configurable: true });
  document.addEventListener('DOMContentLoaded', () => {
    let last = null;
    new MutationObserver(() => {
      const count = document.querySelector('[data-online-count]');
      if (count !== null && count.textContent !== last) {
        last = count.textContent;
        window.__counts.push(last);
      }
    }).observe(document.body, { childList: true, characterData: true, subtree: true });
  });
})();
"""

COUNT = "document.querySelector('[data-online-count]').textContent"
SHOWN = "!document.querySelector('[data-online]').hidden"


@pytest.fixture
def fake_tabs():
    """Toglie alla fine le schede finte aggiunte da un test."""
    yield
    for user_id, sid in FAKE_TABS:
        presence.remove(user_id, sid)


# --- La rotta ---------------------------------------------------------------------


def test_numero_degli_online_senza_login(fake_tabs):
    client = create_app("testing").test_client()
    before = presence.count()
    response = client.get("/api/online")
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert response.get_json() == {"ok": True, "data": {"online_count": before}}

    # Lo stesso utente con due schede conta una volta (come home:status)
    for user_id, sid in FAKE_TABS:
        presence.add(user_id, sid)
    assert client.get("/api/online").get_json()["data"] == {"online_count": before + 2}
    presence.remove(9001, "p82-a")
    assert client.get("/api/online").get_json()["data"] == {"online_count": before + 2}
    presence.remove(9001, "p82-b")
    assert client.get("/api/online").get_json()["data"] == {"online_count": before + 1}


def test_solo_lettura():
    client = create_app("testing").test_client()
    assert client.post("/api/online").status_code == 405


# --- Nel browser ------------------------------------------------------------------


@pytest.fixture(scope="module")
def server():
    needs_spa()
    with running_server(create_app("testing")) as url:  # senza utente finto: nessun login
        yield url


@pytest.fixture(scope="module")
def browser(server, tmp_path_factory):
    b = Browser(find_browser(), tmp_path_factory.mktemp("chrome"))
    b.send("Page.enable")  # senza, lo script qui sotto non entra nelle pagine
    b.send("Page.addScriptToEvaluateOnNewDocument", source=EARLY)
    yield b
    b.close()


def _open(browser, server):
    ready = f"document.querySelector('[data-online]:not([hidden])') !== null && {COUNT} === '{presence.count()}'"
    browser.open(f"{server}/", 390, 844, ready, timeout=100)
    # Senza login la navbar ha "Accedi" al posto dell'avatar con le statistiche
    assert browser.js("document.querySelector('[data-open-stats]') === null") is True


def test_senza_login_il_numero_vero_anche_zero(browser, server, fake_tabs):
    _open(browser, server)
    assert browser.js(COUNT) == str(presence.count())
    # Il numero finto dei dati di prova non compare mai, nemmeno per un attimo
    assert DEMO_COUNT not in json.loads(browser.js("JSON.stringify(window.__counts)"))

    before = presence.count()
    presence.add(9001, "p82-a")
    browser.wait_js(f"{COUNT} === '{before + 1}'", "il numero sale quando qualcuno entra")
    presence.remove(9001, "p82-a")
    browser.wait_js(f"{COUNT} === '{before}'", "il numero scende quando qualcuno esce")
    assert DEMO_COUNT not in json.loads(browser.js("JSON.stringify(window.__counts)"))


def test_con_la_scheda_nascosta_non_chiede_il_numero(browser, server, fake_tabs):
    _open(browser, server)
    browser.wait_js("window.__onlineRequests >= 2", "richieste ripetute con la scheda visibile")
    browser.js("window.__hidden = true; document.dispatchEvent(new Event('visibilitychange')); 0")
    browser.js("new Promise((done) => setTimeout(done, 200))")  # una risposta già partita arriva
    asked = browser.js("window.__onlineRequests")
    presence.add(9002, "p82-c")
    browser.js("new Promise((done) => setTimeout(done, 1200))")  # 4 giri da 0,3 s
    assert browser.js("window.__onlineRequests") == asked
    assert browser.js(COUNT) == str(presence.count() - 1)

    # Tornata visibile, chiede subito il numero nuovo
    browser.js("window.__hidden = false; document.dispatchEvent(new Event('visibilitychange')); 0")
    browser.wait_js(f"{COUNT} === '{presence.count()}'", "numero aggiornato al ritorno")
