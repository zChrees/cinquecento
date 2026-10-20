"""Passo 7b della migrazione: carta-modal, coda e CPU nella home React (/prova-home).

Nel browser (Chrome o Edge senza finestra), con il server vero e il database dei test,
svuotato e ricreato qui con migrate.py (come test_chat_pannello.py: la suite frontend
non lo prepara). L'utente è Mario, registrato davvero, con il login finto di
running_server (FakeUser con il suo id).
Controlla:
- la carta-modal della Partita Veloce è la stessa della home Jinja (elementi,
  attributi e testi, 1v1 e 2v2, con "Giocatore" e con "CPU"), a parte il consiglio
  (a caso) e il rating (vero qui, finto nella home Jinja: "In breve" lo prende da
  GET /stats/me, e Mario ha 1500 provvisorio);
- "Gioca" con "Giocatore" apre la schermata di coda (modo, punti, intervallo, secondi);
  "Annulla" e Esc la chiudono e tolgono dalla coda; P105: con l'intervallo allargato la
  schermata resta la stessa e i numeri scorrono;
- due schede dello stesso utente: la seconda vede la coda della prima (queue:status) e
  "Annulla" da una chiude la schermata anche nell'altra (queue:left);
- con "CPU" (1v1 e 2v2) si va subito al tavolo, senza coda;
- connessione persa (P33): la schermata di coda si chiude, si esce dalla coda e "Gioca"
  è spento finché la connessione non torna.
Gli inviti ("Gioca con un amico", 7c) stanno in tests/frontend2/test_spa_home_inviti.py.
Senza browser, o senza il build della SPA, i controlli si saltano.
"""

import itertools
import json
import re

import pytest
import sqlalchemy as sa

from app import create_app
from app.extensions import db, socketio
from app.realtime import matchmaking
from app.realtime.matchmaking import matchmaker
from app.realtime.presence import presence
from app.realtime.room_manager import rooms
from app.services import auth_service
from tests.browser import (
    FONT_ORIGINS,
    TEST_COOKIE,
    Browser,
    FakeUser,
    find_browser,
    running_server,
)
from tests.frontend.test_chat_pannello import _migrate
from tests.spa import needs_spa

PAGE = "/prova-home"
PASSWORD = "Password-di-prova-7b"
SOCKET_ROUTE = "*/socket.io/*"
# Come test_csp.py: registra ogni risorsa bloccata dalla CSP
RECORD = (
    "window.__csp = [];"
    "document.addEventListener('securitypolicyviolation',"
    " e => window.__csp.push(e.effectiveDirective + ' ' + e.blockedURI));"
)
# READY: home collegata al tempo reale (il numero degli online da home:status)
CONNECTED = "document.querySelector('[data-friends-panel]')?.dataset.connection === 'connected'"
READY = f"document.querySelector('[data-online-count]')?.textContent !== '' && {CONNECTED}"
# READY_OLD: la home Jinja, collegata
READY_OLD = ("document.querySelector('[data-online-count]')?.textContent !== ''"
             " && import('/static/js/core/socket.js').then((m) => m.isConnected())")
MODAL_OPEN = "document.querySelector('[data-mode-modal]')?.open === true"
OVERLAY_OPEN = "document.querySelector('[data-queue-overlay]')?.open === true"
NO_OVERLAY = "document.querySelector('[data-queue-overlay]') === null"
# SIGNATURE: ogni elemento della carta-modal come "profondità tag attributi | testo proprio",
# con gli attributi in ordine alfabetico. Senza "checked", che React scrive come attributo
# e ModeModal.js solo come proprietà (la scelta vera si confronta a parte), senza il
# consiglio (a caso) e senza il rating tra parentesi (vero qui, finto nella home Jinja).
SIGNATURE = """(() => {
  const out = [];
  function walk(node, depth) {
    for (const child of node.children) {
      const attrs = [...child.attributes].filter((a) => a.name !== 'checked')
        .map((a) => `${a.name}=${a.value}`).sort();
      let text = [...child.childNodes].filter((n) => n.nodeType === 3)
        .map((n) => n.textContent.trim()).filter(Boolean).join(' ');
      if (child.matches('.mode-modal__tip p > span')) text = '(consiglio)';
      text = text.replace(/ \\(\\d+(, provvisorio)?\\)$/, '');
      out.push(`${depth} ${child.tagName} ${attrs.join(' ')} | ${text}`);
      walk(child, depth + 1);
    }
  }
  const dialog = document.querySelector('[data-mode-modal]');
  walk({ children: [dialog] }, 0);
  const checked = [...dialog.querySelectorAll('input:checked')].map((i) => `${i.name}=${i.value}`);
  return { out, checked };
})()"""


