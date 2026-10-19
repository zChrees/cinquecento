"""Passo 6 della migrazione: la pagina delle impostazioni in React (frontend/src/pages/SettingsPage.tsx).

Nel browser (Chrome o Edge senza finestra), con il server vero e il database dei test,
svuotato e ricreato qui con migrate.py (come test_chat_pannello.py): ogni prova
registra il suo utente e fa il login vero (POST /api/auth/login dalla pagina).
Controlla:
- la griglia: "Iniziale" con la lettera del nome, poi un'immagine e un nome per ogni
  avatar di avatars.py; quello attuale è scelto;
- "Salva l'avatar" salva, ricarica la pagina con "Avatar salvato." e la navbar ha
  l'avatar nuovo;
- "Cancella l'account": con la password sbagliata l'errore compare in basso e
  l'account resta; "Annulla" non manda niente; con la password giusta (Invio nella
  casella) si va alla home con "Account cancellato..." e l'utente non c'è più;
- senza rete nessun modulo parte: compare "Nessuna connessione".
Senza browser, o senza il build della SPA, i controlli si saltano.
"""

import json

import pytest
import sqlalchemy as sa

from app import create_app
from app.extensions import db
from app.services import auth_service
from app.services.auth_service import DELETE_WRONG_PASSWORD
from app.services.avatars import AVATARS
from tests.browser import Browser, find_browser, running_server
from tests.frontend.test_chat_pannello import _migrate
from tests.spa import needs_spa

PASSWORD = "Password-di-prova-6"
PAGE = "/profile/settings"
# READY: impostazioni collegate al tempo reale e con l'elenco degli avatar arrivato
READY = ("document.querySelector('[data-friends-panel]')?.dataset.connection === 'connected'"
         " && document.querySelector('[data-avatar=\"coppe\"] img') !== null")
FLASHES = "[...document.querySelectorAll('[data-flash] .flash')].map((f) => [f.dataset.flashKind, f.textContent.trim()])"


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
def server(app):
    # Nessun utente finto: il login lo fa ogni prova, con un account vero
    with running_server(app) as url:
        yield url


@pytest.fixture
def browser(server, tmp_path):
    b = Browser(find_browser(), tmp_path / "chrome")
    yield b
    b.close()


def _user(app, username):
    with app.app_context():
        user = auth_service.register(username, f"{username.lower()}@esempio.it", PASSWORD)
        return user.id


def _avatar_in_db(app, user_id):
    with app.app_context():
        db.session.rollback()  # una lettura nuova (P45)
        return db.session.execute(sa.text("SELECT avatar FROM utenti WHERE id = :i"), {"i": user_id}).scalar()


def _exists(app, user_id):
    with app.app_context():
        db.session.rollback()
        return db.session.execute(sa.text("SELECT COUNT(*) FROM utenti WHERE id = :i"), {"i": user_id}).scalar() == 1


def _login_and_open(browser, server, username):
    # Il login vero, dalla pagina di accesso (stessa origine: il cookie della sessione resta)
    browser.open(f"{server}/auth/login", 390, 844, "document.querySelector('h1') !== null")
    status = browser.js(f"""fetch('/api/auth/session').then((r) => r.json()).then((s) => fetch('/api/auth/login', {{
        method: 'POST', headers: {{ 'Content-Type': 'application/json', 'X-CSRFToken': s.data.csrf_token }},
        body: JSON.stringify({{ username: {json.dumps(username)}, password: {json.dumps(PASSWORD)}, next: '' }}),
      }})).then((r) => r.status)""")
    assert status == 200
    browser.open(f"{server}{PAGE}", 390, 844, READY, timeout=60)


def _type(browser, selector, text):
    browser.js(f"document.querySelector({json.dumps(selector)}).focus()")
    browser.send("Input.insertText", text=text)


