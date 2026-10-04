"""P68: partita 1v1 contro la CPU con il server vero (D43).

Il giocatore vero è un client Socket.IO simulato (conftest.py); la CPU gioca nella
stanza da sola. Le attese della CPU si riducono a pochi millesimi cambiando le
costanti di app/realtime/room.py. Si aspettano gli eventi (le viste), non tempi fissi.
"""

import random
import threading
import uuid
from dataclasses import replace

import pytest
import sqlalchemy as sa

from app.game.engine import cpu as cpu_module
from app.realtime import room as room_module
from app.realtime.events import ok
from app.realtime.matchmaking import matchmaker
from app.realtime.room import CPU_PLAYER, Player
from app.realtime.room_manager import create_room, find_room_of_user, rooms
from config import load_config

WAIT = 5


@pytest.fixture(autouse=True)
def fast_cpu(monkeypatch):
    monkeypatch.setattr(room_module, "CPU_SECONDS", 0.01)  # le pause del tavolo le toglie conftest.py (P94)
    # D43: la CPU pensa meno (qui conta la stanza, la forza la prova tests/engine/test_cpu.py)
    monkeypatch.setattr(cpu_module, "SIMULATED_PLAYS", 600)
    monkeypatch.setattr(cpu_module, "MIN_WORLDS", 4)


@pytest.fixture(autouse=True)
def clean(server):
    """Né coda né partite degli utenti di prova, prima e dopo ogni prova."""
    def _clean():
        for user_id in server["user_ids"].values():
            matchmaker.queue.leave(user_id)
            for room in rooms.rooms_of(user_id):
                room.run(room._stop_timers)
                rooms.remove(room.id)

    _clean()
    yield
    _clean()


@pytest.fixture
def saved_matches():
    """saved_matches() → quante partite ci sono nel database."""
    engine = sa.create_engine(load_config("testing").SQLALCHEMY_DATABASE_URI)

    def _count():
        with engine.connect() as conn:
            return conn.execute(sa.text("SELECT COUNT(*) FROM partite")).scalar()

    yield _count
    engine.dispose()


class Table:
    """Il giocatore vero al tavolo: tiene le viste e gli eventi game:sang."""

    def __init__(self, client):
        self.client = client
        self.views = []
        self.sang = []
        self._cond = threading.Condition()
        client.on("game:state", self._on_state)
        client.on("game:sang", self._on_sang)

    def _on_state(self, view):
        with self._cond:
            self.views.append(view)
            self._cond.notify_all()

    def _on_sang(self, data):
        with self._cond:
            self.sang.append(data)

    @property
    def last(self):
        with self._cond:
            return max(self.views, key=lambda v: v["version"]) if self.views else None

    def wait_latest(self, check, timeout=WAIT):
        """Aspetta che la vista più recente soddisfi `check` e la restituisce."""
        with self._cond:
            ok_ = self._cond.wait_for(lambda: self.views and check(max(self.views, key=lambda v: v["version"])),
                                      timeout)
            assert ok_, "la vista attesa non è arrivata"
            return max(self.views, key=lambda v: v["version"])

    def call(self, event, data):
        return self.client.call(event, data, timeout=WAIT)


def start_cpu(client, target_score=150, request_id=None):
    return client.call("cpu:start", {"request_id": request_id or uuid.uuid4().hex,
                                     "target_score": target_score}, timeout=WAIT)


def my_turn_or_end(acted):
    def check(view):
        if view["version"] <= acted:
            return False
        return view["status"] == "finished" or (view["turn"]["seat"] == 0 and bool(view["legal"]["play"]))
    return check


def play_as_human(table, game_id):
    """Il giocatore vero canta se può, altrimenti gioca la prima carta ammessa, fino alla fine."""
    acted = 0
    for _ in range(1000):
        view = table.wait_latest(my_turn_or_end(acted))
        if view["status"] == "finished":
            return view
        if view["legal"]["sing"]:
            answer = table.call("game:sing", {"game_id": game_id, "version": view["version"],
                                              "suit": view["legal"]["sing"][0]})
        else:
            answer = table.call("game:play_card", {"game_id": game_id, "version": view["version"],
                                                   "card": view["legal"]["play"][0]})
        assert answer == ok(), answer
        acted = view["version"]
    raise AssertionError("la partita non finisce")


