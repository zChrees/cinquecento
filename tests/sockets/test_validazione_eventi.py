"""P32: sicurezza degli eventi in tempo reale, con il server vero e client simulati.

- Ogni evento che la pagina può mandare, con dati sbagliati (non un oggetto, tipi
  sbagliati, numeri enormi, testi troppo lunghi), riceve un errore del contratto e mai
  server_error; se i dati non sono un oggetto, invalid_data.
- Una connessione Socket.IO da un altro sito (intestazione Origin diversa) si rifiuta.
- Limite di frequenza per scheda: oltre il limite too_fast con retry_after in secondi
  interi; le altre schede non ne risentono.
- "Esci" scollega tutte le schede dell'utente (ed esce dalla coda); la cancellazione
  dell'account scollega le schede, toglie dalla coda e annulla gli inviti; un evento
  da una scheda di un account che non esiste più riceve not_logged_in.
"""

import re
import threading
import time
import uuid

import pytest
import requests
import socketio as sio_client

from app.extensions import db
from app.realtime.events import ERRORS
from app.realtime.matchmaking import matchmaker
from app.realtime.presence import presence
from app.repositories import user_repo
from app.services import auth_service, friend_service

WAIT = 5
PASSWORD = "Password-di-prova-1"  # la stessa di conftest.py
CSRF_META = re.compile(r'<meta name="csrf-token" content="([^"]+)">')
CSRF_FIELD = re.compile(r'name="csrf_token" (?:type="hidden" )?value="([^"]+)"')

EVENTS = (
    "queue:join", "queue:leave",
    "game:join", "game:play_card", "game:sing", "game:send_phrase", "game:leave",
    "invite:send", "invite:accept", "invite:decline", "invite:cancel", "invite:start",
    "chat:history", "chat:send", "chat:read",
)
NOT_AN_OBJECT = ("testo", 12, [1, 2], True)
BAD_FIELDS = {
    "request_id": 5, "mode": ["1v1"], "target_score": "150", "user_id": 10**30,
    "invite_id": {"x": 1}, "game_id": "x" * 10_000, "version": "1", "card": [1],
    "suit": 7, "code": None, "before_id": "zero", "text": "x" * 100_000,
}
EVERY_FIELD = dict.fromkeys(BAD_FIELDS)


def _wait_until(condition, what, timeout=WAIT):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return
        time.sleep(0.02)
    pytest.fail(f"non è successo: {what}")


# --- Dati sbagliati: mai server_error ---------------------------------------------------


@pytest.mark.parametrize("event", EVENTS)
def test_dati_sbagliati_mai_errore_del_server(server, connect, event):
    client = connect("Primo")
    payloads = [*NOT_AN_OBJECT, {}, BAD_FIELDS, EVERY_FIELD,
                *({name: value} for name, value in BAD_FIELDS.items())]
    for payload in payloads:
        answer = client.call(event, payload, timeout=WAIT)
        assert isinstance(answer, dict) and "ok" in answer, (event, payload, answer)
        if answer["ok"]:
            continue  # per esempio queue:leave, che risponde ok anche se non era in coda
        code = answer["error"]["code"]
        assert code in ERRORS and code != "server_error", (event, payload, answer)
        if payload in NOT_AN_OBJECT:
            assert code == "invalid_data", (event, payload, answer)
    assert matchmaker.queue.status(server["user_ids"]["Primo"]) is None  # nessuno dei dati sopra mette in coda
    assert client.connected


# --- Connessione da un altro sito ------------------------------------------------------


def test_connessione_da_un_altro_sito_rifiutata(server):
    # Con il trasporto "polling": con il websocket il client aggiunge già la sua intestazione
    # Origin, e una seconda copia farebbe rifiutare la connessione per un altro motivo
    cookie = _session(server["url"], "Primo")[1]
    client = sio_client.Client(reconnection=False)
    with pytest.raises(sio_client.exceptions.ConnectionError):
        client.connect(server["url"], headers={"Cookie": cookie, "Origin": "http://sito-cattivo.example"},
                       transports=["polling"], wait_timeout=WAIT)
    assert not client.connected
    # Dallo stesso sito sì
    same = sio_client.Client(reconnection=False)
    same.connect(server["url"], headers={"Cookie": cookie, "Origin": server["url"]},
                 transports=["polling"], wait_timeout=WAIT)
    assert same.connected
    same.disconnect()


# --- Limite di frequenza ---------------------------------------------------------------


def test_limite_di_frequenza_per_scheda(server, connect, monkeypatch):
    monkeypatch.setitem(server["app"].config, "EVENT_BURST", 5)
    monkeypatch.setitem(server["app"].config, "EVENT_RATE_PER_SECOND", 1)
    fast, other = connect("Primo"), connect("Secondo")
    answers = [fast.call("queue:leave", {}, timeout=WAIT) for _ in range(8)]
    assert answers[:5] == [{"ok": True}] * 5
    rejected = [a for a in answers[5:] if not a["ok"]]
    assert rejected, answers
    for answer in rejected:
        assert answer["error"]["code"] == "too_fast"
        assert isinstance(answer["error"]["retry_after"], int) and answer["error"]["retry_after"] >= 1
    # Un'altra scheda non ne risente
    assert other.call("queue:leave", {}, timeout=WAIT) == {"ok": True}
    # Aspettando quanto dice il server, si riparte
    time.sleep(rejected[-1]["error"]["retry_after"])
    assert fast.call("queue:leave", {}, timeout=WAIT) == {"ok": True}


# --- "Esci" e cancellazione dell'account -----------------------------------------------


