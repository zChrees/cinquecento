"""Coda 2v2 (P29; D17; contratto 4).

- Prima la coda da sola, con un orologio finto: quattro singoli in squadre con le medie
  più vicine (D17), la coppia già formata sempre nella stessa squadra, contro due singoli
  o un'altra coppia, chi esce prima dell'abbinamento non blocca gli altri, se esce uno
  della coppia esce tutta la coppia.
- Poi con il server vero e client simulati: quattro singoli al tavolo con game:start,
  la coppia entrata con matchmaker.join_pair (come farà invite:start, P47) seduta nella
  stessa squadra, "partner_left" al compagno, busy.
"""

import threading
import uuid

import pytest
import sqlalchemy as sa

from app.realtime.events import ok
from app.realtime.matchmaking import MatchQueue, matchmaker
from app.realtime.room import Player
from app.realtime.room_manager import find_room_of_user, rooms
from app.services import auth_service
from config import load_config

WAIT = 5
PASSWORD = "Password-di-prova-1"

# --- La coda da sola, con un orologio finto ------------------------------------


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def _p(n):
    return Player(user_id=n, username=f"U{n}")


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def queue(clock):
    return MatchQueue(clock)


def _single(queue, clock, n, rating, target=150):
    queue.join(_p(n), "2v2", target, rating)
    clock.now += 1  # ognuno entra un secondo dopo l'altro


def _teams(match):
    return {frozenset(p.user_id for p in team) for team in match.teams}


def test_quattro_singoli_squadre_con_le_medie_piu_vicine(queue, clock):
    for n, rating in ((1, 1500), (2, 1510), (3, 1580), (4, 1590)):
        _single(queue, clock, n, rating)
    [match] = queue.take_matches()
    assert match.mode == "2v2" and match.target_score == 150
    assert _teams(match) == {frozenset({1, 4}), frozenset({2, 3})}  # 3090 contro 3090
    assert len(queue) == 0


def test_tre_singoli_non_bastano(queue, clock):
    for n in (1, 2, 3):
        _single(queue, clock, n, 1500)
    clock.now += 500
    assert queue.take_matches() == []
    assert len(queue) == 3


def test_code_1v1_e_2v2_separate(queue, clock):
    queue.join(_p(1), "1v1", 150, 1500)
    queue.join(_p(2), "1v1", 150, 1500)
    queue.join(_p(3), "2v2", 150, 1500)
    queue.join(_p(4), "2v2", 150, 1500)
    [match] = queue.take_matches()
    assert match.mode == "1v1" and set(match.user_ids) == {1, 2}
    assert 3 in queue and 4 in queue


def test_punteggi_diversi_non_si_abbinano(queue, clock):
    for n in (1, 2, 3):
        _single(queue, clock, n, 1500)
    _single(queue, clock, 4, 1500, target=300)
    clock.now += 500
    assert queue.take_matches() == []


def test_coppia_contro_due_singoli_resta_unita(queue, clock):
    queue.join_entry((_p(1), _p(2)), (1400, 1600), "2v2", 300)
    _single(queue, clock, 3, 1450, target=300)
    _single(queue, clock, 4, 1550, target=300)
    [match] = queue.take_matches()
    assert _teams(match) == {frozenset({1, 2}), frozenset({3, 4})}


def test_coppia_contro_coppia(queue, clock):
    queue.join_entry((_p(1), _p(2)), (1500, 1500), "2v2", 500)
    queue.join_entry((_p(3), _p(4)), (1450, 1550), "2v2", 500)
    [match] = queue.take_matches()
    assert _teams(match) == {frozenset({1, 2}), frozenset({3, 4})}


def test_coppia_e_un_solo_singolo_non_bastano(queue, clock):
    queue.join_entry((_p(1), _p(2)), (1500, 1500), "2v2", 150)
    _single(queue, clock, 3, 1500)
    clock.now += 500
    assert queue.take_matches() == []


def test_con_due_coppie_e_due_singoli_nessuna_coppia_divisa(queue, clock):
    queue.join_entry((_p(1), _p(2)), (1500, 1500), "2v2", 150)
    queue.join_entry((_p(3), _p(4)), (1500, 1500), "2v2", 150)
    _single(queue, clock, 5, 1500)
    _single(queue, clock, 6, 1500)
    matches = queue.take_matches()
    assert len(matches) == 1
    for team in _teams(matches[0]):
        assert team in ({1, 2}, {3, 4}, {5, 6})


