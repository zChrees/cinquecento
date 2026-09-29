"""Amici online e inviti a partita (P47; contratto 5.2 e 5.3; D27, D36).

Con il server vero e client simulati:
- un amico che si collega o esce appare online / offline agli altri (friends:presence),
  anche "in_game" quando comincia una partita;
- friends:changed dopo richieste e blocchi (chi è bloccato riceve solo "friend_removed");
- un invito 1v1 accettato porta i due nella stessa stanza, senza rating; un invito 2v2
  accettato mette la coppia in coda;
- rifiutato, scaduto e annullato avvisano chi ha invitato (invite:update);
- non si invita chi non è amico, chi è offline o chi è già in partita; un invito alla
  volta nel 1v1; doppio clic con lo stesso request_id; chi chiude l'ultima scheda annulla;
- 2v2 con più amici (P59): fino a tre amici agli stessi punti; con tre che accettano la
  partita parte subito senza rating, con due il gruppo entra in coda e il quarto
  arriva dalla coda, con uno la coppia come prima; "Gioca" annulla gli inviti in attesa.
"""

import threading
import time
import uuid

import pytest
import sqlalchemy as sa

from app.realtime import invites as invites_module
from app.realtime.events import EventError, ok
from app.realtime.invites import Invites, invites
from app.realtime.matchmaking import matchmaker
from app.realtime.presence import presence
from app.realtime.room import Player
from app.realtime.room_manager import create_room, find_room_of_user, rooms
from app.services import auth_service, friend_service
from config import load_config

WAIT = 5
PASSWORD = "Password-di-prova-1"  # la stessa di conftest.py


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


@pytest.fixture(scope="module")
def ids(server):
    """Gli utenti di conftest.py più "Quarto" (il quarto amico del 2v2, P59), registrato
    solo se non c'è già (lo usa anche test_matchmaking_2v2.py)."""
    engine = sa.create_engine(load_config("testing").SQLALCHEMY_DATABASE_URI)
    try:
        with engine.connect() as conn:
            quarto = conn.execute(sa.text("SELECT id FROM utenti WHERE nome_utente = 'Quarto'")).scalar()
    finally:
        engine.dispose()
    if quarto is None:
        with server["app"].app_context():
            quarto = auth_service.register("Quarto", "quarto@esempio.it", PASSWORD).id
    return {**server["user_ids"], "Quarto": quarto}


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


def test_blocca_sblocca_amici_di_nuovo_tutte_e_due_le_liste_si_aggiornano(server, connect, ids):
    """P65: blocca → sblocca → richiesta → accetta. Chi accetta (da una scheda) deve
    rileggere la lista anche nelle altre schede, per esempio la home con la carta
    "Gioca con un amico": prima friends:changed arrivava solo all'altro."""
    app = server["app"]
    primo, secondo = connect("Primo"), connect("Secondo")
    changed_primo, changed_secondo = Events(primo, "friends:changed"), Events(secondo, "friends:changed")
    try:
        with app.app_context():
            friend_service.send_request(ids["Primo"], uuid.uuid4().hex, "Secondo")
            friend_service.accept_request(ids["Secondo"], ids["Primo"])
            friend_service.block(ids["Primo"], uuid.uuid4().hex, ids["Secondo"])
            friend_service.unblock(ids["Primo"], ids["Secondo"])
        changed_primo.items.clear()
        changed_secondo.items.clear()
        with app.app_context():
            friend_service.send_request(ids["Primo"], uuid.uuid4().hex, "Secondo")
            friend_service.accept_request(ids["Secondo"], ids["Primo"])
        changed_primo.wait_for(lambda c: c == {"reason": "request_accepted"})
        changed_secondo.wait_for(lambda c: c == {"reason": "request_accepted"})  # anche chi ha accettato
        with app.app_context():
            listed = {f["user_id"]: f["presence"] for f in friend_service.overview(ids["Secondo"])["friends"]}
        assert listed == {ids["Primo"]: "online"}
    finally:
        with app.app_context():
            friend_service.remove_friend(ids["Primo"], ids["Secondo"])