def _session(url, username):
    """Login dal modulo, come il browser: la sessione HTTP e il suo cookie."""
    session = requests.Session()
    page = session.get(f"{url}/auth/login", timeout=WAIT).text
    response = session.post(f"{url}/auth/login", data={
        "csrf_token": CSRF_FIELD.search(page)[1], "username": username, "password": PASSWORD,
    }, allow_redirects=False, timeout=WAIT)
    assert response.status_code == 302, "login di prova non riuscito"
    return session, "; ".join(f"{k}={v}" for k, v in session.cookies.items())


class Tab:
    """Una scheda collegata con quel cookie, che si accorge quando il server la scollega."""

    def __init__(self, url, cookie):
        self.client = sio_client.Client(reconnection=False)
        self.gone = threading.Event()
        self.events = []
        self.client.on("disconnect", lambda *_: self.gone.set())
        self.client.on("*", lambda event, data=None: self.events.append((event, data)))
        self.client.connect(url, headers={"Cookie": cookie}, transports=["websocket"], wait_timeout=WAIT)

    def call(self, event, data):
        return self.client.call(event, data, timeout=WAIT)

    def close(self):
        if self.client.connected:
            self.client.disconnect()


@pytest.fixture
def new_user(server):
    """new_user("Nome") → id di un utente nuovo (password di conftest.py); alla fine, se c'è ancora, si cancella."""
    app, made = server["app"], []

    def _new(name):
        with app.app_context():
            user_id = auth_service.register(name, f"{name.lower()}@esempio.it", PASSWORD).id
        made.append(user_id)
        return user_id

    yield _new
    with app.app_context():
        for user_id in made:
            user = user_repo.get_by_id(user_id)
            if user is not None:
                user_repo.delete(user)
        db.session.commit()


def test_esci_scollega_tutte_le_schede_ed_esce_dalla_coda(server, new_user):
    user_id = new_user("Uscente")
    session, cookie = _session(server["url"], "Uscente")
    tabs = [Tab(server["url"], cookie), Tab(server["url"], cookie)]
    try:
        joined = tabs[0].call("queue:join", {"request_id": uuid.uuid4().hex, "mode": "1v1", "target_score": 500})
        assert joined["ok"] is True
        token = CSRF_META.search(session.get(f"{server['url']}/", timeout=WAIT).text)[1]
        response = session.post(f"{server['url']}/auth/logout", data={"csrf_token": token},
                                allow_redirects=False, timeout=WAIT)
        assert response.status_code == 302
        for tab in tabs:
            assert tab.gone.wait(WAIT), "la scheda è rimasta collegata dopo Esci"
        _wait_until(lambda: not presence.is_online(user_id), "utente non più online")
        assert matchmaker.queue.status(user_id) is None
    finally:
        for tab in tabs:
            tab.close()


def _delete_account(session, url):
    page = session.get(f"{url}/profile/settings", timeout=WAIT).text
    tokens = CSRF_FIELD.findall(page)
    return session.post(f"{url}/profile/delete", data={"csrf_token": tokens[-1], "password": PASSWORD},
                        allow_redirects=False, timeout=WAIT)


def test_cancellazione_toglie_dalla_coda_e_scollega(server, new_user):
    user_id = new_user("Cancellato1")
    session, cookie = _session(server["url"], "Cancellato1")
    tab = Tab(server["url"], cookie)
    try:
        assert tab.call("queue:join", {"request_id": uuid.uuid4().hex, "mode": "2v2", "target_score": 500})["ok"]
        assert matchmaker.queue.status(user_id) is not None
        assert _delete_account(session, server["url"]).status_code == 302
        assert tab.gone.wait(WAIT)
        assert matchmaker.queue.status(user_id) is None
        with server["app"].app_context():
            assert user_repo.get_by_id(user_id) is None
    finally:
        tab.close()


def test_cancellazione_annulla_gli_inviti(server, connect, new_user):
    user_id = new_user("Cancellato2")
    primo_id = server["user_ids"]["Primo"]
    with server["app"].app_context():
        friend_service.send_request(user_id, uuid.uuid4().hex, "Primo")
        friend_service.accept_request(primo_id, user_id)
    session, cookie = _session(server["url"], "Cancellato2")
    tab = Tab(server["url"], cookie)
    primo = connect("Primo")
    updates = []
    primo.on("invite:update", updates.append)
    try:
        sent = tab.call("invite:send", {"request_id": uuid.uuid4().hex, "user_id": primo_id,
                                        "mode": "1v1", "target_score": 150})
        assert sent["ok"] is True, sent
        invite_id = sent["data"]["invite_id"]
        assert _delete_account(session, server["url"]).status_code == 302
        assert tab.gone.wait(WAIT)
        _wait_until(lambda: {"invite_id": invite_id, "status": "cancelled"} in updates, "invito annullato")
    finally:
        tab.close()


def test_evento_da_un_account_che_non_esiste_piu(server, new_user):
    user_id = new_user("Sparito")
    cookie = _session(server["url"], "Sparito")[1]
    tab = Tab(server["url"], cookie)
    try:
        # L'account sparisce senza passare dalla cancellazione (per esempio da un'altra
        # installazione del sito sullo stesso database): la scheda è ancora collegata
        with server["app"].app_context():
            user_repo.delete(user_repo.get_by_id(user_id))
            db.session.commit()
        answer = tab.call("queue:join", {"request_id": uuid.uuid4().hex, "mode": "1v1", "target_score": 150})
        assert answer["ok"] is False and answer["error"]["code"] == "not_logged_in", answer
    finally:
        tab.close()