def test_la_coppia_vale_la_media_e_vede_il_compagno(queue):
    statuses = queue.join_entry((_p(1), _p(2)), (1400, 1700), "2v2", 150)
    assert statuses[1]["rating_range"] == {"min": 1450, "max": 1650}
    assert statuses[1]["partner"] == {"user_id": 2, "username": "U2", "avatar": None}
    assert statuses[2]["partner"]["user_id"] == 1
    assert queue.status(2)["partner"]["user_id"] == 1
    assert len(queue) == 2


def test_singolo_2v2_senza_compagno(queue):
    status = queue.join(_p(1), "2v2", 150, 1500)
    assert status["mode"] == "2v2" and status["partner"] is None


def test_rating_lontani_solo_dopo_l_allargamento(queue, clock):
    queue.join_entry((_p(1), _p(2)), (1500, 1500), "2v2", 150)
    queue.join_entry((_p(3), _p(4)), (1800, 1800), "2v2", 150)
    clock.now += 39.9  # ±250
    assert queue.take_matches() == []
    clock.now += 10.1  # ±350 dopo 50 secondi
    assert len(queue.take_matches()) == 1


def test_tutte_le_voci_si_devono_accettare(queue, clock):
    # 1 e 4 sono lontani 300: con ±100 tutti i quattro insieme non si accettano
    for n, rating in ((1, 1500), (2, 1600), (3, 1700), (4, 1800)):
        queue.join(_p(n), "2v2", 150, rating)
    assert queue.take_matches() == []
    clock.now += 50  # ±350
    assert len(queue.take_matches()) == 1


def test_se_esce_uno_della_coppia_esce_tutta_la_coppia(queue):
    queue.join_entry((_p(1), _p(2)), (1500, 1500), "2v2", 150)
    entry = queue.leave(2)
    assert entry.user_ids == (1, 2)
    assert 1 not in queue and 2 not in queue and len(queue) == 0


def test_coppia_con_un_giocatore_gia_in_coda_busy(queue):
    queue.join(_p(2), "1v1", 150, 1500)
    with pytest.raises(Exception) as exc:
        queue.join_entry((_p(1), _p(2)), (1500, 1500), "2v2", 150)
    assert exc.value.code == "busy"
    assert 1 not in queue


def test_chi_esce_prima_non_blocca_gli_altri(queue, clock):
    for n in (1, 2, 3, 4, 5):
        _single(queue, clock, n, 1500)
    queue.leave(1)
    [match] = queue.take_matches()
    assert set(match.user_ids) == {2, 3, 4, 5}


def test_prima_chi_aspetta_da_piu_tempo(queue, clock):
    for n in (1, 2, 3, 4, 5):
        _single(queue, clock, n, 1500)
    [match] = queue.take_matches()
    assert 1 in match.user_ids and 5 in queue


def test_molti_in_coda_tutti_abbinati(queue, clock):
    for n in range(1, 41):
        _single(queue, clock, n, 1400 + n * 5)
    matches = queue.take_matches()
    assert len(matches) == 10
    assert sorted(u for m in matches for u in m.user_ids) == list(range(1, 41))


def test_la_coppia_rimessa_in_coda_resta_coppia(queue):
    queue.join_entry((_p(1), _p(2)), (1500, 1500), "2v2", 150)
    entry = queue.leave(1)
    queue.requeue(entry)
    assert queue.status(1)["partner"]["user_id"] == 2 and queue.status(2)["partner"]["user_id"] == 1


# --- Gruppo di tre amici (P59): una coppia e il suo avversario ------------------


def _group(queue, ratings=(1500, 1500, 1500), target=150):
    """1 e 2 fanno coppia, 3 gioca contro di loro."""
    return queue.join_entry((_p(1), _p(2), _p(3)), ratings, "2v2", target, sides=(0, 0, 1))


def test_gruppo_di_tre_con_un_singolo_squadre_fisse(queue, clock):
    _group(queue)
    _single(queue, clock, 4, 1500)
    [match] = queue.take_matches()
    assert _teams(match) == {frozenset({1, 2}), frozenset({3, 4})}
    assert len(queue) == 0


def test_gruppo_di_tre_sempre_diviso_come_deciso(queue, clock):
    # anche quando squadre diverse sarebbero più bilanciate
    _group(queue, (1300, 1300, 1700))
    _single(queue, clock, 4, 1700)
    clock.now += 500
    [match] = queue.take_matches()
    assert _teams(match) == {frozenset({1, 2}), frozenset({3, 4})}


