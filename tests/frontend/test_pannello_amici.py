"""P46: pannello amici e finestra chat.

Controlla il "Fatto quando" di SCALETTA.md (P46): il pannello si apre da
qualsiasi pagina con la navbar (non dal tavolo) e si chiude con "indietro" e con
Esc; a 360 px la chat è leggibile e il campo di scrittura resta visibile; i
componenti non inseriscono testo come HTML. Nel browser (Chrome o Edge senza
finestra, tests/browser.py) le richieste HTTP del contratto 2.2 le intercetta il
test e risponde con i dati di app/static/dev/amici_esempio.json, così non serve
MySQL; il test controlla anche il codice CSRF e request_id delle richieste.
Se né Chrome né Edge sono installati i controlli nel browser si saltano.
"""

import copy
import json
import re
from pathlib import Path

import pytest
from flask import render_template

from app import create_app
from config import load_config
from tests.browser import TEST_COOKIE, Browser, FakeUser, find_browser, running_server

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "app" / "static"
EXAMPLE = json.loads((STATIC / "dev" / "amici_esempio.json").read_text(encoding="utf-8"))
ME = 12   # nei dati finti l'utente collegato è Mario, 12


def _render_logged_in(app, path="/"):
    with app.test_request_context(path):
        return render_template("main/index.html", current_user=FakeUser("Mario", ME), demo_urls=None, demo_state=None)


def _friends_button(html):
    return re.search(r"<button[^>]*data-friends-button[^>]*>", html, flags=re.DOTALL).group(0)


# --- Pagina e file ---------------------------------------------------------------


def test_pulsante_amici_collegato_al_pannello():
    app = create_app("testing")
    button = _friends_button(_render_logged_in(app))
    assert 'aria-controls="friends"' in button and 'aria-haspopup="dialog"' in button
    assert 'data-friends-url="/friends/"' in button
    # Chat di prova solo in sviluppo e nei test
    assert 'data-chat-demo-url="/static/dev/amici_esempio.json"' in button
    app.config["ENV_NAME"] = "demo"
    assert "data-chat-demo-url" not in _friends_button(_render_logged_in(app))


def test_css_del_pannello_in_base_html():
    app = create_app("testing")
    html = _render_logged_in(app)
    client = app.test_client()
    for name in ("friends-panel", "chat"):
        path = f"/static/css/components/{name}.css"
        assert f'href="{path}"' in html, name
        response = client.get(path)
        assert response.status_code == 200, name
        response.close()


def test_limite_della_chat_uguale_al_server():
    code = (STATIC / "js" / "components" / "ChatWindow.js").read_text(encoding="utf-8")
    assert re.search(r"export const MAX_LENGTH = (\d+);", code).group(1) == str(load_config("testing").CHAT_MAX_LENGTH)


def test_componenti_solo_testo_e_niente_inviti():
    for name in ("FriendsPanel", "ChatWindow"):
        code = (STATIC / "js" / "components" / f"{name}.js").read_text(encoding="utf-8")
        for forbidden in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write"):
            assert forbidden not in code, (name, forbidden)
    panel = (STATIC / "js" / "components" / "FriendsPanel.js").read_text(encoding="utf-8")
    # Gli inviti a partita stanno solo nella carta-modal della home (decisione di P46)
    assert "Invita" not in panel and "invite:" not in panel
    layout = (STATIC / "js" / "core" / "layout.js").read_text(encoding="utf-8")
    assert "initFriendsPanel(document.querySelector('[data-friends-button]'))" in layout


# --- Nel browser -------------------------------------------------------------------


class FakeFriendsServer:
    """Risponde alle richieste /friends/... come P45, partendo da amici_esempio.json."""

    def __init__(self):
        self.data = copy.deepcopy(EXAMPLE["GET /friends/"])
        self.calls = []

    def __call__(self, request):
        method, url = request["method"], request["url"]
        path = url.split("/friends", 1)[1]
        body = json.loads(request.get("postData") or "null")
        self.calls.append({"method": method, "path": path, "body": body,
                           "csrf": request["headers"].get("X-CSRFToken", "")})
        if method == "GET" and path == "/":
            return 200, {"ok": True, "data": self.data}
        if method == "POST" and path == "/requests":
            if body["username"] == "Fantasma":
                return 404, {"ok": False, "error": {"code": "not_found", "message": "Nessun utente con questo username."}}
            sent = {"user_id": 99, "username": body["username"], "avatar": None, "sent_at": "2026-09-28T18:00:00.000Z"}
            self.data["requests_out"].insert(0, sent)
            return 200, {"ok": True, "data": sent}
        match = re.fullmatch(r"/requests/(\d+)/accept", path)
        if method == "POST" and match:
            user_id = int(match.group(1))
            request_in = next(r for r in self.data["requests_in"] if r["user_id"] == user_id)
            self.data["requests_in"].remove(request_in)
            self.data["counters"]["requests_in"] -= 1
            self.data["friends"].insert(0, {**request_in, "presence": "online", "unread": 0})
            return 200, {"ok": True, "data": None}
        match = re.fullmatch(r"/(\d+)", path)
        if method == "DELETE" and match:
            self.data["friends"] = [f for f in self.data["friends"] if f["user_id"] != int(match.group(1))]
            return 200, {"ok": True, "data": None}
        return 404, {"ok": False, "error": {"code": "not_found", "message": "Non trovato."}}


