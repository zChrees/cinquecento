"""Passo 5c della migrazione: la chat in React (frontend/src/components/ChatWindow.tsx).

Gli stessi controlli di test_chat_pannello.py (P46, P48, P81, P128), sulla pagina
della SPA con il login (/prova-react, fino al passo 6): aprire la chat azzera i non
letti; a 360×640 la casella si vede, accetta al massimo 1000 caratteri (come
CHAT_MAX_LENGTH di config.py) e un messaggio di soli spazi si rifiuta; dopo "Invia" la
casella tiene il fuoco e un doppio clic manda un solo messaggio; un messaggio
dell'amico arriva nella chat aperta, suona e si segna come letto; "indietro" porta
dalla chat alla lista e poi chiude, la X dalla chat chiude tutto; con pochi messaggi
stanno in fondo anche con la tastiera aperta; un trascinamento dove niente scorre non
muove la pagina dietro.

Nel browser (Chrome o Edge senza finestra), con il server vero e il database dei
test, svuotato e ricreato qui con migrate.py come in test_chat_pannello.py: Mario e
Giulia sono amici, Giulia ha mandato 3 messaggi non letti. Senza browser, o senza il
build della SPA, i controlli nel browser si saltano.
"""

import json
import re
import time
import uuid
from pathlib import Path

import pytest
import sqlalchemy as sa

from app import create_app
from app.extensions import db, socketio
from app.realtime.events import user_channel
from app.repositories import chat_repo
from app.services import auth_service, chat_service, friend_service
from config import load_config
from tests.browser import TEST_COOKIE, Browser, FakeUser, find_browser, running_server
from tests.frontend.test_chat_pannello import _migrate
from tests.spa import needs_spa

ROOT = Path(__file__).resolve().parents[2]
CHAT_TSX = (ROOT / "frontend" / "src" / "components" / "ChatWindow.tsx").read_text(encoding="utf-8")
PASSWORD = "Password-di-prova-1"
UNREAD = 3
PAGE = "/prova-react"
CHAT = "document.querySelector('[data-view=\"chat\"]')"
PANEL_OPEN = "document.querySelector('[data-friends-panel]')?.open === true"
CONNECTED = "document.querySelector('[data-spa-connection=\"connected\"]') !== null"
BADGE = ("Number(document.querySelector('[data-friends-badge]').hidden ? 0"
         " : document.querySelector('[data-friends-badge]').textContent)")
SEND = "[data-chat-form] button[type=submit]"
FOCUSED = "document.activeElement === document.querySelector('#chat-input')"
RECORD_SOUNDS = (
    "window.__sounds = [];"
    "document.addEventListener('cinquecento:sound', (e) => window.__sounds.push(e.detail.name));"
)


def test_limite_della_chat_uguale_al_server():
    limit = re.search(r"export const MAX_LENGTH = (\d+);", CHAT_TSX).group(1)
    assert limit == str(load_config("testing").CHAT_MAX_LENGTH)


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
def users(app):
    with app.app_context():
        mario = auth_service.register("Mario", "mario@esempio.it", PASSWORD).id
        giulia = auth_service.register("Giulia", "giulia@esempio.it", PASSWORD).id
        friend_service.send_request(mario, uuid.uuid4().hex, "Giulia")
        friend_service.accept_request(giulia, mario)
        chat_repo.add(mario, giulia, "ciao Giulia", chat_repo.utc_now())
        for n in range(UNREAD):
            chat_repo.add(giulia, mario, f"messaggio {n}", chat_repo.utc_now())
        db.session.commit()
    return {"Mario": mario, "Giulia": giulia}


@pytest.fixture(scope="module")
def server(app, users):
    with running_server(app, FakeUser("Mario", users["Mario"])) as url:
        yield url


@pytest.fixture
def browser(server, tmp_path):
    # Un browser nuovo per ogni test: la cronologia di un test non passa al successivo
    b = Browser(find_browser(), tmp_path / "chrome")
    b.send("Network.setCookie", name=TEST_COOKIE[0], value=TEST_COOKIE[1], url=server)
    yield b
    b.close()