@pytest.mark.parametrize("action, reason", [
    ("accept", "request_accepted"),
    ("decline", "request_declined"),
    ("cancel", "request_declined"),
    ("remove", "friend_removed"),
    ("unblock", "blocked"),
])
def test_chi_cambia_la_lista_la_rilegge_anche_nelle_altre_schede(server, connect, ids, action, reason):
    """P65: ogni cambiamento di amicizie arriva anche alle schede di chi lo fa (Primo).
    La scheda si collega dopo la preparazione: gli avvisi di prima non le arrivano."""
    app = server["app"]
    with app.app_context():
        if action in ("accept", "decline"):
            friend_service.send_request(ids["Secondo"], uuid.uuid4().hex, "Primo")
        elif action == "cancel":
            friend_service.send_request(ids["Primo"], uuid.uuid4().hex, "Secondo")
        elif action == "remove":
            friend_service.send_request(ids["Primo"], uuid.uuid4().hex, "Secondo")
            friend_service.accept_request(ids["Secondo"], ids["Primo"])
        else:
            friend_service.block(ids["Primo"], uuid.uuid4().hex, ids["Secondo"])
    changed = Events(connect("Primo"), "friends:changed")
    try:
        with app.app_context():
            {
                "accept": lambda: friend_service.accept_request(ids["Primo"], ids["Secondo"]),
                "decline": lambda: friend_service.decline_request(ids["Primo"], ids["Secondo"]),
                "cancel": lambda: friend_service.cancel_request(ids["Primo"], ids["Secondo"]),
                "remove": lambda: friend_service.remove_friend(ids["Primo"], ids["Secondo"]),
                "unblock": lambda: friend_service.unblock(ids["Primo"], ids["Secondo"]),
            }[action]()
        assert changed.wait_for() == {"reason": reason}
    finally:
        with app.app_context():
            friend_service.remove_friend(ids["Primo"], ids["Secondo"])
            friend_service.unblock(ids["Primo"], ids["Secondo"])


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


def test_un_invito_alla_volta_anche_nel_2v2_verso_il_1v1(connect, ids, friends):
    friends("Primo", "Secondo")
    friends("Primo", "Terzo")
    primo = connect("Primo")
    connect("Secondo")
    connect("Terzo")
    assert _invite(primo, ids["Secondo"], "2v2", 150)["ok"] is True
    for mode, target in (("1v1", 150), ("2v2", 300)):  # il gruppo ha già modalità e punti
        answer = _invite(primo, ids["Terzo"], mode, target)
        assert answer["ok"] is False and answer["error"]["code"] == "busy", (mode, target)


# --- 2v2 con più amici (P59) ------------------------------------------------------


def _group(connect, ids, friends, names, target_score=300, make_friends=True):
    """Primo invita `names` nel 2v2 e tutti accettano; restituisce (primo, clients, inviti)."""
    for name in names if make_friends else ():
        friends("Primo", name)
    primo = connect("Primo")
    clients = {name: connect(name) for name in names}
    sent = {}
    for name in names:
        answer = _invite(primo, ids[name], "2v2", target_score)
        assert answer["ok"] is True, answer
        sent[name] = answer["data"]
    for name in names:
        assert _call(clients[name], "invite:accept", sent[name]["invite_id"]) == ok()
    return primo, clients, sent


def test_2v2_tre_amici_partita_subito_squadre_a_sorte_senza_rating(connect, ids, friends):
    names = ("Secondo", "Terzo", "Quarto")
    primo, clients, sent = _group(connect, ids, friends, names)
    starts = [Events(c, "game:start") for c in (primo, *clients.values())]
    updates = Events(primo, "invite:update")

    assert _call(primo, "invite:start", sent["Terzo"]["invite_id"]) == ok()  # vale qualunque invito del gruppo
    game_ids = {s.wait_for()["game_id"] for s in starts}
    assert len(game_ids) == 1
    room = rooms.get(game_ids.pop())
    assert {p.user_id for p in room.players} == {ids[n] for n in ("Primo", *names)}
    assert len(room.players) == 4 and room.rated is False and room.game.target_score == 300
    for invite in sent.values():
        updates.wait_for(lambda u, i=invite: u == {"invite_id": i["invite_id"], "status": "started"})
    assert invites.group_of(ids["Primo"]) == []


def test_2v2_tre_amici_squadre_diverse_da_una_partita_all_altra(connect, ids, friends):
    """Le squadre le decide il caso: in 20 partite Primo non ha sempre lo stesso compagno."""
    names = ("Secondo", "Terzo", "Quarto")
    for name in names:
        friends("Primo", name)
    partners = set()
    for _ in range(20):
        primo, clients, sent = _group(connect, ids, friends, names, make_friends=False)
        start = Events(primo, "game:start")
        assert _call(primo, "invite:start", sent["Secondo"]["invite_id"]) == ok()
        room = rooms.get(start.wait_for()["game_id"])
        seat = room.seat_of(ids["Primo"])
        partners.add(room.players[(seat + 2) % 4].user_id)
        room.run(room._stop_timers)
        rooms.remove(room.id)
        for client in (primo, *clients.values()):
            client.disconnect()
        _wait_until(lambda: presence.count() == 0, "chiusura delle schede")
        if len(partners) > 1:
            break
    assert len(partners) > 1