@pytest.fixture(scope="module")
def server():
    with running_server(create_app("testing"), FakeUser("Mario", ME)) as url:
        yield url


@pytest.fixture
def friends():
    return FakeFriendsServer()


@pytest.fixture
def browser(server, friends, tmp_path):
    b = Browser(find_browser(), tmp_path / "chrome", routes={"*/friends/*": friends})
    b.send("Network.setCookie", name=TEST_COOKIE[0], value=TEST_COOKIE[1], url=server)
    yield b
    b.close()


PANEL_OPEN = "document.querySelector('[data-friends-panel]')?.open === true"
LIST_READY = "document.querySelector('[data-friends-group=\"online\"]') !== null"


def _open_panel(browser):
    browser.click("[data-friends-button]")
    browser.wait_js(f"{PANEL_OPEN} && {LIST_READY}", "apertura del pannello amici")


def _texts(browser, selector):
    return browser.js(f"[...document.querySelectorAll({json.dumps(selector)})].map((e) => e.textContent.trim())")


def _click_dialog_button(browser, label):
    browser.js(f"""[...document.querySelectorAll('dialog.dialog[open] button')]
        .find((b) => b.textContent.trim() === {json.dumps(label)}).click()""")


def test_contatore_e_lista_dal_server(browser, server, friends):
    browser.open(f"{server}/", 390, 844, "document.querySelector('[data-friends-badge]:not([hidden])') !== null")
    counters = friends.data["counters"]
    assert browser.js("document.querySelector('[data-friends-badge]').textContent") == str(counters["requests_in"] + counters["unread_messages"])
    _open_panel(browser)
    assert _texts(browser, "[data-requests-in] .friend__name") == ["Toto"]
    assert _texts(browser, "[data-friends-group='online'] .friend__name") == ["Giulia", "Salvo"]
    assert _texts(browser, "[data-friends-group='in_game'] .friend__name") == ["Rosalia"]
    assert _texts(browser, "[data-friends-group='offline'] .friend__name") == ["Turi", "Nina"]
    assert _texts(browser, "[data-requests-out] .friend__name") == ["Carmelo"]
    assert browser.js("document.querySelector('[data-blocked]')") is None
    assert browser.js("document.querySelector('[data-user-id=\"44\"] [data-unread]').dataset.unread") == "2"
    # Niente inviti a partita nel pannello
    assert "Invita" not in browser.js("document.querySelector('[data-friends-panel]').textContent")
    # Ogni pulsante con sola icona ha un'etichetta
    unlabeled = browser.js("""[...document.querySelectorAll('[data-friends-panel] .icon-btn')]
        .filter((b) => !b.getAttribute('aria-label')).length""")
    assert unlabeled == 0