@pytest.fixture(scope="module")
def app():
    needs_spa()
    app = create_app("testing")
    with app.app_context():
        assert db.engine.url.database.endswith("_test")
        with db.engine.begin() as conn:
            tables = conn.execute(sa.text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE()"
            )).scalars().all()
            conn.execute(sa.text("SET FOREIGN_KEY_CHECKS = 0"))
            for table in tables:
                conn.execute(sa.text(f"DROP TABLE `{table}`"))
            conn.execute(sa.text("SET FOREIGN_KEY_CHECKS = 1"))
        _migrate(db.engine.url)
    return app


@pytest.fixture(scope="module")
def user_id(app):
    with app.app_context():
        return auth_service.register("Mario", "mario@esempio.it", PASSWORD).id


@pytest.fixture(scope="module")
def server(app, user_id):
    # Con il cookie di prova risulta collegato Mario, con il suo id vero
    with running_server(app, FakeUser("Mario", user_id)) as url:
        yield url


@pytest.fixture(autouse=True)
def clean(user_id):
    yield
    # Nessuna prova lascia l'utente in coda o una partita contro la CPU aperta
    matchmaker.leave(user_id)
    for room in rooms.rooms_of(user_id):
        room.run(room._stop_timers)
        rooms.remove(room.id)


def _browser(server, tmp_path, name):
    b = Browser(find_browser(), tmp_path / name)
    b.send("Network.setCookie", name=TEST_COOKIE[0], value=TEST_COOKIE[1], url=server)
    b.send("Page.enable")  # senza, lo script qui sotto non parte con le pagine nuove
    b.send("Page.addScriptToEvaluateOnNewDocument", source=RECORD)
    return b


@pytest.fixture
def browser(server, tmp_path):
    b = _browser(server, tmp_path, "chrome")
    yield b
    b.close()


def _open(browser, server, width=1440, height=900):
    browser.open(f"{server}{PAGE}", width, height, READY, timeout=60)


def _click(browser, selector):
    browser.js(f"document.querySelector({json.dumps(selector)}).click()")


def _open_modal(browser, mode):
    _click(browser, f'[data-tile][data-kind="veloce"][data-mode="{mode}"]')
    browser.wait_js(MODAL_OPEN, f"apertura della carta-modal {mode}")


def _escape(browser):
    for kind in ("keyDown", "keyUp"):
        browser.send("Input.dispatchKeyEvent", type=kind, key="Escape", code="Escape", windowsVirtualKeyCode=27)


def _join(browser, mode="1v1", target=150):
    _open_modal(browser, mode)
    _click(browser, f'input[name="target"][value="{target}"]')
    _click(browser, "[data-play]")
    browser.wait_js(OVERLAY_OPEN, "schermata di coda")


# --- Carta-modal ---------------------------------------------------------------


