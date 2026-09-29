"""Coda 1v1 (P28; D16; contratto 4).

- Prima la coda da sola, con un orologio finto: intervallo che si allarga, abbinamento
  solo se i due si accettano a vicenda, chi aspetta da più tempo servito per primo.
- Poi con il server vero e client simulati: abbinamento subito e game:start, code
  separate per punteggio, rating lontani abbinati solo dopo l'allargamento, Annulla,
  doppio clic, due schede, chi è già in partita, dati non validi, chiusura delle schede.
"""

import threading
import time
import uuid
from datetime import UTC, datetime

import pytest
import sqlalchemy as sa

from app.extensions import socketio
from app.realtime import matchmaking
from app.realtime.events import ok, user_channel
from app.realtime.matchmaking import ANY, MatchQueue, half_width, matchmaker, stage_of
from app.realtime.room import Player
from app.realtime.room_manager import create_room, find_room_of_user, rooms
from config import load_config

WAIT = 5

# --- La coda da sola, con un orologio finto ------------------------------------


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def _player(n):
    return Player(user_id=n, username=f"U{n}")


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def queue(clock):
    return MatchQueue(clock)


@pytest.mark.parametrize("waited, half", [
    (0, 100), (9.9, 100), (10, 150), (25, 200), (59.9, 350), (60, 400), (119.9, 400), (120, None), (500, None),
])
def test_intervallo_si_allarga_come_d16(waited, half):
    assert half_width(stage_of(waited)) == half


def test_valori_di_d16_da_config():
    config = load_config("testing")
    assert (matchmaking.RANGE_START, matchmaking.RANGE_STEP, matchmaking.RANGE_STEP_SECONDS,
            matchmaking.RANGE_MAX, matchmaking.ANY_AFTER_SECONDS) == (100, 50, 10, 400, 120)
    assert matchmaking.RANGE_START == config.MATCH_RANGE_START
    assert matchmaking.ANY_AFTER_SECONDS == config.MATCH_ANY_AFTER_SECONDS


def test_stato_della_coda_nella_forma_del_contratto(queue, clock):
    status = queue.join(_player(1), "1v1", 300, 1540.4)
    assert status == {"mode": "1v1", "target_score": 300, "seconds_waiting": 0,
                      "rating_range": {"min": 1440, "max": 1640}, "partner": None,
                      "opponents": []}
    clock.now += 23.7
    assert queue.status(1)["seconds_waiting"] == 23
    assert queue.status(1)["rating_range"] == {"min": 1340, "max": 1740}
    clock.now += 120
    assert queue.status(1)["rating_range"] is None
    assert queue.status(2) is None


def test_intervallo_non_scende_sotto_zero(queue):
    assert queue.join(_player(1), "1v1", 150, 30)["rating_range"] == {"min": 0, "max": 130}


def test_due_volte_in_coda_busy(queue):
    queue.join(_player(1), "1v1", 150, 1500)
    with pytest.raises(Exception) as exc:
        queue.join(_player(1), "1v1", 500, 1500)
    assert exc.value.code == "busy"
    assert len(queue) == 1


def test_rating_vicini_stesso_punteggio_si_abbinano(queue):
    queue.join(_player(1), "1v1", 150, 1500)
    queue.join(_player(2), "1v1", 150, 1590)
    [match] = queue.take_matches()
    assert set(match.user_ids) == {1, 2}
    assert match.teams in (((_player(1),), (_player(2),)), ((_player(2),), (_player(1),)))
    assert len(queue) == 0


def test_punteggi_diversi_non_si_abbinano(queue, clock):
    queue.join(_player(1), "1v1", 150, 1500)
    queue.join(_player(2), "1v1", 300, 1500)
    clock.now += 500  # anche quando va bene qualunque avversario
    assert queue.take_matches() == []
    assert len(queue) == 2


def test_rating_lontani_solo_dopo_l_allargamento(queue, clock):
    queue.join(_player(1), "1v1", 150, 1500)
    queue.join(_player(2), "1v1", 150, 1700)
    clock.now += 19.9  # ±150: non basta per 200 di differenza
    assert queue.take_matches() == []
    clock.now += 0.1  # ±200
    assert len(queue.take_matches()) == 1


def test_si_devono_accettare_a_vicenda(queue, clock):
    queue.join(_player(1), "1v1", 150, 1500)
    clock.now += 60  # il primo accetta già ±400
    queue.join(_player(2), "1v1", 150, 1750)  # il secondo, appena entrato, solo ±100
    assert queue.take_matches() == []
    clock.now += 29.9  # secondo a ±200: 250 di differenza sono ancora troppi per lui
    assert queue.take_matches() == []
    clock.now += 0.1  # secondo a ±250 dopo 30 secondi
    assert len(queue.take_matches()) == 1


