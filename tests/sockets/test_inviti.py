"""Amici online e inviti a partita (P47; contratto 5.2 e 5.3; D27, D36).

Con il server vero e client simulati:
- un amico che si collega o esce appare online / offline agli altri (friends:presence),
  anche "in_game" quando comincia una partita;
- friends:changed dopo richieste e blocchi (chi è bloccato riceve solo "friend_removed");
- un invito 1v1 accettato porta i due nella stessa stanza, senza rating; un invito 2v2
  accettato mette la coppia in coda;
- rifiutato, scaduto e annullato avvisano chi ha invitato (invite:update);
- non si invita chi non è amico, chi è offline o chi è già in partita; un invito alla
  volta; doppio clic con lo stesso request_id; chi chiude l'ultima scheda annulla.
"""

import threading
import time
import uuid

import pytest

from app.realtime import invites as invites_module
from app.realtime.events import ok
from app.realtime.invites import invites
from app.realtime.matchmaking import matchmaker
from app.realtime.presence import presence
from app.realtime.room import Player
from app.realtime.room_manager import create_room, find_room_of_user, rooms
from app.services import friend_service

WAIT = 5


class Events:
    """Raccoglie tutti gli eventi di un nome; `wait_for(test)` aspetta quello che serve."""

    def __init__(self, client, event):
        self.items = []
        self._cond = threading.Condition()

        def receive(data):
            with self._cond:
                self.items.append(data)
                self._cond.notify_all()

        client.on(event, receive)

    def wait_for(self, test=lambda _: True, timeout=WAIT):
        with self._cond:
            found = self._cond.wait_for(lambda: any(test(item) for item in self.items), timeout)
        assert found, f"evento atteso non arrivato; ricevuti: {self.items}"
        return next(item for item in self.items if test(item))


def _wait_until(condition, what, timeout=WAIT):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return
        time.sleep(0.02)
    pytest.fail(f"non è successo: {what}")


@pytest.fixture
def ids(server):
    return server["user_ids"]


@pytest.fixture
def friends(server, ids):
    """friends("Primo", "Secondo") li rende amici (con le funzioni di P45); alla fine l'amicizia si toglie."""
    app, made = server["app"], []

    def _make(a, b):
        with app.app_context():
            friend_service.send_request(ids[a], uuid.uuid4().hex, b)
            friend_service.accept_request(ids[b], ids[a])
        made.append((a, b))

    yield _make
    with app.app_context():
        for a, b in made:
            friend_service.remove_friend(ids[a], ids[b])


@pytest.fixture(autouse=True)
def clean(server, ids):
    """Nessuna scheda collegata all'inizio; alla fine niente inviti aperti, code o partite."""
    _wait_until(lambda: presence.count() == 0, "chiusura delle schede delle prove precedenti")
    yield
    for user_id in ids.values():
        invites.cancel_all_of(user_id)
        matchmaker.queue.leave(user_id)
        room = find_room_of_user(user_id)
        if room is not None:
            room.run(room._stop_timers)
            rooms.remove(room.id)


def _invite(client, user_id, mode="1v1", target_score=150, request_id=None):
    return client.call("invite:send", {"request_id": request_id or uuid.uuid4().hex, "user_id": user_id,
                                       "mode": mode, "target_score": target_score}, timeout=WAIT)


def _call(client, event, invite_id):
    return client.call(event, {"invite_id": invite_id}, timeout=WAIT)


# --- Amici online (5.2) ---------------------------------------------------------


def test_un_amico_che_si_collega_appare_online(connect, ids, friends):
    friends("Primo", "Secondo")
    primo = connect("Primo")
    presence_events = Events(primo, "friends:presence")
    secondo = connect("Secondo")
    presence_events.wait_for(lambda p: p == {"user_id": ids["Secondo"], "presence": "online"})
    secondo.disconnect()
    presence_events.wait_for(lambda p: p == {"user_id": ids["Secondo"], "presence": "offline"})


def test_chi_non_e_amico_non_riceve_la_presenza(connect, ids, friends):
    friends("Primo", "Secondo")
    terzo = connect("Terzo")
    presence_events = Events(terzo, "friends:presence")
    primo = connect("Primo")
    presence_events_primo = Events(primo, "friends:presence")
    connect("Secondo")
    presence_events_primo.wait_for(lambda p: p["user_id"] == ids["Secondo"])
    assert presence_events.items == []