@pytest.mark.parametrize("mode", ["1v1", "2v2"])
def test_carta_modal_uguale_a_quella_della_home_jinja(browser, server, mode):
    signatures = []
    for url, ready in ((f"{server}/", READY_OLD), (f"{server}{PAGE}", READY)):
        browser.open(url, 390, 844, ready, timeout=60)
        _open_modal(browser, mode)
        player = browser.js(SIGNATURE)
        _click(browser, 'input[name="opponent"][value="cpu"]')
        browser.wait_js("document.querySelector('[data-mode-modal]').dataset.opponent === 'cpu'", "scelta della CPU")
        signatures.append((player, browser.js(SIGNATURE)))
    assert signatures[1] == signatures[0]
    assert signatures[1][0]["checked"] == ["target=500", "opponent=player"]
    assert signatures[1][1]["checked"] == ["target=500", "opponent=cpu"]
    assert browser.js("window.__csp") == []


@pytest.mark.parametrize("mode", ["1v1", "2v2"])
def test_carta_modal_con_un_amico_uguale_a_quella_della_home_jinja(browser, server, mode):
    # 7c: "Gioca con un amico" (Mario non ha amici: "Nessun amico online in questo momento.")
    signatures = []
    for url, ready in ((f"{server}/", READY_OLD), (f"{server}{PAGE}", READY)):
        browser.open(url, 390, 844, ready, timeout=60)
        _click(browser, f'[data-tile][data-kind="amico"][data-mode="{mode}"]')
        browser.wait_js(f"{MODAL_OPEN} && document.querySelector('.invite__empty') !== null", "carta-modal con un amico")
        signatures.append(browser.js(SIGNATURE))
    assert signatures[1] == signatures[0]
    assert browser.js("document.querySelector('[data-play]').disabled") is True
    assert browser.js("window.__csp") == []


def test_in_breve_con_il_rating_vero(browser, server):
    _open(browser, server)
    _open_modal(browser, "1v1")
    # Mario non ha mai giocato: 1500, provvisorio (GET /stats/me)
    browser.wait_js("document.querySelector('.facts').textContent.includes('(1500, provvisorio)')", "rating in In breve")
    assert "Conta per il tuo rating 1v1 (1500, provvisorio)" in browser.js("document.querySelector('.facts').textContent")
    # I punti cambiano la frase sotto
    _click(browser, 'input[name="target"][value="300"]')
    browser.wait_js("document.querySelector('.target__note').textContent === 'Incontri solo chi ha scelto 300 punti.'",
                    "frase dei punti")
    # X chiude, e la carta-pulsante torna visibile
    _click(browser, ".mode-modal__close")
    browser.wait_js("document.querySelector('[data-mode-modal]') === null", "carta-modal chiusa")
    assert browser.js("document.querySelector('[data-tile][data-mode=\"1v1\"]').style.visibility") == ""
    # Esc e un tocco fuori chiudono anche loro
    _open_modal(browser, "2v2")
    _escape(browser)
    browser.wait_js("document.querySelector('[data-mode-modal]') === null", "Esc sulla carta-modal")
    _open_modal(browser, "2v2")
    browser.send("Input.dispatchMouseEvent", type="mousePressed", x=5, y=5, button="left", clickCount=1)
    browser.send("Input.dispatchMouseEvent", type="mouseReleased", x=5, y=5, button="left", clickCount=1)
    browser.wait_js("document.querySelector('[data-mode-modal]') === null", "tocco fuori dalla carta-modal")


# --- Coda ----------------------------------------------------------------------