def test_2v2_due_amici_il_gruppo_va_in_coda_e_il_quarto_arriva_dalla_coda(connect, ids, friends):
    names = ("Secondo", "Terzo")
    primo, clients, sent = _group(connect, ids, friends, names, target_score=150)
    queued = {name: Events(clients[name], "queue:status") for name in names}
    start = Events(primo, "game:start")

    answer = _call(primo, "invite:start", sent["Secondo"]["invite_id"])
    assert answer["ok"] is True and answer["data"]["mode"] == "2v2"
    views = {"Primo": answer["data"], **{n: queued[n].wait_for() for n in names}}
    alone = [n for n, v in views.items() if v["partner"] is None]
    assert len(alone) == 1 and len(views[alone[0]]["opponents"]) == 2
    for name in ("Primo", *names):
        assert ids[name] in matchmaker.queue

    quarto = connect("Quarto")
    assert quarto.call("queue:join", {"request_id": uuid.uuid4().hex, "mode": "2v2",
                                      "target_score": 150}, timeout=WAIT)["ok"] is True
    room = rooms.get(start.wait_for()["game_id"])
    assert room.rated is True
    assert room.seat_of(ids["Quarto"]) % 2 == room.seat_of(ids[alone[0]]) % 2


def test_2v2_gioca_con_un_solo_accettato_annulla_gli_altri(connect, ids, friends):
    friends("Primo", "Secondo")
    friends("Primo", "Terzo")
    primo, secondo, terzo = connect("Primo"), connect("Secondo"), connect("Terzo")
    updates_terzo = Events(terzo, "invite:update")
    first = _invite(primo, ids["Secondo"], "2v2", 500)["data"]
    second = _invite(primo, ids["Terzo"], "2v2", 500)["data"]
    assert _call(secondo, "invite:accept", first["invite_id"]) == ok()

    answer = _call(primo, "invite:start", first["invite_id"])
    assert answer["ok"] is True and answer["data"]["partner"]["user_id"] == ids["Secondo"]
    assert answer["data"]["opponents"] == []
    updates_terzo.wait_for(lambda u: u == {"invite_id": second["invite_id"], "status": "cancelled"})
    assert ids["Terzo"] not in matchmaker.queue
    assert _call(terzo, "invite:accept", second["invite_id"])["error"]["code"] == "not_found"


def test_2v2_gioca_solo_dopo_almeno_un_accettato(connect, ids, friends):
    friends("Primo", "Secondo")
    friends("Primo", "Terzo")
    primo = connect("Primo")
    connect("Secondo")
    connect("Terzo")
    first = _invite(primo, ids["Secondo"], "2v2", 150)["data"]
    _invite(primo, ids["Terzo"], "2v2", 150)
    assert _call(primo, "invite:start", first["invite_id"])["error"]["code"] == "not_allowed"


def test_2v2_chi_e_nel_gruppo_non_manda_ne_riceve_altri_inviti(connect, ids, friends):
    friends("Primo", "Secondo")
    friends("Terzo", "Secondo")
    friends("Terzo", "Primo")
    primo, secondo, terzo = connect("Primo"), connect("Secondo"), connect("Terzo")
    assert _invite(primo, ids["Secondo"], "2v2", 150)["ok"] is True
    # chi ha ricevuto un invito non ne manda; chi ha già un invito non ne riceve
    assert _invite(secondo, ids["Terzo"], "2v2", 150)["error"]["code"] == "busy"
    assert _invite(terzo, ids["Secondo"], "2v2", 150)["error"]["code"] == "busy"
    assert _invite(terzo, ids["Primo"], "2v2", 150)["error"]["code"] == "busy"


def test_2v2_al_massimo_tre_amici():
    """Il limite del gruppo, con la classe degli inviti da sola (servirebbe un quinto utente)."""
    group = Invites()
    me = Player(1, "Io")
    try:
        for n in (2, 3, 4):
            group.send(me, Player(n, f"U{n}"), "2v2", 150)
        with pytest.raises(EventError) as exc:
            group.send(me, Player(5, "U5"), "2v2", 150)
        assert exc.value.code == "busy" and "3 amici" in exc.value.message
        assert [i.recipient.user_id for i in group.group_of(1)] == [2, 3, 4]
    finally:
        group.cancel_all_of(1)


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