def test_friends_changed_dopo_richiesta_e_blocco(server, connect, ids):
    app = server["app"]
    primo, terzo = connect("Primo"), connect("Terzo")
    changed_primo, changed_terzo = Events(primo, "friends:changed"), Events(terzo, "friends:changed")
    with app.app_context():
        friend_service.send_request(ids["Terzo"], uuid.uuid4().hex, "Primo")
    changed_primo.wait_for(lambda c: c == {"reason": "request_received"})
    with app.app_context():
        friend_service.accept_request(ids["Primo"], ids["Terzo"])
    changed_terzo.wait_for(lambda c: c == {"reason": "request_accepted"})
    try:
        with app.app_context():
            friend_service.block(ids["Primo"], uuid.uuid4().hex, ids["Terzo"])
        changed_terzo.wait_for(lambda c: c == {"reason": "friend_removed"})
        changed_primo.wait_for(lambda c: c == {"reason": "blocked"})
        assert {"reason": "blocked"} not in changed_terzo.items  # chi è bloccato non lo sa
    finally:
        with app.app_context():
            friend_service.unblock(ids["Primo"], ids["Terzo"])


# --- Inviti (5.3) ---------------------------------------------------------------


def test_invito_1v1_accettato_porta_i_due_nella_stessa_stanza(connect, ids, friends):
    friends("Primo", "Secondo")
    primo, secondo = connect("Primo"), connect("Secondo")
    received = Events(secondo, "invite:received")
    updates = [Events(primo, "invite:update"), Events(secondo, "invite:update")]
    starts = [Events(primo, "game:start"), Events(secondo, "game:start")]
    in_game = Events(secondo, "friends:presence")

    answer = _invite(primo, ids["Secondo"], "1v1", 300)
    assert answer["ok"] is True
    invite = answer["data"]
    assert invite["from"]["user_id"] == ids["Primo"] and invite["to"]["user_id"] == ids["Secondo"]
    assert invite["mode"] == "1v1" and invite["target_score"] == 300 and invite["status"] == "pending"
    assert 55 < invite["seconds_left"] <= 60
    assert received.wait_for()["invite_id"] == invite["invite_id"]

    assert _call(secondo, "invite:accept", invite["invite_id"]) == ok()
    for events in updates:
        events.wait_for(lambda u: u == {"invite_id": invite["invite_id"], "status": "accepted"})
    assert _call(primo, "invite:start", invite["invite_id"]) == ok()

    game_ids = {s.wait_for()["game_id"] for s in starts}
    assert len(game_ids) == 1
    room = rooms.get(game_ids.pop())
    assert {p.user_id for p in room.players} == {ids["Primo"], ids["Secondo"]}
    assert room.rated is False and room.game.target_score == 300  # 1v1 contro un amico: niente rating (D36)
    for events in updates:
        events.wait_for(lambda u: u["status"] == "started")
    in_game.wait_for(lambda p: p == {"user_id": ids["Primo"], "presence": "in_game"})


def test_invito_2v2_accettato_mette_la_coppia_in_coda(connect, ids, friends):
    friends("Primo", "Secondo")
    primo, secondo = connect("Primo"), connect("Secondo")
    queue_secondo = Events(secondo, "queue:status")
    invite = _invite(primo, ids["Secondo"], "2v2", 500)["data"]
    assert _call(secondo, "invite:accept", invite["invite_id"]) == ok()

    answer = _call(primo, "invite:start", invite["invite_id"])
    assert answer["ok"] is True
    assert answer["data"]["mode"] == "2v2" and answer["data"]["target_score"] == 500
    assert answer["data"]["partner"]["user_id"] == ids["Secondo"]
    assert queue_secondo.wait_for()["partner"]["user_id"] == ids["Primo"]
    assert ids["Primo"] in matchmaker.queue and ids["Secondo"] in matchmaker.queue


def test_rifiutato_avvisa_chi_ha_invitato(connect, ids, friends):
    friends("Primo", "Secondo")
    primo, secondo = connect("Primo"), connect("Secondo")
    updates = Events(primo, "invite:update")
    invite = _invite(primo, ids["Secondo"])["data"]
    assert _call(secondo, "invite:decline", invite["invite_id"]) == ok()
    updates.wait_for(lambda u: u == {"invite_id": invite["invite_id"], "status": "declined"})
    # dopo un rifiuto si può invitare di nuovo (D27)
    assert _invite(primo, ids["Secondo"])["ok"] is True


def test_si_puo_rifiutare_anche_dopo_aver_accettato(connect, ids, friends):
    friends("Primo", "Secondo")
    primo, secondo = connect("Primo"), connect("Secondo")
    updates = Events(primo, "invite:update")
    invite = _invite(primo, ids["Secondo"])["data"]
    assert _call(secondo, "invite:accept", invite["invite_id"]) == ok()
    assert _call(secondo, "invite:decline", invite["invite_id"]) == ok()
    updates.wait_for(lambda u: u["status"] == "declined")
    answer = _call(primo, "invite:start", invite["invite_id"])
    assert answer["ok"] is False and answer["error"]["code"] == "not_allowed"


def test_scaduto_avvisa_chi_ha_invitato(connect, ids, friends, monkeypatch):
    monkeypatch.setattr(invites_module, "INVITE_SECONDS", 0.3)
    friends("Primo", "Secondo")
    primo, secondo = connect("Primo"), connect("Secondo")
    updates = Events(primo, "invite:update")
    invite = _invite(primo, ids["Secondo"])["data"]
    updates.wait_for(lambda u: u == {"invite_id": invite["invite_id"], "status": "expired"})
    answer = _call(secondo, "invite:accept", invite["invite_id"])
    assert answer["ok"] is False and answer["error"]["code"] == "expired"