def test_griglia_e_avatar_salvato(browser, server, app):
    user_id = _user(app, "Mario")
    _login_and_open(browser, server, "Mario")
    assert browser.js("document.querySelector('h1').textContent") == "Impostazioni"
    assert browser.js("document.title") == "Impostazioni · Cinquecento"
    # "Iniziale" per prima, scelta (l'utente non ha un avatar), con la lettera del nome
    initial = browser.js("""(() => { const l = document.querySelector('label.avatar-choice[data-avatar=""]');
      return { face: l.querySelector('.avatar-choice__face').textContent, name: l.textContent.trim(),
               checked: l.querySelector('input').checked }; })()""")
    assert initial == {"face": "M", "name": "MIniziale", "checked": True}
    # Poi un'immagine e un nome per ogni avatar, nell'ordine di avatars.py
    choices = browser.js("""[...document.querySelectorAll('label.avatar-choice')].slice(1).map((l) => [
      l.dataset.avatar, l.querySelector('img').getAttribute('src'), l.querySelector('.avatar-choice__name').textContent])""")
    assert choices == [[code, f"/static/img/avatars/{code}.svg", name] for code, name in AVATARS.items()]

    browser.click("label.avatar-choice[data-avatar='re_denari'] input")
    browser.js("window.__old = true")
    browser.click("[data-avatar-submit]")
    browser.wait_js(f"window.__old !== true && {READY}", "pagina ricaricata dopo il salvataggio", 30)
    assert browser.js(FLASHES) == [["success", "check_circleAvatar salvato."]]
    assert browser.js("document.querySelector('label.avatar-choice[data-avatar=\"re_denari\"] input').checked") is True
    assert browser.js("document.querySelector('[data-open-stats] .avatar').dataset.avatar") == "re_denari"
    assert _avatar_in_db(app, user_id) == "re_denari"


def test_cancellazione_con_la_password(browser, server, app):
    user_id = _user(app, "Nina")
    _login_and_open(browser, server, "Nina")

    # Annulla: niente parte
    browser.click("[data-delete-open]")
    browser.wait_js("document.activeElement?.id === 'delete-password'", "finestra con il fuoco sulla password")
    browser.js("""[...document.querySelectorAll('dialog.dialog[open] button')]
        .find((b) => b.textContent.trim() === 'Annulla').click()""")
    browser.wait_js("document.querySelector('dialog.dialog[open]') === null", "finestra chiusa")
    assert _exists(app, user_id)

    # Password sbagliata: l'errore in basso, l'account resta, il pulsante si riaccende
    browser.click("[data-delete-open]")
    browser.wait_js("document.activeElement?.id === 'delete-password'", "finestra aperta")
    _type(browser, "#delete-password", "Password-sbagliata")
    browser.js("""[...document.querySelectorAll('dialog.dialog[open] button')]
        .find((b) => b.textContent.trim() === "Cancella l'account").click()""")
    browser.wait_js(f"JSON.stringify({FLASHES}).includes({json.dumps(DELETE_WRONG_PASSWORD)})", "errore della password")
    browser.wait_js("document.querySelector('[data-delete-open]').disabled === false", "pulsante riacceso")
    assert _exists(app, user_id)

    # Password giusta, con Invio nella casella: si va alla home e l'account non c'è più
    browser.click("[data-delete-open]")
    browser.wait_js("document.activeElement?.id === 'delete-password'", "finestra aperta")
    _type(browser, "#delete-password", PASSWORD)
    browser.send("Input.dispatchKeyEvent", type="keyDown", key="Enter", code="Enter", windowsVirtualKeyCode=13, text="\r")
    browser.send("Input.dispatchKeyEvent", type="keyUp", key="Enter", code="Enter", windowsVirtualKeyCode=13)
    browser.wait_js("location.pathname === '/' && document.readyState === 'complete'", "home dopo la cancellazione", 30)
    assert "Account cancellato" in browser.js("document.querySelector('[data-flash]')?.textContent ?? ''")
    assert not _exists(app, user_id)


def test_senza_rete_nessuna_richiesta(browser, server, app):
    user_id = _user(app, "Turi")
    _login_and_open(browser, server, "Turi")
    browser.send("Network.enable")
    browser.send("Network.emulateNetworkConditions", offline=True, latency=0, downloadThroughput=-1, uploadThroughput=-1)
    browser.wait_js("navigator.onLine === false", "browser senza rete")
    browser.click("label.avatar-choice[data-avatar='coppe'] input")
    browser.click("[data-avatar-submit]")
    browser.wait_js("document.querySelector('dialog.dialog[open] .dialog__title')?.textContent === 'Nessuna connessione'",
                    "finestra Nessuna connessione")
    assert browser.js("document.querySelector('[data-avatar-submit]').disabled") is False
    browser.send("Network.emulateNetworkConditions", offline=False, latency=0, downloadThroughput=-1, uploadThroughput=-1)
    assert _avatar_in_db(app, user_id) is None
