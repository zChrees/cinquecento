"""P48: la chat vera nel pannello amici (FriendsPanel.js, ChatWindow.js).

Nel browser (Chrome o Edge senza finestra, tests/browser.py), con il server vero e il
database dei test (svuotato e ricreato qui con migrate.py, come nella suite sockets):
Mario e Giulia sono amici e hanno 55 messaggi. Controlla: gli ultimi 50 in ordine,
"Messaggi precedenti" carica gli altri 5, un messaggio con tag resta testo, un
messaggio arrivato mentre la chat è aperta compare da solo, e dopo un blocco la chat
dice "Bloccato" e chiude la scrittura (scelta di Giuseppe).
Se né Chrome né Edge sono installati i controlli nel browser si saltano.
"""

import importlib.util
import uuid
from pathlib import Path

import pytest
import sqlalchemy as sa

from app import create_app
from app.extensions import db, socketio
from app.realtime.events import user_channel
from app.repositories import chat_repo
from app.services import auth_service, chat_service, friend_service
from tests.browser import TEST_COOKIE, Browser, FakeUser, find_browser, running_server

ROOT = Path(__file__).resolve().parents[2]
PASSWORD = "Password-di-prova-1"
CHAT = "document.querySelector('[data-view=\"chat\"]')"


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
        for n in range(55):
            sender, recipient = (giulia, mario) if n % 2 == 0 else (mario, giulia)
            chat_repo.add(sender, recipient, f"messaggio {n}", chat_repo.utc_now())
        db.session.commit()
    return {"Mario": mario, "Giulia": giulia}


@pytest.fixture(scope="module")
def server(app, users):
    app.config["CHAT_MIN_INTERVAL_SECONDS"] = 0
    with running_server(app, FakeUser("Mario", users["Mario"])) as url:
        yield url


@pytest.fixture(scope="module")
def browser(server, tmp_path_factory):
    b = Browser(find_browser(), tmp_path_factory.mktemp("chrome"))
    b.send("Network.setCookie", name=TEST_COOKIE[0], value=TEST_COOKIE[1], url=server)
    yield b
    b.close()


def _open_chat(browser, server, friend_id):
    browser.open(f"{server}/", 390, 844, "document.querySelector('[data-online-count]')?.textContent === '1'",
                 timeout=60)
    browser.click("[data-friends-button]")
    browser.wait_js(f"document.querySelector(\"[data-chat-open='{friend_id}']\") !== null", "lista degli amici")
    browser.click(f"[data-chat-open='{friend_id}']")
    browser.wait_js(f"{CHAT} !== null", "apertura della chat")


def test_ultimi_50_poi_messaggi_precedenti(browser, server, users):
    _open_chat(browser, server, users["Giulia"])
    texts = browser.js("[...document.querySelectorAll('.chat__msg')].map((m) => m.firstChild.textContent)")
    assert texts == [f"messaggio {n}" for n in range(5, 55)]
    assert browser.js("document.querySelector('[data-chat-more]').closest('li').hidden") is False
    browser.click("[data-chat-more]")
    browser.wait_js("document.querySelectorAll('.chat__msg').length === 55", "messaggi precedenti")
    first = browser.js("document.querySelector('.chat__msg').firstChild.textContent")
    assert first == "messaggio 0"
    assert browser.js("document.querySelector('[data-chat-more]').closest('li').hidden") is True
    assert browser.js("document.querySelector('[data-chat-notice]')") is None  # si può scrivere


def test_messaggio_con_tag_e_messaggio_arrivato(browser, server, users, app):
    _open_chat(browser, server, users["Giulia"])
    browser.js("document.querySelector('#chat-input').value = '<b>ciao</b>'")
    browser.click("[data-chat-form] button[type=submit]")
    browser.wait_js("[...document.querySelectorAll('.chat__msg--mine')].at(-1).firstChild.textContent === '<b>ciao</b>'",
                    "messaggio mandato")
    assert browser.js("document.querySelector('.chat__msg b')") is None

    # Giulia risponde: il messaggio compare da solo nella chat aperta
    with app.app_context():
        message = chat_service.send(users["Giulia"], uuid.uuid4().hex, users["Mario"], "Amunì!")["message"]
    socketio.emit("chat:message", {"message": message}, to=user_channel(users["Mario"]))
    browser.wait_js(f"document.querySelector('[data-message-id=\"{message['id']}\"]') !== null",
                    "messaggio arrivato")


def test_dopo_il_blocco_la_chat_dice_bloccato(browser, server, users, app):
    _open_chat(browser, server, users["Giulia"])
    with app.app_context():
        friend_service.block(users["Giulia"], uuid.uuid4().hex, users["Mario"])  # Giulia blocca Mario
    try:
        browser.js("document.querySelector('#chat-input').value = 'ci sei?'")
        browser.click("[data-chat-form] button[type=submit]")
        browser.wait_js("document.querySelector('#chat-input').disabled === true", "scrittura chiusa")
        notice = browser.js("document.querySelector('[data-chat-notice]').textContent")
        assert notice == "Bloccato: non potete più scrivervi."
    finally:
        with app.app_context():
            friend_service.unblock(users["Giulia"], users["Mario"])
