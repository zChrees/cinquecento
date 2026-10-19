"""Passo 5b della migrazione: il pannello amici in React (frontend/src/components/FriendsPanel.tsx).

Gli stessi controlli di test_pannello_amici.py (P46, P47), sulla pagina della SPA
con il login (/prova-react, fino al passo 6):
- il contatore sull'icona e la lista divisa in gruppi, con lo stesso HTML e gli
  stessi data-* del pannello di oggi; ogni pulsante con sola icona ha l'etichetta;
- richiesta di amicizia (campo vuoto, errore del server, riuscita) con X-CSRFToken e
  request_id; accetta, rimuovi con la conferma, "Chatta" che per ora avvisa (5c);
- la lista si rilegge da sola con friends:changed e con un messaggio di un amico;
- si chiude con "indietro", Esc, la X e un tocco fuori; dopo un ricaricamento non si
  riapre da solo e "indietro" lo chiude ancora (P34).

Le richieste /friends/... le intercetta il browser e risponde FakeFriendsServer di
test_pannello_amici.py (dati di app/static/dev/amici_esempio.json), così non serve
MySQL; la sessione (/api/auth/session) e il tempo reale sono quelli veri del server
dei test. Senza Chrome o Edge, o senza il build della SPA, i controlli si saltano.
"""

import json
import re

import pytest

from app import create_app
from app.extensions import socketio
from app.realtime.events import user_channel
from tests.browser import TEST_COOKIE, Browser, FakeUser, find_browser, running_server
from tests.frontend2.test_pannello_amici import ME, FakeFriendsServer
from tests.spa import needs_spa

# PAGE: l'unica pagina della SPA con il login, fino al passo 6
PAGE = "/prova-react"
# CHAT_LATER: l'avviso di "Chatta" finché la chat non è in React (lotto 5c)
CHAT_LATER = "La chat arriva con il prossimo lotto della migrazione (5c)."
PANEL_OPEN = "document.querySelector('[data-friends-panel]')?.open === true"
LIST_READY = "document.querySelector('[data-friends-group=\"online\"]') !== null"
CONNECTED = "document.querySelector('[data-spa-connection=\"connected\"]') !== null"
UUID4 = r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"
# Come test_csp.py: registra ogni risorsa bloccata dalla CSP
RECORD = (
    "window.__csp = [];"
    "document.addEventListener('securitypolicyviolation',"
    " e => window.__csp.push(e.effectiveDirective + ' ' + e.blockedURI));"
)


@pytest.fixture(scope="module")
def app():
    needs_spa()
    return create_app("testing")


@pytest.fixture(scope="module")
def server(app):
    with running_server(app, FakeUser("Mario", ME)) as url:
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


def _open_page(browser, server, width=390, height=844):
    # Collegati al tempo reale prima di tutto (CLAUDE.md, "Test nel browser e tempo reale")
    browser.open(f"{server}{PAGE}", width, height, f"{CONNECTED} && document.querySelector('[data-friends-button]') !== null")


def _open_panel(browser):
    browser.click("[data-friends-button]")
    browser.wait_js(f"{PANEL_OPEN} && {LIST_READY}", "apertura del pannello amici")


def _texts(browser, selector):
    return browser.js(f"[...document.querySelectorAll({json.dumps(selector)})].map((e) => e.textContent.trim())")


def _type(browser, text):
    # Come un utente vero: React non vede un .value cambiato da fuori, vede quello scritto
    browser.js("document.querySelector('#add-friend-input').focus()")
    browser.js("document.querySelector('#add-friend-input').select()")
    browser.send("Input.insertText", text=text)


def _click_dialog_button(browser, label):
    browser.js(f"""[...document.querySelectorAll('dialog.dialog[open] button')]
        .find((b) => b.textContent.trim() === {json.dumps(label)}).click()""")


def _notice(browser):
    return "document.querySelector('[data-friends-notice]').textContent"