def test_qualunque_avversario_dopo_due_minuti(queue, clock):
    queue.join(_player(1), "1v1", 500, 800)
    queue.join(_player(2), "1v1", 500, 2400)
    clock.now += 119.9
    assert queue.take_matches() == []
    clock.now += 0.1
    assert len(queue.take_matches()) == 1


def test_prima_chi_aspetta_da_piu_tempo_con_il_rating_piu_vicino(queue, clock):
    queue.join(_player(1), "1v1", 150, 1500)
    clock.now += 1
    queue.join(_player(2), "1v1", 150, 1580)
    clock.now += 1
    queue.join(_player(3), "1v1", 150, 1510)
    [match] = queue.take_matches()
    assert match.user_ids == (1, 3)
    assert 2 in queue


def test_aggiornamenti_solo_quando_l_intervallo_cambia(queue, clock):
    queue.join(_player(1), "1v1", 150, 1500)
    assert queue.take_updates() == []
    clock.now += 10
    [(user_id, status)] = queue.take_updates()
    assert user_id == 1 and status["rating_range"] == {"min": 1350, "max": 1650}
    assert queue.take_updates() == []  # stesso intervallo: niente di nuovo
    clock.now += 300
    [(_, status)] = queue.take_updates()
    assert status["rating_range"] is None
    assert stage_of(300) == ANY


def test_annulla_e_rimetti_in_coda(queue):
    queue.join(_player(1), "1v1", 150, 1500)
    entry = queue.leave(1)
    assert entry.user_ids == (1,) and 1 not in queue
    assert queue.leave(1) is None
    queue.requeue(entry)
    assert 1 in queue


# --- Con il server vero --------------------------------------------------------


def _join(client, target_score=150, mode="1v1", request_id=None):
    return client.call("queue:join", {"request_id": request_id or uuid.uuid4().hex,
                                      "mode": mode, "target_score": target_score}, timeout=WAIT)


def _wait_until(condition, what, timeout=WAIT):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return
        time.sleep(0.02)
    pytest.fail(f"non è successo: {what}")


def _tabs(user_id):
    """Quante schede di quell'utente il server vede collegate."""
    return sum(1 for _ in socketio.server.manager.get_participants("/", user_channel(user_id)))


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


@pytest.fixture
def ids(server):
    return server["user_ids"]


@pytest.fixture(autouse=True)
def clean_queue(server):
    """Coda vuota prima e dopo ogni prova; le partite create dalla coda si fermano e si tolgono."""
    users = server["user_ids"].values()

    def clean():
        for user_id in users:
            matchmaker.queue.leave(user_id)
            room = find_room_of_user(user_id)
            if room is not None:
                room.run(room._stop_timers)
                rooms.remove(room.id)

    clean()
    yield
    clean()


@pytest.fixture
def rating_rows():
    """rating_rows({user_id: valore}) scrive il rating 1v1 di quegli utenti; alla fine li toglie."""
    engine = sa.create_engine(load_config("testing").SQLALCHEMY_DATABASE_URI)
    written = []

    def _write(values):
        with engine.begin() as conn:
            for user_id, value in values.items():
                conn.execute(sa.text(
                    "INSERT INTO rating (utente_id, modalita, valore, deviazione, volatilita, aggiornato_il) "
                    "VALUES (:u, '1v1', :v, 350, 0.06, :t)"
                ), {"u": user_id, "v": value, "t": datetime.now(UTC).replace(tzinfo=None)})
                written.append(user_id)

    yield _write
    with engine.begin() as conn:
        for user_id in written:
            conn.execute(sa.text("DELETE FROM rating WHERE utente_id = :u AND modalita = '1v1'"), {"u": user_id})
    engine.dispose()


def test_due_giocatori_vicini_si_abbinano_subito(connect, ids):
    primo, secondo = connect("Primo"), connect("Secondo")
    starts = [Events(primo, "game:start"), Events(secondo, "game:start")]

    answer = _join(primo, 300)
    assert answer == ok({"mode": "1v1", "target_score": 300, "seconds_waiting": 0,
                         "rating_range": {"min": 1400, "max": 1600}, "partner": None,
                         "opponents": []})
    assert _join(secondo, 300)["ok"] is True

    assert all(s.wait() for s in starts), "game:start non arrivato"
    game = starts[0].items[0]
    assert starts[1].items[0] == game and game["url"] == f"/game/{game['game_id']}"
    room = rooms.get(game["game_id"])
    assert {p.user_id for p in room.players} == {ids["Primo"], ids["Secondo"]}
    assert room.rated is True and room.game.target_score == 300
    assert room._app is not None, "partita creata fuori da Flask: a fine partita non si salverebbe (P26)"
    assert ids["Primo"] not in matchmaker.queue and ids["Secondo"] not in matchmaker.queue


def test_punteggi_diversi_code_separate(connect, ids):
    primo, secondo = connect("Primo"), connect("Secondo")
    start = Events(primo, "game:start")
    assert _join(primo, 150)["ok"] and _join(secondo, 500)["ok"]
    matchmaker.check()
    assert not start.items
    assert ids["Primo"] in matchmaker.queue and ids["Secondo"] in matchmaker.queue


