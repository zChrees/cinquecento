"""P84: "Cala le carte" con il server vero (D45, contratto 3.2 e 3.3).

I giocatori sono client Socket.IO simulati (conftest.py). La mano si prepara a mazzo
finito sostituendo la mano della partita nella stanza, sotto il suo lock, prima che i
giocatori si siedano. Si aspettano le viste, non tempi fissi.
"""

import json
import threading
from dataclasses import replace

import pytest
import sqlalchemy as sa

from app.game.engine.cards import Card, Suit
from app.game.engine.deck import full_deck
from app.game.engine.singing import Sing
from app.game.engine.state import HandState, LastTrick, TrickPlay
from app.realtime import room as room_module
from app.realtime.events import ok
from app.realtime.room import CPU_PLAYER, Player
from app.realtime.room_manager import create_room, rooms
from config import load_config

WAIT = 5
# 1v1, briscola bastoni (l'ha cantata il posto 1): Asso di coppe e Tre di bastoni contro
# 2 di coppe e 4 di spade, di turno il posto 0 a inizio presa: si cala (esempio di D45)
WINNING = (("coppe-1", "bastoni-3"), ("coppe-2", "spade-4"))


def end_hand(hands, leader=0, trump_by=1):
    hands = tuple(tuple(Card.from_code(code) for code in hand) for hand in hands)
    rest = [c for c in full_deck() if not any(c in hand for hand in hands)]
    return HandState(
        num_players=len(hands), hands=hands, deck=(), trick=(), leader_seat=leader, turn_seat=leader,
        sings=(Sing(trump_by, Suit.BASTONI, 40),),
        captured=(tuple(rest[: len(rest) // 2]), tuple(rest[len(rest) // 2:])),
        last_trick=LastTrick(leader, (TrickPlay(leader, rest[0]), TrickPlay((leader + 1) % len(hands), rest[1]))),
    )


@pytest.fixture(autouse=True)
def clean(server):
    def _clean():
        for user_id in server["user_ids"].values():
            for room in rooms.rooms_of(user_id):
                room.run(room._stop_timers)
                rooms.remove(room.id)

    _clean()
    yield
    _clean()


@pytest.fixture
def players(server):
    ids = server["user_ids"]
    return [Player(user_id=ids["Primo"], username="Primo"), Player(user_id=ids["Secondo"], username="Secondo")]


class Seat:
    def __init__(self, client):
        self.client = client
        self.state = None
        self._cond = threading.Condition()
        client.on("game:state", self._on_state)

    def _on_state(self, view):
        with self._cond:
            if self.state is None or view["version"] >= self.state["version"]:
                self.state = view
            self._cond.notify_all()

    def wait_version(self, version):
        return self.wait_for(lambda view: view["version"] >= version, f"version {version}")

    def wait_for(self, check, what):
        with self._cond:
            arrived = self._cond.wait_for(lambda: self.state is not None and check(self.state), WAIT)
        assert arrived, f"nessuna vista con {what}"
        return self.state

    def call(self, event, data):
        return self.client.call(event, data, timeout=WAIT)


def prepared_room(players, scores=(0, 0), hand=None, cpu_seats=(), app=None):
    """Con `app` la stanza nasce dentro Flask e a fine partita salva (punto delicato di P26)."""
    if app is not None:
        with app.app_context():
            return prepared_room(players, scores, hand, cpu_seats)
    room = create_room(players, "1v1", 150, rated=False, cpu_seats=cpu_seats)
    with room.lock:
        room.game = replace(room.game, hand=hand or end_hand(WINNING), first_seat=0, scores=scores)
    return room


def sit(connect, room, names):
    seats = [Seat(connect(name)) for name in names]
    for seat in seats:
        assert seat.call("game:join", {"game_id": room.id}) == ok()
    for seat in seats:
        seat.wait_version(room.version)
    return seats


def test_si_cala_e_tutti_vedono_le_carte(connect, players):
    room = prepared_room(players)
    seats = sit(connect, room, ["Primo", "Secondo"])
    version = room.version
    before = seats[0].wait_version(version)
    assert before["legal"]["lay_down"] is True
    assert seats[1].wait_version(version)["legal"]["lay_down"] is False
    # Prima della calata nessuno vede le carte dell'altro
    assert json.dumps({"suit": "coppe", "rank": 2}) not in json.dumps(before)

    answer = seats[0].call("game:lay_down", {"game_id": room.id, "version": version})
    assert answer == ok(), answer
    for seat in seats:
        view = seat.wait_version(version + 1)
        assert view["hand_number"] == 2
        laid = view["last_hand"]["laid_down"]
        assert laid["seat"] == 0 and laid["sings"] == []
        assert laid["hands"] == [
            {"seat": 0, "cards": [{"suit": "coppe", "rank": 1}, {"suit": "bastoni", "rank": 3}]},
            {"seat": 1, "cards": [{"suit": "coppe", "rank": 2}, {"suit": "spade", "rank": 4}]},
        ]
        assert view["last_hand"]["last_trick"] is not None  # l'ultima presa chiusa resta com'era
    kinds = [move.kind for move in room._moves]
    assert kinds == ["cala_carte"]
    assert room._moves[0].details["mani"][1] == {
        "posto": 1, "carte": [{"seme": "coppe", "valore": 2}, {"seme": "spade", "valore": 4}],
    }


def test_doppio_clic_una_calata_sola(connect, players):
    room = prepared_room(players)
    seats = sit(connect, room, ["Primo", "Secondo"])
    version = room.version
    data = {"game_id": room.id, "version": version}
    assert seats[0].call("game:lay_down", data) == ok()
    second = seats[0].call("game:lay_down", data)
    assert second["ok"] is False and second["error"]["code"] == "stale_state"
    assert [move.kind for move in room._moves] == ["cala_carte"]


def test_calata_non_ammessa_rifiutata(connect, players):
    # Con il 4 di bastoni (briscola) l'avversario prende l'Asso di coppe: non si cala
    room = prepared_room(players, hand=end_hand((("coppe-1", "bastoni-3"), ("coppe-2", "bastoni-4"))))
    seats = sit(connect, room, ["Primo", "Secondo"])
    version = room.version
    assert seats[0].wait_version(version)["legal"]["lay_down"] is False
    answer = seats[0].call("game:lay_down", {"game_id": room.id, "version": version})
    assert answer["ok"] is False and answer["error"]["code"] == "illegal_move"
    assert answer["error"]["message"] == "Adesso non puoi calare le carte."
    fuori_turno = seats[1].call("game:lay_down", {"game_id": room.id, "version": version})
    assert fuori_turno["ok"] is False and fuori_turno["error"]["code"] == "not_your_turn"
    assert room.version == version and room._moves == []


@pytest.mark.parametrize("change", [
    {"version": None},  # manca la version
    {"version": "1"},
    {"version": True},
    {"game_id": 3},
])
def test_dati_non_validi(connect, players, change):
    room = prepared_room(players)
    seats = sit(connect, room, ["Primo", "Secondo"])
    payload = {key: value for key, value in {"game_id": room.id, "version": room.version, **change}.items()
               if value is not None}
    answer = seats[0].call("game:lay_down", payload)
    assert answer["ok"] is False and answer["error"]["code"] == "invalid_data"
    assert room._moves == []


def test_la_calata_chiude_la_partita_e_si_salva(connect, players, server):
    engine = sa.create_engine(load_config("testing").SQLALCHEMY_DATABASE_URI)
    try:
        room = prepared_room(players, scores=(140, 0), app=server["app"])
        seats = sit(connect, room, ["Primo", "Secondo"])
        version = room.version
        assert seats[0].call("game:lay_down", {"game_id": room.id, "version": version}) == ok()
        view = seats[1].wait_version(version + 1)
        assert view["status"] == "finished" and view["result"]["winner_team"] == 0
        assert view["last_hand"]["laid_down"]["seat"] == 0
        with engine.connect() as conn:
            row = conn.execute(sa.text(
                "SELECT m.tipo, m.dettagli FROM mosse_partita m JOIN partite p ON p.id = m.partita_id "
                "ORDER BY p.id DESC, m.numero DESC LIMIT 1")).one()
        assert row.tipo == "cala_carte"
        assert json.loads(row.dettagli)["mani"][0]["carte"] == [{"seme": "coppe", "valore": 1},
                                                                {"seme": "bastoni", "valore": 3}]
    finally:
        engine.dispose()


def test_la_cpu_cala_quando_puo(connect, players, monkeypatch):
    # La CPU al posto 0 con le carte che vincono tutto. Le sue attese si accorciano solo dopo
    # aver preparato la mano, così non gioca prima sulla mano di partenza
    room = prepared_room([CPU_PLAYER, players[1]], cpu_seats=(0,))
    seats = sit(connect, room, ["Secondo"])
    for name in ("CPU_SECONDS", "CPU_AFTER_TRICK_SECONDS", "CPU_NEW_HAND_SECONDS"):
        monkeypatch.setattr(room_module, name, 0.01)
    with room.lock:
        room._start_turn()  # nuovo turno: il timer di prima della CPU non vale più
    view = seats[0].wait_for(lambda view: view["hand_number"] == 2, "la mano 2")
    assert view["last_hand"]["laid_down"]["seat"] == 0
    assert room._moves[0].kind == "cala_carte" and room._moves[0].seat == 0
