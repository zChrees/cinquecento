"""P46 con la chat vera di P48: finestra chat nel pannello amici (P128, molti messaggi).

Fino al lotto 9b-1 della migrazione questo file provava la chat del JavaScript vecchio
(sulla home Jinja, /vecchia-home): i suoi controlli (campo visibile a 360 px e limiti,
non letti azzerati, fuoco dopo "Invia", doppio clic, "indietro", pochi messaggi in
fondo, trascinamento) li fa ora tests/frontend/test_spa_chat.py sulla chat React. Qui
resta, sulla home React (/), quello che lì non c'è: con molti messaggi l'elenco scorre
fino al primo (lo spazio vuoto in alto di P128 non li rende irraggiungibili).
Nel browser (Chrome o Edge senza finestra, tests/browser.py), con il server vero e il
database dei test, svuotato e ricreato qui con migrate.py: Mario e Giulia sono amici,
Giulia ha mandato 3 messaggi non letti. _migrate la usano anche test_spa_chat.py,
test_spa_home_coda.py e test_spa_impostazioni.py.
Se né Chrome né Edge sono installati, o manca il build della SPA, i controlli si saltano.
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
from tests.spa import needs_spa

ROOT = Path(__file__).resolve().parents[2]
PASSWORD = "Password-di-prova-1"
UNREAD = 3
CHAT = "document.querySelector('[data-view=\"chat\"]')"
# READY: la home React collegata al tempo reale (senza, chat:history non parte)
READY = ("document.querySelector('[data-online-count]')?.textContent === '1'"
         " && document.querySelector('[data-friends-panel]')?.dataset.connection === 'connected'")


def _migrate(url):
    spec = importlib.util.spec_from_file_location("migrate", ROOT / "scripts" / "migrate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.migrate(url, report=lambda _msg: None)


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
    b = Browser(find_browser(), tmp_path / "chrome")
    b.send("Network.setCookie", name=TEST_COOKIE[0], value=TEST_COOKIE[1], url=server)
    yield b
    b.close()


def _open_chat(browser, server, friend_id, width, height):
    browser.open(f"{server}/", width, height, READY, timeout=60)
    browser.click("[data-friends-button]")
    browser.wait_js(f"document.querySelector(\"[data-chat-open='{friend_id}']\") !== null", "lista degli amici")
    browser.click(f"[data-chat-open='{friend_id}']")
    browser.wait_js(f"{CHAT} !== null && document.querySelectorAll('.chat__msg').length > 0", "apertura della chat")


# P128: dove stanno l'ultimo messaggio, l'elenco e la casella
LAST = """(() => {
  const msgs = [...document.querySelectorAll('.chat__msg')];
  const last = msgs[msgs.length - 1].getBoundingClientRect();
  const list = document.querySelector('[data-chat-messages]').getBoundingClientRect();
  const form = document.querySelector('[data-chat-form]').getBoundingClientRect();
  return { lastTop: last.top, lastBottom: last.bottom, listTop: list.top, listBottom: list.bottom,
           formTop: form.top, firstTop: msgs[0].getBoundingClientRect().top };
})()"""


def test_con_molti_messaggi_si_scorre_fino_al_primo(browser, server, users):
    # Lo spazio vuoto in alto non deve rendere irraggiungibili i messaggi più vecchi
    _open_chat(browser, server, users["Giulia"], 390, 420)
    for n in range(12):
        browser.js(f"""(() => {{ const list = document.querySelector('[data-chat-messages]');
          const li = document.createElement('li'); li.className = 'chat__msg'; li.textContent = 'riga {n}';
          list.append(li); list.scrollTop = list.scrollHeight; }})()""")
    browser.js("document.querySelector('[data-chat-messages]').scrollTop = 0")
    where = browser.js(LAST)
    assert where["firstTop"] >= where["listTop"], where  # il primo si vede tutto
    assert browser.js("document.querySelector('[data-chat-messages]').scrollTop") == 0