def _open_chat(browser, server, friend_id, width, height):
    # Collegati al tempo reale prima di tutto: senza, chat:history non parte
    browser.open(f"{server}{PAGE}", width, height, CONNECTED, timeout=60)
    browser.click("[data-friends-button]")
    browser.wait_js(f"document.querySelector(\"[data-chat-open='{friend_id}']\") !== null", "lista degli amici")
    browser.click(f"[data-chat-open='{friend_id}']")
    browser.wait_js(f"{CHAT} !== null", "apertura della chat")


def _real_clicks(browser, selector, count=1):
    """`count` clic veri del mouse al centro di `selector` (il pulsante prende il fuoco come con un tocco)."""
    point = browser.js(f"""(() => {{
      const b = document.querySelector({json.dumps(selector)}).getBoundingClientRect();
      return {{ x: b.left + b.width / 2, y: b.top + b.height / 2 }};
    }})()""")
    for _ in range(count):
        for kind in ("mousePressed", "mouseReleased"):
            browser.send("Input.dispatchMouseEvent", type=kind, x=point["x"], y=point["y"], button="left", clickCount=1)


def _write(browser, text, user_id):
    """Scrive `text` nella casella come da tastiera e conta da qui le volte che perde il fuoco."""
    chat_service.rate_limit.give_back(user_id)  # il messaggio del test prima non conta (1 al secondo, P48)
    browser.js("""(() => { const input = document.querySelector('#chat-input');
      input.focus(); window.blurs = 0; input.addEventListener('blur', () => { window.blurs += 1; }); })()""")
    browser.send("Input.insertText", text=text)


def _unread_for_mario(app, users):
    with app.app_context():
        db.session.rollback()  # una lettura nuova, non quella della transazione di prima (P45)
        return friend_service.overview(users["Mario"])["counters"]["unread_messages"]


def test_aprire_la_chat_azzera_i_non_letti(browser, server, users):
    browser.open(f"{server}{PAGE}", 390, 844, f"{CONNECTED} && {BADGE} === {UNREAD}", timeout=60)
    browser.click("[data-friends-button]")
    browser.wait_js(f"document.querySelector(\"[data-chat-open='{users['Giulia']}']\") !== null", "lista degli amici")
    unread = browser.js(f"document.querySelector('[data-user-id=\"{users['Giulia']}\"] [data-unread]').dataset.unread")
    assert unread == str(UNREAD)
    browser.click(f"[data-chat-open='{users['Giulia']}']")
    browser.wait_js(f"{CHAT} !== null", "apertura della chat")
    assert browser.js("document.querySelectorAll('.chat__msg').length") == UNREAD + 1
    assert browser.js("document.querySelectorAll('.chat__msg--mine').length") == 1
    assert browser.js("document.querySelector('#chat-title').textContent") == "Giulia"
    assert browser.js("document.querySelector('[data-view=\"list\"]').hidden") is True
    assert browser.js(BADGE) == 0


def test_a_360_il_campo_si_vede_e_i_limiti(browser, server, users):
    _open_chat(browser, server, users["Giulia"], 360, 640)
    field = browser.js("(() => { const r = document.querySelector('#chat-input').getBoundingClientRect();"
                       " return {top: r.top, bottom: r.bottom, vh: innerHeight}; })()")
    assert 0 <= field["top"] and field["bottom"] <= field["vh"]
    assert browser.js("document.querySelector('#chat-input').maxLength") == 1000
    # Messaggio di soli spazi: rifiutato nella pagina, non parte niente
    count = browser.js("document.querySelectorAll('.chat__msg').length")
    _write(browser, "   ", users["Mario"])
    browser.click(SEND)
    browser.wait_js("document.querySelector('[data-chat-error]').textContent === 'Scrivi un messaggio.'", "errore")
    assert browser.js("document.querySelector('[data-chat-error]').hidden") is False
    assert browser.js("document.querySelectorAll('.chat__msg').length") == count