def sit(connect, game_id, name="Primo"):
    table = Table(connect(name))
    assert table.call("game:join", {"game_id": game_id}) == ok()
    table.wait_latest(lambda v: True)
    return table


# --- Avvio --------------------------------------------------------------------------


def test_cpu_start_crea_la_partita(connect, server, inbox):
    client = connect("Primo")
    starts = inbox(client, "game:start")
    answer = start_cpu(client, 300)
    assert answer["ok"] is True, answer
    game_id = answer["data"]["game_id"]
    assert starts.wait() and starts.items[0] == {"game_id": game_id, "url": f"/game/{game_id}"}
    room = rooms.get(game_id)
    assert room.cpu_seats == {1} and room.rated is False
    assert room.members == {server["user_ids"]["Primo"]}  # la CPU non è un membro
    table = Table(client)
    assert table.call("game:join", {"game_id": game_id}) == ok()
    view = table.wait_latest(lambda v: True)
    assert view["mode"] == "1v1" and view["target_score"] == 300 and view["rated"] is False
    assert view["you"] == {"seat": 0}
    cpu = view["players"][1]
    assert (cpu["user_id"], cpu["username"], cpu["avatar"], cpu["connected"]) == (0, "CPU", None, True)
    assert cpu["cpu"] is True and view["players"][0]["cpu"] is False  # D43: la pagina la riconosce da qui


def test_stesso_request_id_una_partita_sola(connect, server):
    client = connect("Primo")
    request_id = uuid.uuid4().hex
    first = start_cpu(client, request_id=request_id)
    again = start_cpu(client, request_id=request_id)
    assert first["ok"] is True and again == first
    assert len(rooms.rooms_of(server["user_ids"]["Primo"])) == 1


@pytest.mark.parametrize("data", [
    None, {}, {"target_score": 150}, {"request_id": "", "target_score": 150},
    {"request_id": "a", "target_score": 100}, {"request_id": "a", "target_score": "150"},
    {"request_id": "a", "target_score": True},
])
def test_dati_non_validi(connect, data):
    answer = connect("Primo").call("cpu:start", data, timeout=WAIT)
    assert answer["ok"] is False and answer["error"]["code"] == "invalid_data"


def test_busy_se_gia_in_partita(connect):
    client = connect("Primo")
    assert start_cpu(client)["ok"] is True
    answer = start_cpu(client)
    assert answer["ok"] is False and answer["error"]["code"] == "busy"


def test_busy_se_in_coda(connect):
    client = connect("Primo")
    joined = client.call("queue:join", {"request_id": uuid.uuid4().hex, "mode": "1v1", "target_score": 150},
                         timeout=WAIT)
    assert joined["ok"] is True
    answer = start_cpu(client)
    assert answer["ok"] is False and answer["error"]["code"] == "busy"


def test_due_giocatori_contro_la_cpu_insieme(connect, server):
    """La CPU può essere in più partite: non risulta mai "già in partita"."""
    assert start_cpu(connect("Primo"))["ok"] is True
    assert start_cpu(connect("Secondo"))["ok"] is True
    assert find_room_of_user(0) is None


# --- Partita ------------------------------------------------------------------------


def test_partita_intera_contro_la_cpu_non_si_salva(connect, saved_matches):
    before = saved_matches()
    client = connect("Primo")
    answer = start_cpu(client)
    game_id = answer["data"]["game_id"]
    table = Table(client)
    assert table.call("game:join", {"game_id": game_id}) == ok()
    final = play_as_human(table, game_id)
    assert final["result"]["reason"] == "score"
    assert final["turn"] is None
    room = rooms.get(game_id)
    # La CPU ha giocato davvero: metà delle carte delle prese sono sue
    assert any(move.seat == 1 and move.kind == "gioca_carta" for move in room._moves)
    assert saved_matches() == before  # D43: la partita contro la CPU non si salva