def test_rating_lontani_abbinati_dopo_l_allargamento(connect, ids, rating_rows, monkeypatch):
    monkeypatch.setattr(matchmaking, "RANGE_STEP_SECONDS", 1.0)  # ±200 dopo 2 secondi invece di 20
    rating_rows({ids["Secondo"]: 1700.0})
    primo, secondo = connect("Primo"), connect("Secondo")
    statuses, start = Events(primo, "queue:status"), Events(primo, "game:start")

    assert _join(primo)["data"]["rating_range"] == {"min": 1400, "max": 1600}
    assert _join(secondo)["data"]["rating_range"] == {"min": 1600, "max": 1800}
    matchmaker.check()
    assert not start.items, "abbinati subito con 200 punti di differenza"

    assert start.wait(timeout=WAIT), "non abbinati dopo l'allargamento"
    assert statuses.items[0]["rating_range"] == {"min": 1350, "max": 1650}  # queue:status dopo 1 secondo


def test_annulla_da_un_altra_scheda(connect, ids):
    scheda_a, scheda_b = connect("Primo"), connect("Primo")
    status_b = Events(scheda_b, "queue:status")
    left_a, left_b = Events(scheda_a, "queue:left"), Events(scheda_b, "queue:left")

    assert _join(scheda_a)["ok"]
    assert status_b.wait(), "l'altra scheda non ha ricevuto queue:status"
    assert scheda_b.call("queue:leave", {}, timeout=WAIT) == ok()
    assert left_a.wait() and left_b.wait()
    assert left_a.items[0] == {"reason": "cancelled"}
    assert ids["Primo"] not in matchmaker.queue
    assert scheda_a.call("queue:leave", {}, timeout=WAIT) == ok()  # non era più in coda: ok lo stesso


def test_doppio_clic_e_seconda_scheda(connect, ids):
    scheda_a, scheda_b = connect("Primo"), connect("Primo")
    request_id = uuid.uuid4().hex
    first = _join(scheda_a, request_id=request_id)
    assert _join(scheda_a, request_id=request_id) == first  # stesso tentativo: stessa risposta
    other = _join(scheda_b)
    assert other["ok"] is False and other["error"]["code"] == "busy"
    assert len(matchmaker.queue) == 1


def test_chi_e_gia_in_partita_non_entra_in_coda(connect, ids):
    room = create_room([Player(ids["Primo"], "Primo"), Player(ids["Secondo"], "Secondo")], "1v1", 150)
    try:
        answer = _join(connect("Primo"))
        assert answer["ok"] is False and answer["error"]["code"] == "busy"
        assert ids["Primo"] not in matchmaker.queue
    finally:
        room.run(room._stop_timers)
        rooms.remove(room.id)


@pytest.mark.parametrize("data, code", [
    (None, "invalid_data"),
    ([], "invalid_data"),
    ({"mode": "1v1", "target_score": 150}, "invalid_data"),
    ({"request_id": "", "mode": "1v1", "target_score": 150}, "invalid_data"),
    ({"request_id": "x" * 101, "mode": "1v1", "target_score": 150}, "invalid_data"),
    ({"request_id": "r", "mode": "3v3", "target_score": 150}, "invalid_data"),
    ({"request_id": "r", "mode": "1v1", "target_score": 200}, "invalid_data"),
    ({"request_id": "r", "mode": "1v1", "target_score": "150"}, "invalid_data"),
    ({"request_id": "r", "mode": "1v1", "target_score": True}, "invalid_data"),
])
def test_dati_non_validi(connect, ids, data, code):
    answer = connect("Primo").call("queue:join", data, timeout=WAIT)
    assert answer["ok"] is False and answer["error"]["code"] == code
    assert ids["Primo"] not in matchmaker.queue


def test_chi_chiude_tutte_le_schede_esce_dalla_coda(connect, ids):
    scheda_a, scheda_b = connect("Primo"), connect("Primo")
    assert _join(scheda_a)["ok"]
    scheda_a.disconnect()
    _wait_until(lambda: _tabs(ids["Primo"]) == 1, "scollegamento della prima scheda visto dal server")
    assert ids["Primo"] in matchmaker.queue
    scheda_b.disconnect()
    _wait_until(lambda: ids["Primo"] not in matchmaker.queue, "uscita dalla coda dopo l'ultima scheda")


def test_una_scheda_nuova_riceve_lo_stato_della_coda(connect, ids):
    assert _join(connect("Primo"), 500)["ok"]
    received = {}
    connect("Primo", before=lambda client: received.update(status=Events(client, "queue:status")))
    assert received["status"].wait(), "queue:status non arrivato alla scheda nuova"
    assert received["status"].items[0]["target_score"] == 500