def test_coda_si_apre_e_si_annulla(browser, server, user_id):
    _open(browser, server)
    _join(browser, "1v1", 150)
    assert browser.js("document.querySelector('[data-mode-modal]')") is None
    overlay = browser.js("""(() => { const o = document.querySelector('[data-queue-overlay]');
      return {mode: o.dataset.mode, target: o.dataset.targetScore, text: o.textContent,
              kicker: o.querySelector('.queue-overlay__kicker').textContent,
              seconds: o.querySelector('[data-queue-seconds]').textContent}; })()""")
    assert overlay["mode"] == "1v1" and overlay["target"] == "150"
    assert overlay["kicker"] == "Partita Veloce · 1v1 · 150 punti"
    # Mario non ha rating (1500): l'intervallo è 1500 ± 150 (D16, P111)
    assert "Cerco un avversario" in overlay["text"] and "tra 1350 e 1650" in overlay["text"]
    assert re.fullmatch(r"\d+:\d\d", overlay["seconds"])
    assert user_id in matchmaker.queue
    # I secondi contano da soli
    browser.wait_js("document.querySelector('[data-queue-seconds]').textContent !== '0:00'", "secondi che contano", 5)
    # "Annulla": queue:leave, la schermata si chiude e si esce dalla coda
    _click(browser, "[data-queue-cancel]")
    browser.wait_js(NO_OVERLAY, "schermata di coda chiusa")
    assert user_id not in matchmaker.queue
    # Esc vale come "Annulla"
    _join(browser, "2v2", 500)
    assert "Cerco compagno e avversari" in browser.js("document.querySelector('[data-queue-overlay]').textContent")
    _escape(browser)
    browser.wait_js(NO_OVERLAY, "Esc sulla schermata di coda")
    assert user_id not in matchmaker.queue
    assert browser.js("window.__csp") == []


def test_intervallo_allargato_senza_riaprire_la_schermata(browser, server, monkeypatch):
    # P105: un queue:status nuovo della stessa coda non riapre la schermata: cambiano
    # solo i numeri, che scorrono fino ai valori nuovi
    monkeypatch.setattr(matchmaking, "RANGE_STEP_SECONDS", 1)
    _open(browser, server)
    _join(browser, "1v1", 150)
    browser.send("Emulation.setEmulatedMedia", features=[{"name": "prefers-reduced-motion", "value": "no-preference"}])
    browser.js("""(() => {
      window.__overlay = document.querySelector('[data-queue-overlay]');
      window.__mins = [];
      const tick = () => { const m = document.querySelector('[data-range-min]'); if (m) window.__mins.push(Number(m.textContent));
        if (window.__mins.length < 400) requestAnimationFrame(tick); };
      requestAnimationFrame(tick);
      return true;
    })()""")
    browser.wait_js("Number(document.querySelector('[data-range-min]')?.dataset.rangeMin) <= 1250", "intervallo allargato", 6)
    browser.wait_js("document.querySelector('[data-range-min]').textContent === document.querySelector('[data-range-min]').dataset.rangeMin",
                    "numeri arrivati", 3)
    assert browser.js("document.querySelector('[data-queue-overlay]') === window.__overlay && window.__overlay.open") is True
    assert browser.js("document.querySelectorAll('[data-queue-overlay]').length") == 1
    mins = browser.js("window.__mins")
    assert all(abs(a - b) <= 30 for a, b in itertools.pairwise(mins)), mins
    assert any(1250 < m < 1350 for m in mins), mins
    text = browser.js("document.querySelector('[data-queue-range]').textContent")
    assert re.fullmatch(r"Avversari con rating tra \d+ e \d+", text), text


def test_due_schede_stessa_coda(browser, server, tmp_path, user_id):
    _open(browser, server)
    _join(browser, "1v1", 300)
    other = _browser(server, tmp_path, "chrome2")
    try:
        # La seconda scheda riceve la coda della prima appena si collega (queue:status)
        other.open(f"{server}{PAGE}", 1440, 900, f"{READY} && {OVERLAY_OPEN}", timeout=60)
        assert other.js("document.querySelector('[data-queue-overlay]').dataset.targetScore") == "300"
        # "Annulla" dalla seconda: si chiude anche nella prima (queue:left)
        _click(other, "[data-queue-cancel]")
        other.wait_js(NO_OVERLAY, "schermata chiusa nella seconda scheda")
        browser.wait_js(NO_OVERLAY, "schermata chiusa nella prima scheda")
        assert user_id not in matchmaker.queue
    finally:
        other.close()


# --- CPU -----------------------------------------------------------------------