def test_gruppo_di_tre_non_gioca_con_una_coppia(queue, clock):
    _group(queue)
    queue.join_entry((_p(5), _p(6)), (1500, 1500), "2v2", 150)
    clock.now += 500
    assert queue.take_matches() == []
    _single(queue, clock, 7, 1500)
    [match] = queue.take_matches()
    assert set(match.user_ids) == {1, 2, 3, 7}
    assert 5 in queue and 6 in queue


def test_gruppo_di_tre_vede_compagno_e_avversari(queue):
    statuses = _group(queue)
    assert statuses[1]["partner"]["user_id"] == 2 and statuses[2]["partner"]["user_id"] == 1
    assert statuses[1]["opponents"] == [{"user_id": 3, "username": "U3", "avatar": None}]
    assert statuses[3]["partner"] is None
    assert [o["user_id"] for o in statuses[3]["opponents"]] == [1, 2]
    assert queue.status(3) == statuses[3]


def test_singolo_e_coppia_senza_avversari_noti(queue):
    assert queue.join(_p(1), "2v2", 150, 1500)["opponents"] == []
    statuses = queue.join_entry((_p(2), _p(3)), (1500, 1500), "2v2", 150)
    assert statuses[2]["opponents"] == [] and statuses[3]["opponents"] == []


def test_se_esce_uno_del_gruppo_escono_tutti(queue):
    _group(queue)
    entry = queue.leave(3)
    assert entry.user_ids == (1, 2, 3) and len(queue) == 0


# --- Con il server vero --------------------------------------------------------


class Events:
    """Raccoglie tutti gli eventi di un nome; `wait(n)` aspetta che ne siano arrivati n."""

    def __init__(self, client, event):
        self.items = []
        self._cond = threading.Condition()

        def receive(data):
            with self._cond:
                self.items.append(data)
                self._cond.notify_all()

        client.on(event, receive)

    def wait(self, n=1, timeout=WAIT):
        with self._cond:
            return self._cond.wait_for(lambda: len(self.items) >= n, timeout)


def _join(client, target_score=150, mode="2v2"):
    return client.call("queue:join", {"request_id": uuid.uuid4().hex, "mode": mode,
                                      "target_score": target_score}, timeout=WAIT)


@pytest.fixture(scope="module")
def ids(server):
    """Gli utenti di conftest.py più "Quarto" (serve al 2v2), registrato se non c'è già."""
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


@pytest.fixture(autouse=True)
def clean_queue(ids):
    """Coda vuota prima e dopo ogni prova; le partite create dalla coda si fermano e si tolgono."""

    def clean():
        for user_id in ids.values():
            matchmaker.queue.leave(user_id)
            room = find_room_of_user(user_id)
            if room is not None:
                room.run(room._stop_timers)
                rooms.remove(room.id)

    clean()
    yield
    clean()


def _user(ids, name):
    return Player(ids[name], name)


def test_quattro_singoli_al_tavolo(connect, ids):
    names = ("Primo", "Secondo", "Terzo", "Quarto")
    clients = {name: connect(name) for name in names}
    starts = {name: Events(client, "game:start") for name, client in clients.items()}
    for name in names:
        answer = _join(clients[name], 300)
        assert answer["ok"] is True and answer["data"]["partner"] is None, name
    assert all(s.wait() for s in starts.values()), "game:start non arrivato a tutti"
    game_ids = {s.items[0]["game_id"] for s in starts.values()}
    assert len(game_ids) == 1
    room = rooms.get(game_ids.pop())
    assert {p.user_id for p in room.players} == {ids[n] for n in names}
    assert len(room.players) == 4 and room.rated is True and room.game.target_score == 300
    assert room._app is not None, "partita creata fuori da Flask: a fine partita non si salverebbe (P26)"


def test_coppia_con_due_singoli_nella_stessa_squadra(server, connect, ids):
    terzo, quarto = connect("Terzo"), connect("Quarto")
    primo, secondo = connect("Primo"), connect("Secondo")
    start = Events(primo, "game:start")
    with server["app"].app_context():
        status = matchmaker.join_pair(server["app"], _user(ids, "Primo"), _user(ids, "Secondo"), 150)
    assert status["partner"]["user_id"] == ids["Secondo"]
    assert _join(terzo)["ok"] and _join(quarto)["ok"]
    assert start.wait(), "game:start non arrivato"
    room = rooms.get(start.items[0]["game_id"])
    assert room.seat_of(ids["Primo"]) % 2 == room.seat_of(ids["Secondo"]) % 2
    assert room.seat_of(ids["Terzo"]) % 2 == room.seat_of(ids["Quarto"]) % 2
    assert room.seat_of(ids["Primo"]) % 2 != room.seat_of(ids["Terzo"]) % 2
    assert secondo.connected


