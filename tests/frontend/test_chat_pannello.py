"""P46 con la chat vera di P48: finestra chat nel pannello amici.

I controlli della finestra chat di P46 ("Fatto quando" di SCALETTA.md) che prima
usavano la chat finta: a 360×640 il campo di scrittura resta visibile, un messaggio
vuoto si rifiuta, il campo accetta al massimo 1000 caratteri, aprire la chat azzera
il contatore dei non letti, "indietro" riporta dalla chat alla lista e poi chiude il
pannello. Nel browser (Chrome o Edge senza finestra, tests/browser.py), con il server
vero e il database dei test, svuotato e ricreato qui con migrate.py come in
test_chat_vera.py: Mario e Giulia sono amici, Giulia ha mandato 3 messaggi non letti.
Se né Chrome né Edge sono installati i controlli nel browser si saltano.
"""

import importlib.util
import uuid
from pathlib import Path

import pytest
import sqlalchemy as sa

from app import create_app
from app.extensions import db
from app.repositories import chat_repo
from app.services import auth_service, friend_service
from tests.browser import TEST_COOKIE, Browser, FakeUser, find_browser, running_server

ROOT = Path(__file__).resolve().parents[2]
PASSWORD = "Password-di-prova-1"
UNREAD = 3
CHAT = "document.querySelector('[data-view=\"chat\"]')"
PANEL_OPEN = "document.querySelector('[data-friends-panel]')?.open === true"
BADGE = "Number(document.querySelector('[data-friends-badge]').hidden ? 0 : document.querySelector('[data-friends-badge]').textContent)"


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
    # Un browser nuovo per ogni test: riaprire la stessa pagina con la chat aperta vale
    # come ricaricarla, e la cronologia terrebbe lo stato della chat del test prima
    b = Browser(find_browser(), tmp_path / "chrome")
    b.send("Network.setCookie", name=TEST_COOKIE[0], value=TEST_COOKIE[1], url=server)
    yield b
    b.close()


def _open_chat(browser, server, friend_id, width, height):
    browser.open(f"{server}/", width, height, "document.querySelector('[data-online-count]')?.textContent === '1'",
                 timeout=60)
    browser.click("[data-friends-button]")
    browser.wait_js(f"document.querySelector(\"[data-chat-open='{friend_id}']\") !== null", "lista degli amici")
    browser.click(f"[data-chat-open='{friend_id}']")
    browser.wait_js(f"{CHAT} !== null", "apertura della chat")


def test_aprire_la_chat_azzera_i_non_letti(browser, server, users):
    # Anche collegati al tempo reale (1 online): senza, chat:history non parte e la chat non si apre
    browser.open(f"{server}/", 390, 844,
                 f"{BADGE} === {UNREAD} && document.querySelector('[data-online-count]')?.textContent === '1'",
                 timeout=60)
    browser.click("[data-friends-button]")
    browser.wait_js(f"document.querySelector(\"[data-chat-open='{users['Giulia']}']\") !== null", "lista degli amici")
    unread = browser.js(f"document.querySelector('[data-user-id=\"{users['Giulia']}\"] [data-unread]').dataset.unread")
    assert unread == str(UNREAD)
    browser.click(f"[data-chat-open='{users['Giulia']}']")
    browser.wait_js(f"{CHAT} !== null", "apertura della chat")
    assert browser.js("document.querySelectorAll('.chat__msg').length") == UNREAD + 1
    assert browser.js("document.querySelectorAll('.chat__msg--mine').length") == 1
    assert browser.js(BADGE) == 0


def test_a_360_il_campo_si_vede_e_i_limiti(browser, server, users):
    _open_chat(browser, server, users["Giulia"], 360, 640)
    field = browser.js("(() => { const r = document.querySelector('#chat-input').getBoundingClientRect();"
                       " return {top: r.top, bottom: r.bottom, vh: innerHeight}; })()")
    assert 0 <= field["top"] and field["bottom"] <= field["vh"]
    assert browser.js("document.querySelector('#chat-input').maxLength") == 1000
    # Messaggio di soli spazi: rifiutato nella pagina, non parte niente
    count = browser.js("document.querySelectorAll('.chat__msg').length")
    browser.js("document.querySelector('#chat-input').value = '   '")
    browser.click("[data-chat-form] button[type=submit]")
    assert browser.js("document.querySelector('[data-chat-error]').textContent") == "Scrivi un messaggio."
    assert browser.js("document.querySelector('[data-chat-error]').hidden") is False
    assert browser.js("document.querySelectorAll('.chat__msg').length") == count


def test_indietro_dalla_chat_alla_lista_poi_chiude(browser, server, users):
    _open_chat(browser, server, users["Giulia"], 1440, 900)
    browser.js("history.back()")
    browser.wait_js(f"{CHAT} === null && {PANEL_OPEN}", "ritorno alla lista")
    browser.js("history.back()")
    browser.wait_js("document.querySelector('[data-friends-panel]').open === false", "chiusura con indietro")
    assert browser.js("history.state?.friendsPanel ?? null") is None