@pytest.mark.parametrize(("mode", "target", "players"), [("1v1", 150, 2), ("2v2", 300, 4)])
def test_contro_la_cpu_si_va_subito_al_tavolo(browser, server, user_id, mode, target, players):
    _open(browser, server)
    _open_modal(browser, mode)
    _click(browser, 'input[name="opponent"][value="cpu"]')
    browser.wait_js("document.querySelector('.target__note').hidden === true", "frase dei punti nascosta con la CPU")
    facts = browser.js("document.querySelector('.facts').textContent")
    assert "Parte subito, senza coda" in facts and "Non conta per il rating" in facts
    _click(browser, f'input[name="target"][value="{target}"]')
    _click(browser, "[data-play]")
    browser.wait_js("location.pathname.startsWith('/game/')", "tavolo contro la CPU", 10)
    room = rooms.get(browser.js("location.pathname").split("/")[2])
    assert room is not None and len(room.players) == players and room.rated is False
    assert len(room.cpu_seats) == players - 1
    assert user_id not in matchmaker.queue


# --- Connessione (P33) -----------------------------------------------------------


def _intercept(browser):
    browser.send("Fetch.enable", patterns=[{"urlPattern": p} for p in (*FONT_ORIGINS, *browser.routes)])


def test_connessione_persa_chiude_la_coda_e_spegne_gioca(browser, server, user_id):
    _open(browser, server)
    _join(browser, "1v1", 150)
    # Il browser rifiuta /socket.io/ e il server chiude i collegamenti (come un calo di rete)
    browser.routes[SOCKET_ROUTE] = lambda _request: (503, {"ok": False})
    _intercept(browser)
    for sid in presence.tabs_of(user_id):
        socketio.server.eio.disconnect(socketio.server.manager.eio_sid_from_sid(sid, "/"))
    # La pagina si accorge della connessione persa qualche istante dopo il server
    browser.wait_js("document.querySelector('[data-friends-panel]')?.dataset.connection !== 'connected'",
                    "connessione persa vista dalla pagina", 15)
    browser.wait_js(NO_OVERLAY, "schermata di coda chiusa senza connessione")
    assert user_id not in matchmaker.queue   # chi resta senza schede esce dalla coda
    _open_modal(browser, "1v1")
    assert browser.js("document.querySelector('[data-play]').disabled") is True
    # La connessione torna: "Gioca" si riaccende
    browser.routes.pop(SOCKET_ROUTE, None)
    _intercept(browser)
    browser.wait_js("document.querySelector('[data-play]').disabled === false", "Gioca di nuovo attivo", 30)


def test_volo_della_carta_con_le_animazioni(browser, server):
    # Gli altri test hanno "riduci movimento" (niente volo): qui la carta vola davvero,
    # la carta-pulsante si nasconde durante il volo e torna quando la carta-modal è chiusa
    _open(browser, server)
    browser.send("Emulation.setEmulatedMedia", features=[{"name": "prefers-reduced-motion", "value": "no-preference"}])
    tile = '[data-tile][data-kind="veloce"][data-mode="2v2"]'
    _click(browser, tile)
    browser.wait_js(MODAL_OPEN, "apertura della carta-modal")
    assert browser.js(f"document.querySelector({json.dumps(tile)}).style.visibility") == "hidden"
    assert browser.js("document.querySelector('.mode-modal__flip').getAnimations().length") == 1
    # Il retro della carta grande è la copia della carta-pulsante
    assert browser.js("document.querySelector('.mode-modal__back > .mode-tile--purple .mode-tile__label')?.textContent") == "2v2"
    browser.wait_js("document.querySelector('.mode-modal__flip').getAnimations().length === 0", "volo di apertura finito", 5)
    _click(browser, ".mode-modal__close")
    browser.wait_js("document.querySelector('[data-mode-modal]')?.classList.contains('is-closing')", "volo di chiusura")
    browser.wait_js("document.querySelector('[data-mode-modal]') === null", "carta-modal chiusa dopo il volo", 5)
    assert browser.js(f"document.querySelector({json.dumps(tile)}).style.visibility") == ""
