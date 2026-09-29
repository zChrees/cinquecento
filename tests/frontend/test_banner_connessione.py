"""P33: avviso della connessione e pulsanti spenti senza connessione.

Nel browser (Chrome o Edge senza finestra, tests/browser.py), con il server vero e il
database dei test (svuotato e ricreato qui con migrate.py, come in test_chat_vera.py):
Mario e Giulia sono amici. La connessione "cade" così: il browser rifiuta le richieste
a /socket.io/ (la pagina non riesce a ricollegarsi) e il server chiude il collegamento
aperto; togliendo il blocco la pagina si ricollega da sola, come dopo un calo di rete.
Controlla: "Connessione persa" in cima alla pagina, "Gioca" e "Invia" spenti, al
ritorno avviso tolto, pulsanti di nuovo attivi e messaggi arrivati nel frattempo nella
chat aperta; lo scollegamento deciso dal server ("Esci" da un'altra scheda, P32) con
"Ricarica"; l'avviso al primo collegamento solo se ci mette più di 3 secondi.
Se né Chrome né Edge sono installati i controlli nel browser si saltano.
"""

import importlib.util
import uuid
from pathlib import Path

import pytest
import sqlalchemy as sa

from app import create_app
from app.extensions import db, socketio
from app.realtime.presence import disconnect_user, presence
from app.services import auth_service, chat_service, friend_service
from tests.browser import (
    FONT_ORIGINS,
    TEST_COOKIE,
    Browser,
    FakeUser,
    find_browser,
    running_server,
)

ROOT = Path(__file__).resolve().parents[2]
PASSWORD = "Password-di-prova-1"
SOCKET_ROUTE = "*/socket.io/*"
BANNER = "document.querySelector('[data-banner]')"
ONLINE = "document.querySelector('[data-online-count]')?.textContent === '1'"
PLAY = "document.querySelector('[data-mode-modal] [data-play]')"
CHAT = "document.querySelector('[data-view=\"chat\"]')"
SEND = "document.querySelector('[data-chat-form] button[type=submit]')"


