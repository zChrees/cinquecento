"""P115: suoni del menu per richiesta di amicizia, messaggio e invito.

Controlla il "Fatto quando" di SCALETTA.md (P115): ognuno dei tre avvisi ha il suo suono,
diverso dagli altri (sounds.js), e parte quando arriva l'avviso: friends:changed con
"request_received" (non con gli altri motivi), chat:message di un amico (non i propri
messaggi mandati da un'altra scheda), invite:received nella home; con l'interruttore
"Suoni" spento (scelta ricordata nel browser) niente. Il contesto audio non si crea mai
durante un ridisegno: nella home si crea all'apertura (come al tavolo, P118). I test
ascoltano l'evento "cinquecento:sound", che parte anche quando il browser non fa sentire.

La home si apre in Chrome o Edge senza finestra (tests/browser.py) con l'utente di prova
collegato al tempo reale; gli avvisi li manda il server vero (socketio.emit sul canale
dell'utente), come farebbero friend_service, chat e inviti. Non serve MySQL. Se né Chrome
né Edge sono installati i controlli nel browser si saltano.
"""

import json
import re
from pathlib import Path

import pytest

from app import create_app
from app.extensions import socketio
from app.realtime.events import user_channel
from app.realtime.invites import invites
from app.realtime.room import Player
from tests.browser import TEST_COOKIE, Browser, FakeUser, find_browser, running_server

ROOT = Path(__file__).resolve().parents[2]
SOUNDS_JS = (ROOT / "app" / "static" / "js" / "core" / "sounds.js").read_text(encoding="utf-8")
ME = 8
FRIEND = Player(45, "Giulia")
RECORD = """
  window.__sounds = [];
  document.addEventListener('cinquecento:sound', (e) => window.__sounds.push(e.detail.name));"""


def _files_of(name):
    return re.search(rf"^\s+{name}: \[([^\]]*)\]", SOUNDS_JS, re.MULTILINE).group(1)


def test_tre_suoni_diversi_tra_loro_e_da_quelli_del_tavolo():
    menu = {name: _files_of(name) for name in ("friend_request", "message", "invite")}
    assert len(set(menu.values())) == 3, menu
    table = [_files_of(name) for name in ("card", "draw", "shuffle", "deal", "trick", "lay_down", "sing",
                                          "phrase", "tick", "last_tick", "win", "lose", "tie")]
    assert not set(menu.values()) & set(table), menu


@pytest.fixture(scope="module")
def server():
    with running_server(create_app("testing"), FakeUser("Mario", ME)) as url:
        yield url


@pytest.fixture(scope="module")
def browser(server, tmp_path_factory):
    b = Browser(find_browser(), tmp_path_factory.mktemp("chrome"))
    b.send("Network.setCookie", name=TEST_COOKIE[0], value=TEST_COOKIE[1], url=server)
    b.send("Page.enable")  # addScriptToEvaluateOnNewDocument funziona solo dopo (P91)
    b.send("Page.addScriptToEvaluateOnNewDocument", source=RECORD)
    yield b
    b.close()


def _home(browser, server, sounds="on"):
    """La home aperta e collegata al tempo reale (home:status vero: 1 online)."""
    browser.open(f"{server}/", 390, 844, "document.querySelector('[data-online-count]') !== null")
    browser.js(f"localStorage.setItem('cinquecento.sounds', {json.dumps(sounds)})")
    browser.open(f"{server}/", 390, 844, "document.querySelector('[data-online-count]')?.textContent === '1'")
    return browser


def _emit(event, data):
    socketio.emit(event, data, to=user_channel(ME))


def _heard(browser):
    return browser.js("window.__sounds")


def _message(from_user_id):
    return {"message": {"id": 1, "from_user_id": from_user_id, "to_user_id": ME if from_user_id != ME else 45,
                        "text": "Ciao!", "sent_at": "2026-10-06T08:00:00.000Z"}}


def test_ogni_avviso_ha_il_suo_suono(browser, server):
    home = _home(browser, server)
    _emit("friends:changed", {"reason": "request_received"})
    home.wait_js("window.__sounds.includes('friend_request')", "suono della richiesta di amicizia")
    _emit("chat:message", _message(45))
    home.wait_js("window.__sounds.includes('message')", "suono del messaggio")
    invite = invites.send(FRIEND, Player(ME, "Mario"), "1v1", 150)
    try:
        _emit("invite:received", invites.data(invite))
        home.wait_js("window.__sounds.includes('invite')", "suono dell'invito")
        home.wait_js("document.querySelector('[data-invite-dialog]')?.open", "finestra dell'invito")
    finally:
        invites.cancel_all_of(ME)
    assert _heard(home) == ["friend_request", "message", "invite"]


def test_niente_suono_per_gli_altri_avvisi_e_i_propri_messaggi(browser, server):
    home = _home(browser, server)
    for reason in ("request_accepted", "request_declined", "friend_removed", "blocked"):
        _emit("friends:changed", {"reason": reason})
    _emit("chat:message", _message(ME))  # mandato da te, da un'altra scheda
    # Un avviso che suona, mandato dopo: quando arriva, gli altri sono già arrivati (stesso canale, in ordine)
    _emit("friends:changed", {"reason": "request_received"})
    home.wait_js("window.__sounds.length > 0", "il suono dell'ultimo avviso")
    assert _heard(home) == ["friend_request"]


def test_con_i_suoni_spenti_niente(browser, server):
    home = _home(browser, server, sounds="off")
    try:
        _emit("friends:changed", {"reason": "request_received"})
        _emit("chat:message", _message(45))
        # La lista degli amici si rilegge dopo friends:changed: a quel punto gli avvisi sono arrivati
        home.wait_js("performance.getEntriesByType('resource').filter((r) => r.name.endsWith('/friends/')).length >= 2",
                     "lista degli amici riletta")
        assert _heard(home) == []
    finally:
        home.js("localStorage.removeItem('cinquecento.sounds')")