def test_il_compagno_riceve_lo_stato_e_partner_left(server, connect, ids):
    primo, secondo = connect("Primo"), connect("Secondo")
    status_secondo = Events(secondo, "queue:status")
    left_primo, left_secondo = Events(primo, "queue:left"), Events(secondo, "queue:left")
    with server["app"].app_context():
        matchmaker.join_pair(server["app"], _user(ids, "Primo"), _user(ids, "Secondo"), 500)
    assert status_secondo.wait(), "il compagno non ha ricevuto queue:status"
    assert status_secondo.items[0]["partner"]["user_id"] == ids["Primo"]
    assert status_secondo.items[0]["mode"] == "2v2" and status_secondo.items[0]["target_score"] == 500

    assert primo.call("queue:leave", {}, timeout=WAIT) == ok()
    assert left_primo.wait() and left_secondo.wait()
    assert left_primo.items[0] == {"reason": "cancelled"}
    assert left_secondo.items[0] == {"reason": "partner_left"}
    assert ids["Primo"] not in matchmaker.queue and ids["Secondo"] not in matchmaker.queue


def test_coppia_busy_se_uno_e_gia_in_coda(server, connect, ids):
    assert _join(connect("Secondo"), mode="1v1")["ok"]
    with server["app"].app_context(), pytest.raises(Exception) as exc:
        matchmaker.join_pair(server["app"], _user(ids, "Primo"), _user(ids, "Secondo"), 150)
    assert exc.value.code == "busy"
    assert ids["Primo"] not in matchmaker.queue


def test_gruppo_di_tre_con_un_singolo_al_tavolo(server, connect, ids):
    """P59: il gruppo entra con matchmaker.join_group (come fa invite:start con due
    amici); la coppia tirata a sorte gioca insieme, il terzo con chi arriva dalla coda."""
    names = ("Primo", "Secondo", "Terzo")
    clients = {name: connect(name) for name in names}
    statuses = {name: Events(clients[name], "queue:status") for name in ("Secondo", "Terzo")}
    start = Events(clients["Primo"], "game:start")
    with server["app"].app_context():
        mine = matchmaker.join_group(server["app"], _user(ids, "Primo"),
                                     [_user(ids, "Secondo"), _user(ids, "Terzo")], 150)
    assert all(s.wait() for s in statuses.values()), "il gruppo non ha ricevuto queue:status"
    views = {"Primo": mine, **{name: s.items[0] for name, s in statuses.items()}}
    alone = [name for name, v in views.items() if v["partner"] is None]
    assert len(alone) == 1, views
    pair = [name for name in names if name not in alone]
    assert views[pair[0]]["partner"]["user_id"] == ids[pair[1]]
    assert [o["user_id"] for o in views[pair[0]]["opponents"]] == [ids[alone[0]]]
    assert {o["user_id"] for o in views[alone[0]]["opponents"]} == {ids[n] for n in pair}

    assert _join(connect("Quarto"))["ok"]
    assert start.wait(), "game:start non arrivato"
    room = rooms.get(start.items[0]["game_id"])
    assert room.rated is True  # dalla coda, come la coppia con un amico (D36)
    side = {name: room.seat_of(ids[name]) % 2 for name in (*names, "Quarto")}
    assert side[pair[0]] == side[pair[1]] != side[alone[0]] == side["Quarto"]


def test_gruppo_con_utenti_ripetuti_rifiutato(server, ids):
    with server["app"].app_context(), pytest.raises(Exception) as exc:
        matchmaker.join_group(server["app"], _user(ids, "Primo"),
                              [_user(ids, "Secondo"), _user(ids, "Secondo")], 150)
    assert exc.value.code == "invalid_data"
    assert ids["Primo"] not in matchmaker.queue


def test_coppia_con_se_stesso_rifiutata(server, ids):
    with server["app"].app_context(), pytest.raises(Exception) as exc:
        matchmaker.join_pair(server["app"], _user(ids, "Primo"), _user(ids, "Primo"), 150)
    assert exc.value.code == "invalid_data"