def test_la_cpu_canta_e_lo_dice_a_tutti(connect, users_for_cpu):
    """Con un mazzo fisso (rng) la partita è sempre la stessa: se ne cerca una in cui la CPU canta."""
    for seed in range(20):
        room = create_room([users_for_cpu["Primo"], CPU_PLAYER], "1v1", 150, rated=False,
                           rng=random.Random(seed), cpu_seats=(1,), announce=False)
        table = sit(connect, room.id)
        play_as_human(table, room.id)
        cpu_sings = [move for move in room._moves if move.seat == 1 and move.kind == "canta"]
        table.client.disconnect()
        rooms.remove(room.id)
        if cpu_sings:
            sang = [event for event in table.sang if event["seat"] == 1]
            assert len(sang) == len(cpu_sings)
            assert all(event["points"] in (40, 20) and len(event["cards"]) == 2 for event in sang)
            return
    pytest.fail("in 20 partite la CPU non ha mai cantato")


@pytest.fixture
def users_for_cpu(server):
    return {name: Player(user_id=user_id, username=name) for name, user_id in server["user_ids"].items()}


def test_con_la_mossa_automatica_la_cpu_continua(connect, users_for_cpu, monkeypatch):
    """Il giocatore vero non gioca mai: la sua mossa automatica e la CPU si alternano."""
    monkeypatch.setattr(room_module, "TURN_SECONDS", 0.2)
    room = create_room([users_for_cpu["Primo"], CPU_PLAYER], "1v1", 150, rated=False,
                       rng=random.Random(1), cpu_seats=(1,), announce=False)
    table = sit(connect, room.id)
    table.wait_latest(lambda v: sum(p["cards_in_hand"] for p in v["players"]) < 10 and v["last_trick"] is not None
                      and len([m for m in room._moves if m.kind == "mossa_automatica"]) >= 3)
    kinds = {(move.seat, move.kind) for move in room._moves}
    assert (0, "mossa_automatica") in kinds and (1, "gioca_carta") in kinds


def test_abbandono_contro_la_cpu(connect, saved_matches):
    before = saved_matches()
    client = connect("Primo")
    game_id = start_cpu(client)["data"]["game_id"]
    table = Table(client)
    assert table.call("game:join", {"game_id": game_id}) == ok()
    table.wait_latest(lambda v: True)
    assert table.call("game:leave", {"game_id": game_id}) == ok()
    view = table.wait_latest(lambda v: v["status"] == "finished")
    assert view["result"]["reason"] == "abandon" and view["result"]["winner_team"] == 1
    room = rooms.get(game_id)
    assert room._cpu_timer is None and room._turn_timer is None  # la CPU non gioca più
    assert saved_matches() == before


def test_se_la_vista_cambia_mentre_pensa_la_cpu_ci_ripensa(connect, users_for_cpu, monkeypatch):
    """La CPU pensa fuori dal lock: se intanto la vista cambia (qui il giocatore rientra da
    un'altra scheda) la mossa pensata non vale, ma la CPU non resta ferma: ci ripensa."""
    thinking = threading.Event()
    go_on = threading.Event()
    calls = []
    real_move = room_module.cpu_move

    def slow_move(view, rng, memory):
        calls.append(view["version"])
        if len(calls) == 1:
            thinking.set()
            go_on.wait(WAIT)
        return real_move(view, rng, memory)

    monkeypatch.setattr(room_module, "CPU_SECONDS", 5)  # ferma finché la mano non è pronta
    room = create_room([users_for_cpu["Primo"], CPU_PLAYER], "1v1", 150, rated=False,
                       rng=random.Random(2), cpu_seats=(1,), announce=False)
    monkeypatch.setattr(room_module, "cpu_move", slow_move)
    monkeypatch.setattr(room_module, "CPU_SECONDS", 0.01)
    with room.lock:
        # Apre la CPU: la sua prima mossa parte subito, prima che il giocatore si sieda
        room.game = replace(room.game, first_seat=1, hand=replace(room.game.hand, leader_seat=1, turn_seat=1))
        room._start_turn()
    assert thinking.wait(WAIT)
    first = sit(connect, room.id)  # il giocatore si siede: la vista cambia mentre la CPU pensa
    version = room.version
    go_on.set()
    view = first.wait_latest(lambda v: v["version"] > version and len(v["trick"]["cards"]) == 1)
    assert view["trick"]["cards"][0]["seat"] == 1  # la CPU ha giocato, dopo averci ripensato
    assert len(calls) >= 2 and calls[1] > calls[0]