def _migrate(url):
    spec = importlib.util.spec_from_file_location("migrate", ROOT / "scripts" / "migrate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.migrate(url, report=lambda _msg: None)


@pytest.fixture(scope="module")
def app():
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
        db.session.commit()
    return {"Mario": mario, "Giulia": giulia}


@pytest.fixture(scope="module")
def server(app, users):
    app.config["CHAT_MIN_INTERVAL_SECONDS"] = 0
    with running_server(app, FakeUser("Mario", users["Mario"])) as url:
        yield url


@pytest.fixture
def browser(server, tmp_path):
    b = Browser(find_browser(), tmp_path / "chrome")
    b.send("Network.setCookie", name=TEST_COOKIE[0], value=TEST_COOKIE[1], url=server)
    yield b
    b.close()


def _intercept(browser):
    browser.send("Fetch.enable", patterns=[{"urlPattern": p} for p in (*FONT_ORIGINS, *browser.routes)])


def _block_socket(browser):
    """Il browser rifiuta le richieste a /socket.io/: la pagina non riesce a ricollegarsi."""
    browser.routes[SOCKET_ROUTE] = lambda _request: (503, {"ok": False})
    _intercept(browser)


def _unblock_socket(browser):
    browser.routes.pop(SOCKET_ROUTE, None)
    _intercept(browser)


def _drop_connections(user_id):
    """Il server chiude i collegamenti dell'utente come farebbe un calo di rete
    (non uno scollegamento deciso: la pagina riprova da sola)."""
    for sid in presence.tabs_of(user_id):
        socketio.server.eio.disconnect(socketio.server.manager.eio_sid_from_sid(sid, "/"))


def _lose_connection(browser, user_id):
    _block_socket(browser)
    _drop_connections(user_id)
    browser.wait_js(f"{BANNER}?.dataset.banner === 'waiting'"
                    f" && {BANNER}.textContent.includes('Connessione persa')", "avviso di connessione persa")


def _open_home(browser, server):
    browser.open(f"{server}/", 390, 844, ONLINE, timeout=60)
    assert browser.js(BANNER) is None


def test_connessione_persa_e_tornata_nella_home(browser, server, users):
    _open_home(browser, server)
    browser.click("[data-tile][data-kind='veloce'][data-mode='1v1']")
    browser.wait_js(f"{PLAY} && !{PLAY}.disabled", "Gioca attivo")

    _lose_connection(browser, users["Mario"])
    assert browser.js(f"{BANNER}.getAttribute('role')") == "status"
    browser.wait_js(f"{PLAY}.disabled", "Gioca spento senza connessione")
    # L'avviso sta sopra la carta-modal aperta (top layer) e dentro lo schermo
    box = browser.js(f"(() => {{ const b = {BANNER}.getBoundingClientRect();"
                     " return {l: b.left, r: b.right, t: b.top, w: innerWidth}; })()")
    assert box["l"] >= 0 and box["r"] <= box["w"] and box["t"] >= 0
    assert browser.js(f"{BANNER}.matches(':popover-open')") is True

    _unblock_socket(browser)
    browser.wait_js(f"{BANNER} === null && !{PLAY}.disabled && {ONLINE}", "ritorno della connessione", timeout=30)


def test_chat_spenta_senza_connessione_e_messaggi_al_ritorno(browser, server, users, app):
    _open_home(browser, server)
    browser.click("[data-friends-button]")
    browser.wait_js(f"document.querySelector(\"[data-chat-open='{users['Giulia']}']\") !== null", "lista degli amici")
    browser.click(f"[data-chat-open='{users['Giulia']}']")
    browser.wait_js(f"{CHAT} !== null && !{SEND}.disabled", "chat aperta")

    _lose_connection(browser, users["Mario"])
    browser.wait_js(f"{SEND}.disabled", "Invia spento senza connessione")
    # Giulia scrive mentre Mario è scollegato: il messaggio non gli arriva adesso
    with app.app_context():
        message = chat_service.send(users["Giulia"], uuid.uuid4().hex, users["Mario"], "Ci sei?")["message"]

    _unblock_socket(browser)
    browser.wait_js(f"{BANNER} === null && !{SEND}.disabled"
                    f" && document.querySelector('[data-message-id=\"{message['id']}\"]') !== null",
                    "ritorno con il messaggio arrivato nel frattempo", timeout=30)


def test_scollegato_dal_server_chiede_di_ricaricare(browser, server, users, app):
    _open_home(browser, server)
    browser.js("window.primaDelRicaricamento = true")
    with app.app_context():
        disconnect_user(users["Mario"])   # come "Esci" da un'altra scheda (P32)
    browser.wait_js(f"{BANNER}?.dataset.banner === 'error'", "avviso di scollegamento")
    assert browser.js(f"{BANNER}.getAttribute('role')") == "alert"
    assert "ricarica la pagina" in browser.js(f"{BANNER}.textContent")
    assert browser.js("document.querySelector('[data-banner-action]').textContent") == "Ricarica"

    browser.click("[data-banner-action]")
    browser.wait_js(f"window.primaDelRicaricamento === undefined && document.readyState === 'complete' && {ONLINE}",
                    "pagina ricaricata e collegata", timeout=60)
    assert browser.js(BANNER) is None


def test_primo_collegamento_lento(browser, server):
    _block_socket(browser)
    browser.open(f"{server}/", 390, 844)
    assert browser.js(BANNER) is None   # subito niente avviso: non lampeggia a ogni apertura
    browser.wait_js(f"{BANNER}?.textContent.includes('Collegamento al server in corso')",
                    "avviso dopo 3 secondi", timeout=10)
    _unblock_socket(browser)
    browser.wait_js(f"{BANNER} === null && {ONLINE}", "collegato", timeout=30)