def test_annullato_avvisa_l_invitato(connect, ids, friends):
    friends("Primo", "Secondo")
    primo, secondo = connect("Primo"), connect("Secondo")
    updates = Events(secondo, "invite:update")
    invite = _invite(primo, ids["Secondo"])["data"]
    assert _call(primo, "invite:cancel", invite["invite_id"]) == ok()
    updates.wait_for(lambda u: u == {"invite_id": invite["invite_id"], "status": "cancelled"})
    assert _call(primo, "invite:cancel", invite["invite_id"]) == ok()  # seconda volta: niente da fare


def test_chi_chiude_l_ultima_scheda_annulla_l_invito(connect, ids, friends):
    friends("Primo", "Secondo")
    primo, secondo = connect("Primo"), connect("Secondo")
    updates = Events(primo, "invite:update")
    invite = _invite(primo, ids["Secondo"])["data"]
    secondo.disconnect()
    updates.wait_for(lambda u: u == {"invite_id": invite["invite_id"], "status": "cancelled"})


def test_non_si_invita_chi_non_e_amico(connect, ids):
    connect("Terzo")
    answer = _invite(connect("Primo"), ids["Terzo"])
    assert answer["ok"] is False and answer["error"]["code"] == "not_friends"


def test_non_si_invita_un_amico_offline(connect, ids, friends):
    friends("Primo", "Secondo")
    answer = _invite(connect("Primo"), ids["Secondo"])
    assert answer["ok"] is False and answer["error"]["code"] == "offline"


def test_non_si_invita_chi_e_gia_in_partita(connect, ids, friends):
    friends("Primo", "Secondo")
    primo = connect("Primo")
    connect("Secondo")
    room = create_room([Player(ids["Secondo"], "Secondo"), Player(ids["Terzo"], "Terzo")], "1v1", 150)
    try:
        answer = _invite(primo, ids["Secondo"])
        assert answer["ok"] is False and answer["error"]["code"] == "busy"
    finally:
        room.run(room._stop_timers)
        rooms.remove(room.id)


def test_un_invito_alla_volta(connect, ids, friends):
    friends("Primo", "Secondo")
    friends("Primo", "Terzo")
    primo = connect("Primo")
    connect("Secondo")
    connect("Terzo")
    assert _invite(primo, ids["Secondo"])["ok"] is True
    answer = _invite(primo, ids["Terzo"])
    assert answer["ok"] is False and answer["error"]["code"] == "busy"


def test_doppio_clic_un_solo_invito(connect, ids, friends):
    friends("Primo", "Secondo")
    primo, secondo = connect("Primo"), connect("Secondo")
    received = Events(secondo, "invite:received")
    request_id = uuid.uuid4().hex
    first = _invite(primo, ids["Secondo"], request_id=request_id)
    assert _invite(primo, ids["Secondo"], request_id=request_id) == first
    received.wait_for()
    assert len(received.items) == 1


def test_solo_chi_ha_invitato_avvia_e_solo_l_invitato_accetta(connect, ids, friends):
    friends("Primo", "Secondo")
    primo, secondo = connect("Primo"), connect("Secondo")
    invite = _invite(primo, ids["Secondo"])["data"]
    assert _call(primo, "invite:accept", invite["invite_id"])["error"]["code"] == "not_found"
    assert _call(secondo, "invite:start", invite["invite_id"])["error"]["code"] == "not_found"
    assert _call(primo, "invite:start", invite["invite_id"])["error"]["code"] == "not_allowed"  # non ancora accettato


@pytest.mark.parametrize("event, data", [
    ("invite:send", None),
    ("invite:send", {"user_id": 1, "mode": "1v1", "target_score": 150}),
    ("invite:send", {"request_id": "r", "user_id": "2", "mode": "1v1", "target_score": 150}),
    ("invite:send", {"request_id": "r", "user_id": True, "mode": "1v1", "target_score": 150}),
    ("invite:send", {"request_id": "r", "user_id": 2, "mode": "3v3", "target_score": 150}),
    ("invite:send", {"request_id": "r", "user_id": 2, "mode": "1v1", "target_score": 200}),
    ("invite:accept", {"invite_id": 5}),
    ("invite:accept", {"invite_id": ""}),
    ("invite:start", {"invite_id": "x" * 65}),
    ("invite:cancel", []),
])
def test_dati_non_validi(connect, event, data):
    answer = connect("Primo").call(event, data, timeout=WAIT)
    assert answer["ok"] is False and answer["error"]["code"] == "invalid_data"


def test_invitare_se_stessi(connect, ids):
    answer = _invite(connect("Primo"), ids["Primo"])
    assert answer["ok"] is False and answer["error"]["code"] == "invalid_data"