def test_invia_tiene_il_fuoco_e_il_doppio_clic_manda_un_messaggio(browser, server, users):
    # P81: toccando "Invia" il fuoco passava al pulsante e il telefono chiudeva la tastiera
    _open_chat(browser, server, users["Giulia"], 360, 640)
    mine = browser.js("document.querySelectorAll('.chat__msg--mine').length")
    _write(browser, "una volta sola", users["Mario"])
    _real_clicks(browser, SEND, 2)
    assert browser.js("document.querySelector('#chat-input').disabled") is False
    assert browser.js(FOCUSED) is True
    browser.wait_js(f"document.querySelectorAll('.chat__msg--mine').length === {mine + 1}", "messaggio inviato")
    browser.wait_js(f"document.querySelector('{SEND}').disabled === false || document.querySelector('#chat-input').value === ''",
                    "invio finito")
    assert browser.js("document.querySelectorAll('.chat__msg--mine').length") == mine + 1
    assert browser.js("[...document.querySelectorAll('.chat__msg--mine')].pop().firstChild.textContent") == "una volta sola"
    assert browser.js("document.querySelector('[data-chat-error]').hidden") is True
    assert browser.js(FOCUSED) is True
    assert browser.js("window.blurs") == 0
    assert browser.js("document.querySelector('#chat-input').value") == ""


def test_messaggio_dell_amico_nella_chat_aperta(browser, server, users, app):
    browser.send("Page.enable")
    browser.send("Page.addScriptToEvaluateOnNewDocument", source=RECORD_SOUNDS)
    _open_chat(browser, server, users["Giulia"], 390, 844)
    count = browser.js("document.querySelectorAll('.chat__msg').length")
    # Giulia scrive (come chat:send dalla sua scheda): il server lo recapita a Mario
    chat_service.rate_limit.give_back(users["Giulia"])
    with app.app_context():
        message = chat_service.send(users["Giulia"], uuid.uuid4().hex, users["Mario"], "ci sei?")["message"]
        socketio.emit("chat:message", {"message": message}, to=user_channel(users["Mario"]))
    browser.wait_js(f"document.querySelectorAll('.chat__msg').length === {count + 1}", "messaggio arrivato")
    assert browser.js("[...document.querySelectorAll('.chat__msg')].pop().firstChild.textContent") == "ci sei?"
    assert browser.js("window.__sounds") == ["message"]
    # La chat è aperta: chat:read lo segna come letto
    deadline = time.monotonic() + 10
    while _unread_for_mario(app, users) != 0 and time.monotonic() < deadline:
        time.sleep(0.1)
    assert _unread_for_mario(app, users) == 0
    # Lo stesso messaggio ricevuto di nuovo (per esempio dopo un ricollegamento) non si duplica
    with app.app_context():
        socketio.emit("chat:message", {"message": message}, to=user_channel(users["Mario"]))
    browser.js("new Promise((r) => setTimeout(r, 300))")
    assert browser.js(f"document.querySelectorAll('[data-message-id=\"{message['id']}\"]').length") == 1


def test_indietro_dalla_chat_alla_lista_poi_chiude(browser, server, users):
    _open_chat(browser, server, users["Giulia"], 1440, 900)
    browser.js("history.back()")
    browser.wait_js(f"{CHAT} === null && {PANEL_OPEN}", "ritorno alla lista")
    assert browser.js("document.querySelector('[data-view=\"list\"]').hidden") is False
    browser.js("history.back()")
    browser.wait_js("document.querySelector('[data-friends-panel]').open === false", "chiusura con indietro")
    # La freccia "Torna agli amici" e la X dalla chat
    browser.click("[data-friends-button]")
    browser.wait_js(f"document.querySelector(\"[data-chat-open='{users['Giulia']}']\") !== null", "lista degli amici")
    browser.click(f"[data-chat-open='{users['Giulia']}']")
    browser.wait_js(f"{CHAT} !== null", "chat riaperta")
    browser.click("[data-chat-back]")
    browser.wait_js(f"{CHAT} === null && {PANEL_OPEN}", "ritorno alla lista con la freccia")
    browser.click(f"[data-chat-open='{users['Giulia']}']")
    browser.wait_js(f"{CHAT} !== null", "chat riaperta")
    browser.click("[data-view='chat'] .drawer__head .icon-btn[aria-label='Chiudi']")
    browser.wait_js("document.querySelector('[data-friends-panel]').open === false", "chiusura con la X dalla chat")
    # Tutti i passi del pannello sono stati tolti: si riapre normalmente sulla lista
    browser.click("[data-friends-button]")
    browser.wait_js(f"{PANEL_OPEN} && {CHAT} === null", "riapertura sulla lista")