def test_contatore_lista_e_azioni(browser, server, friends):
    browser.send("Page.enable")  # senza, lo script qui sotto non parte con le pagine nuove
    browser.send("Page.addScriptToEvaluateOnNewDocument", source=RECORD)
    _open_page(browser, server)
    counters = friends.data["counters"]
    total = counters["requests_in"] + counters["unread_messages"]
    browser.wait_js(f"document.querySelector('[data-friends-badge]:not([hidden])')?.textContent === '{total}'", "contatore")
    assert browser.js("document.querySelector('[data-friends-button]').getAttribute('aria-label')") == \
        f"Amici: {total} novità (richieste e messaggi)"

    # La lista, con gli stessi gruppi e gli stessi data-* del pannello di oggi
    _open_panel(browser)
    assert _texts(browser, "[data-requests-in] .friend__name") == ["Toto"]
    assert _texts(browser, "[data-friends-group='online'] .friend__name") == ["Giulia", "Salvo"]
    assert _texts(browser, "[data-friends-group='in_game'] .friend__name") == ["Rosalia"]
    assert _texts(browser, "[data-friends-group='offline'] .friend__name") == ["Turi", "Nina"]
    assert _texts(browser, "[data-requests-out] .friend__name") == ["Carmelo"]
    assert _texts(browser, "[data-friends-group='online'] .friends-group__title") == ["Online (2)"]
    assert browser.js("document.querySelector('[data-blocked]')") is None
    assert browser.js("document.querySelector('[data-user-id=\"44\"] [data-unread]').dataset.unread") == "2"
    assert browser.js("document.querySelector('[data-friends-panel]').id") == "friends"
    assert "Invita" not in browser.js("document.querySelector('[data-friends-panel]').textContent")
    unlabeled = browser.js("""[...document.querySelectorAll('[data-friends-panel] .icon-btn')]
        .filter((b) => !b.getAttribute('aria-label')).length""")
    assert unlabeled == 0

    # "Chatta": per ora solo l'avviso (la chat arriva con il lotto 5c)
    browser.click("[data-chat-open='44']")
    browser.wait_js(f"{_notice(browser)} === {json.dumps(CHAT_LATER)}", "avviso della chat")

    # Richiesta di amicizia: campo vuoto, errore del server sotto il campo, riuscita
    browser.click("[data-add-friend] button[type=submit]")
    browser.wait_js("document.querySelector('[data-add-friend-error]').textContent === 'Scrivi uno username.'", "campo vuoto")
    _type(browser, "Fantasma")
    browser.click("[data-add-friend] button[type=submit]")
    browser.wait_js("!document.querySelector('[data-add-friend-error]').hidden"
                    " && document.querySelector('[data-add-friend-error]').textContent.includes('Nessun utente')",
                    "errore del server sotto il campo")
    _type(browser, "Nuovo_1")
    browser.click("[data-add-friend] button[type=submit]")
    browser.wait_js(f"{_notice(browser)} === 'Richiesta inviata a Nuovo_1.'", "conferma della richiesta")
    browser.wait_js("[...document.querySelectorAll('[data-requests-out] .friend__name')].some((e) => e.textContent === 'Nuovo_1')",
                    "richiesta mandata nella lista")
    assert browser.js("document.querySelector('#add-friend-input').value") == ""
    posts = [c for c in friends.calls if c["method"] == "POST" and c["path"] == "/requests"]
    assert [c["body"]["username"] for c in posts] == ["Fantasma", "Nuovo_1"]
    assert all(c["csrf"] for c in posts), "manca X-CSRFToken"
    ids = [c["body"]["request_id"] for c in posts]
    assert all(re.fullmatch(UUID4, i) for i in ids)
    assert ids[0] != ids[1]

    # Accetta: l'amico passa tra gli online
    browser.click("[data-accept='52']")
    browser.wait_js(f"{_notice(browser)} === 'Ora tu e Toto siete amici.'", "conferma dell'amicizia")
    browser.wait_js("document.querySelector('[data-requests-in]') === null", "richiesta sparita")
    assert "Toto" in _texts(browser, "[data-friends-group='online'] .friend__name")
    accept = [c for c in friends.calls if c["path"] == "/requests/52/accept"]
    assert accept and accept[0]["csrf"]

    # Altro → Rimuovi amico → conferma rossa → Rimuovi
    browser.click("[data-friend-more='45']")
    browser.wait_js("document.querySelector('dialog.dialog[open]') !== null", "menu Altro")
    _click_dialog_button(browser, "Rimuovi amico")
    browser.wait_js("document.querySelector('dialog.dialog[open] .dialog__title')?.textContent === 'Togliere Salvo dagli amici?'",
                    "conferma della rimozione")
    assert browser.js("[...document.querySelectorAll('dialog.dialog[open] button')]"
                      ".find((b) => b.textContent.trim() === 'Rimuovi').className") == "btn btn--danger"
    _click_dialog_button(browser, "Rimuovi")
    browser.wait_js(f"{_notice(browser)} === 'Salvo non è più tuo amico.'", "rimozione fatta")
    assert {"method": "DELETE", "path": "/45"} in [{"method": c["method"], "path": c["path"]} for c in friends.calls]
    browser.wait_js("![...document.querySelectorAll('.friend__name')].some((e) => e.textContent === 'Salvo')",
                    "lista ricaricata senza Salvo")
    # Il pannello resta aperto sotto la finestra chiusa
    assert browser.js(PANEL_OPEN) is True
    assert browser.js("window.__csp") == []