def test_richiesta_di_amicizia_con_csrf_e_request_id(browser, server, friends):
    browser.open(f"{server}/", 390, 844)
    _open_panel(browser)
    browser.click("[data-add-friend] button[type=submit]")
    assert browser.js("document.querySelector('[data-add-friend-error]').textContent") == "Scrivi uno username."

    browser.js("document.querySelector('#add-friend-input').value = 'Fantasma'")
    browser.click("[data-add-friend] button[type=submit]")
    browser.wait_js("!document.querySelector('[data-add-friend-error]').hidden"
                    " && document.querySelector('[data-add-friend-error]').textContent.includes('Nessun utente')",
                    "errore del server sotto il campo")

    browser.js("document.querySelector('#add-friend-input').value = 'Nuovo_1'")
    browser.click("[data-add-friend] button[type=submit]")
    browser.wait_js("document.querySelector('[data-friends-notice]').textContent === 'Richiesta inviata a Nuovo_1.'",
                    "conferma della richiesta")
    browser.wait_js("[...document.querySelectorAll('[data-requests-out] .friend__name')].some((e) => e.textContent === 'Nuovo_1')",
                    "richiesta mandata nella lista")
    posts = [c for c in friends.calls if c["method"] == "POST"]
    assert [c["body"]["username"] for c in posts] == ["Fantasma", "Nuovo_1"]
    assert all(c["csrf"] for c in posts), "manca X-CSRFToken"
    ids = [c["body"]["request_id"] for c in posts]
    assert all(re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", i) for i in ids)
    assert ids[0] != ids[1]


def test_accetta_e_rimuovi_con_conferma(browser, server, friends):
    browser.open(f"{server}/", 390, 844)
    _open_panel(browser)
    browser.click("[data-accept='52']")
    browser.wait_js("document.querySelector('[data-friends-notice]').textContent === 'Ora tu e Toto siete amici.'",
                    "conferma dell'amicizia")
    browser.wait_js("document.querySelector('[data-requests-in]') === null", "richiesta sparita")
    assert "Toto" in _texts(browser, "[data-friends-group='online'] .friend__name")

    browser.click("[data-friend-more='45']")
    browser.wait_js("document.querySelector('dialog.dialog[open]') !== null", "menu Altro")
    _click_dialog_button(browser, "Rimuovi amico")
    browser.wait_js("document.querySelector('dialog.dialog[open] .dialog__title')?.textContent === 'Togliere Salvo dagli amici?'",
                    "conferma della rimozione")
    _click_dialog_button(browser, "Rimuovi")
    browser.wait_js("document.querySelector('[data-friends-notice]').textContent === 'Salvo non è più tuo amico.'",
                    "rimozione fatta")
    assert {"method": "DELETE", "path": "/45"} in [{"method": c["method"], "path": c["path"]} for c in friends.calls]
    browser.wait_js("![...document.querySelectorAll('.friend__name')].some((e) => e.textContent === 'Salvo')",
                    "lista ricaricata senza Salvo")


def test_chat_di_prova_testo_come_testo(browser, server):
    browser.open(f"{server}/", 360, 640)
    before = int(browser.js("document.querySelector('[data-friends-badge]').textContent") or 0)
    _open_panel(browser)
    browser.click("[data-chat-open='44']")
    browser.wait_js("document.querySelector('[data-view=\"chat\"]') !== null", "apertura della chat")
    history = EXAMPLE["chat:history (risposta)"]["messages"]
    assert browser.js("document.querySelectorAll('.chat__msg').length") == len(history)
    assert browser.js("document.querySelectorAll('.chat__msg--mine').length") == sum(m["from_user_id"] == ME for m in history)
    assert "Chat di prova" in browser.js("document.querySelector('[data-chat-notice]').textContent")
    # Aprire la chat segna come letti i 2 messaggi di Giulia
    assert int(browser.js("document.querySelector('[data-friends-badge]').textContent") or 0) == before - 2

    # A 360×640 il campo di scrittura è visibile
    field = browser.js("(() => { const r = document.querySelector('#chat-input').getBoundingClientRect();"
                       " return {top: r.top, bottom: r.bottom, vh: innerHeight}; })()")
    assert 0 <= field["top"] and field["bottom"] <= field["vh"]

    # Messaggio vuoto rifiutato; un testo con tag resta testo
    browser.js("document.querySelector('#chat-input').value = '   '")
    browser.click("[data-chat-form] button[type=submit]")
    assert browser.js("document.querySelector('[data-chat-error]').textContent") == "Scrivi un messaggio."
    browser.js("document.querySelector('#chat-input').value = '<b>ciao</b> <img src=x onerror=alert(1)>'")
    browser.click("[data-chat-form] button[type=submit]")
    browser.wait_js(f"document.querySelectorAll('.chat__msg').length === {len(history) + 1}", "messaggio mandato")
    last = browser.js("""(() => { const m = [...document.querySelectorAll('.chat__msg')].at(-1);
        return {text: m.firstChild.textContent, tags: m.querySelectorAll('b, img').length, mine: m.classList.contains('chat__msg--mine')}; })()""")
    assert last == {"text": "<b>ciao</b> <img src=x onerror=alert(1)>", "tags": 0, "mine": True}
    assert browser.js("document.querySelector('#chat-input').maxLength") == 1000


def test_indietro_ed_esc_chiudono(browser, server):
    browser.open(f"{server}/", 1440, 900)
    _open_panel(browser)
    browser.click("[data-chat-open='44']")
    browser.wait_js("document.querySelector('[data-view=\"chat\"]') !== null", "apertura della chat")
    # "indietro": dalla chat alla lista, poi chiude il pannello
    browser.js("history.back()")
    browser.wait_js(f"document.querySelector('[data-view=\"chat\"]') === null && {PANEL_OPEN}", "ritorno alla lista")
    browser.js("history.back()")
    browser.wait_js("document.querySelector('[data-friends-panel]').open === false", "chiusura con indietro")
    # Esc
    _open_panel(browser)
    browser.key("Escape", "Escape", 27)
    browser.wait_js("document.querySelector('[data-friends-panel]').open === false", "chiusura con Esc")
    assert browser.js("history.state?.friendsPanel ?? null") is None
    # Si riapre subito, senza doppioni
    _open_panel(browser)
    assert browser.js("document.querySelectorAll('[data-friends-panel]').length") == 1


def test_niente_pannello_al_tavolo_ne_senza_login(browser, server):
    browser.open(f"{server}/game/prova?demo=1v1", 390, 844, "document.querySelector('[data-mode]') !== null")
    assert browser.js("document.querySelector('[data-friends-panel]')") is None
    browser.send("Network.deleteCookies", name=TEST_COOKIE[0], url=server)
    browser.open(f"{server}/", 390, 844)
    assert browser.js("document.querySelector('[data-friends-panel]')") is None
    browser.click("[data-login-prompt][aria-label^='Amici']")
    browser.wait_js("document.querySelector('dialog.dialog[open]') !== null", "finestra di accesso")