# P128: dove stanno l'ultimo messaggio, l'elenco e la casella
LAST = """(() => {
  const msgs = [...document.querySelectorAll('.chat__msg')];
  const last = msgs[msgs.length - 1].getBoundingClientRect();
  const list = document.querySelector('[data-chat-messages]').getBoundingClientRect();
  const form = document.querySelector('[data-chat-form]').getBoundingClientRect();
  return { lastTop: last.top, lastBottom: last.bottom, listTop: list.top, listBottom: list.bottom,
           formTop: form.top, firstTop: msgs[0].getBoundingClientRect().top };
})()"""


def test_pochi_messaggi_attaccati_in_fondo_anche_con_la_tastiera(browser, server, users):
    _open_chat(browser, server, users["Giulia"], 390, 844)
    where = browser.js(LAST)
    assert where["listBottom"] - 16 <= where["lastBottom"] <= where["listBottom"], where  # in fondo
    assert where["firstTop"] - where["listTop"] > 100, where  # lo spazio vuoto è sopra
    # La tastiera accorcia lo schermo: gli ultimi messaggi restano visibili sopra la casella
    browser.send("Emulation.setDeviceMetricsOverride", width=390, height=420, deviceScaleFactor=1, mobile=False)
    browser.wait_js("innerHeight === 420", "schermo più basso")
    browser.wait_js(f"(() => {{ const w = {LAST}; return w.lastBottom <= w.listBottom + 1"
                    " && w.lastTop >= w.listTop; })()", "ultimo messaggio visibile", 3)
    where = browser.js(LAST)
    assert where["listBottom"] <= where["formTop"] + 1, where


def _touch_drag(browser, selector, fingers=1):
    """Un trascinamento verso l'alto su `selector`; restituisce se il touchmove è stato bloccato."""
    point = browser.js(f"""(() => {{ const b = document.querySelector({selector!r}).getBoundingClientRect();
      window.__moves = [];
      document.addEventListener('touchmove', (e) => setTimeout(() => window.__moves.push(e.defaultPrevented)),
                                {{ once: true }});
      return {{ x: b.left + b.width / 2, y: b.top + b.height / 2 }}; }})()""")

    def points(dy):
        return [{"x": point["x"] + 30 * i, "y": point["y"] + dy, "id": i} for i in range(fingers)]

    browser.send("Input.dispatchTouchEvent", type="touchStart", touchPoints=points(0))
    browser.send("Input.dispatchTouchEvent", type="touchMove", touchPoints=points(-40))
    browser.send("Input.dispatchTouchEvent", type="touchEnd", touchPoints=[])
    browser.wait_js("window.__moves.length === 1", "touchmove", 3)
    return browser.js("window.__moves[0]")


def test_trascinare_dove_non_si_scorre_non_muove_la_pagina_dietro(browser, server, users):
    # P128: su iPhone, con la chat vuota (o cercando un amico) si scorreva fino a vedere la pagina dietro
    browser.send("Emulation.setTouchEmulationEnabled", enabled=True, maxTouchPoints=5)
    _open_chat(browser, server, users["Giulia"], 390, 844)
    assert _touch_drag(browser, ".chat .drawer__head") is True  # la testata non scorre
    assert _touch_drag(browser, "[data-chat-messages]") is True  # pochi messaggi: l'elenco non scorre
    assert _touch_drag(browser, ".chat .drawer__head", fingers=2) is False  # lo zoom con due dita resta
    browser.send("Emulation.setDeviceMetricsOverride", width=390, height=300, deviceScaleFactor=1, mobile=False)
    browser.wait_js("(() => { const l = document.querySelector('[data-chat-messages]');"
                    " return l.scrollHeight > l.clientHeight; })()", "elenco che scorre", 3)
    assert _touch_drag(browser, ".chat__msg") is False  # un elenco che scorre scorre