def test_la_lista_si_aggiorna_da_sola(browser, server, friends, app):
    _open_page(browser, server)
    _open_panel(browser)

    # friends:changed (P47): una richiesta nuova compare senza ricaricare, e il contatore sale
    friends.data["requests_in"].insert(0, {"user_id": 77, "username": "Nuova", "avatar": None,
                                           "sent_at": "2026-10-19T18:00:00.000Z"})
    friends.data["counters"]["requests_in"] += 1
    total = friends.data["counters"]["requests_in"] + friends.data["counters"]["unread_messages"]
    with app.app_context():
        socketio.emit("friends:changed", {"reason": "request_received"}, to=user_channel(ME))
    browser.wait_js("[...document.querySelectorAll('[data-requests-in] .friend__name')].some((e) => e.textContent === 'Nuova')",
                    "richiesta nuova nella lista")
    browser.wait_js(f"document.querySelector('[data-friends-badge]').textContent === '{total}'", "contatore aggiornato")

    # Un messaggio di un amico (chat:message): si rilegge la lista per i non letti
    for friend in friends.data["friends"]:
        if friend["user_id"] == 44:
            friend["unread"] = 3
    reads = len([c for c in friends.calls if c["method"] == "GET"])
    message = {"id": 900, "from_user_id": 44, "to_user_id": ME, "text": "Ciao", "sent_at": "2026-10-19T18:01:00.000Z"}
    with app.app_context():
        socketio.emit("chat:message", {"message": message}, to=user_channel(ME))
    browser.wait_js("document.querySelector('[data-user-id=\"44\"] [data-unread]')?.dataset.unread === '3'",
                    "non letti aggiornati")
    assert len([c for c in friends.calls if c["method"] == "GET"]) > reads


def test_si_chiude_con_indietro_esc_x_e_fuori(browser, server):
    _open_page(browser, server, 1440, 900)

    _open_panel(browser)
    browser.js("history.back()")
    browser.wait_js("document.querySelector('[data-friends-panel]').open === false", "chiusura con indietro")

    _open_panel(browser)
    browser.key("Escape", "Escape", 27)
    browser.wait_js("document.querySelector('[data-friends-panel]').open === false", "chiusura con Esc")

    _open_panel(browser)
    browser.click("[data-friends-panel] .drawer__head .icon-btn")
    browser.wait_js("document.querySelector('[data-friends-panel]').open === false", "chiusura con la X")

    # Tocco fuori: a sinistra del pannello laterale (da computer sta a destra)
    _open_panel(browser)
    for kind in ("mousePressed", "mouseReleased"):
        browser.send("Input.dispatchMouseEvent", type=kind, x=20, y=450, button="left", clickCount=1)
    browser.wait_js("document.querySelector('[data-friends-panel]').open === false", "chiusura con un tocco fuori")

    # Si riapre subito, senza doppioni
    _open_panel(browser)
    assert browser.js("document.querySelectorAll('[data-friends-panel]').length") == 1


def test_dopo_un_ricaricamento_non_si_riapre(browser, server):
    # P34: il browser tiene lo stato del pannello nella cronologia anche dopo un
    # ricaricamento; il pannello non deve riaprirsi da solo e "indietro" deve ancora chiuderlo
    _open_page(browser, server)
    _open_panel(browser)
    # window.__old segna la pagina di prima: si aspetta quella nuova, non quella che sta per sparire
    browser.js("window.__old = true")
    browser.send("Page.reload")
    browser.wait_js(f"window.__old !== true && document.readyState === 'complete' && {CONNECTED}"
                    " && document.querySelector('[data-friends-button]') !== null", "pagina ricaricata")
    assert browser.js(PANEL_OPEN) is False
    _open_panel(browser)
    browser.js("history.back()")
    browser.wait_js("document.querySelector('[data-friends-panel]').open === false", "chiusura con indietro dopo il ricaricamento")
