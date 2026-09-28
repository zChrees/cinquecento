"""P24: si gioca davvero, con client simulati contro il server vero.

- Una partita 1v1 e una 2v2 fino a 150, con la stanza creata da create_room;
  ogni giocatore riceve solo la propria vista, con i campi del contratto (3.3).
- Una mossa illegale, fuori turno, su una vista vecchia o con dati non validi
  riceve un errore e non cambia niente.
- D14: l'ultima scheda prende il posto, la precedente riceve game:replaced.
- create_room e find_room_of_user hanno i loro test.
"""

import json
import random
import re
import threading
from pathlib import Path

import pytest
import requests
import sqlalchemy as sa

from app.realtime.events import ok
from app.realtime.room import Player
from app.realtime.room_manager import RoomError, create_room, find_room_of_user, rooms
from config import load_config

BASE_DIR = Path(__file__).resolve().parents[2]
WAIT = 5
PASSWORD = "Password-di-prova-1"  # la stessa degli utenti di conftest.py
EXAMPLE = json.loads((BASE_DIR / "app" / "static" / "dev" / "vista_1v1.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def users(server):
    """Gli utenti di conftest.py più "Quarto", registrato come farebbe il browser (serve al 2v2)."""
    session = requests.Session()
    page = session.get(f"{server['url']}/auth/register", timeout=WAIT).text
    token = re.search(r'name="csrf_token" type="hidden" value="([^"]+)"', page)[1]
    response = session.post(f"{server['url']}/auth/register", data={
        "csrf_token": token, "username": "Quarto", "email": "quarto@esempio.it",
        "password": PASSWORD, "confirm": PASSWORD,
    }, allow_redirects=False, timeout=WAIT)
    assert response.status_code == 302
    # Niente create_app qui: una seconda app nello stesso processo ricollegherebbe socketio altrove.
    engine = sa.create_engine(load_config("testing").SQLALCHEMY_DATABASE_URI)
    try:
        with engine.connect() as conn:
            quarto = conn.execute(sa.text("SELECT id FROM utenti WHERE nome_utente = 'Quarto'")).scalar()
    finally:
        engine.dispose()
    return {**server["user_ids"], "Quarto": quarto}


def player(users, name):
    return Player(user_id=users[name], username=name)


@pytest.fixture
def new_room(users):
    """new_room(["Primo", "Secondo"], "1v1", ...) → stanza creata con create_room, tolta alla fine."""
    created = []

    def _new_room(names, mode, target_score=150, **options):
        room = create_room([player(users, n) for n in names], mode, target_score, **options)
        created.append(room)
        return room

    yield _new_room
    for room in created:
        rooms.remove(room.id)


class Seat:
    """Un giocatore al tavolo: tiene l'ultima vista ricevuta e aspetta quella con una certa version."""

    def __init__(self, client):
        self.client = client
        self.state = None
        self.replaced = []
        self.sang = []
        self._cond = threading.Condition()
        client.on("game:state", self._on_state)
        client.on("game:replaced", self.replaced.append)
        client.on("game:sang", self.sang.append)

    def _on_state(self, view):
        with self._cond:
            if self.state is None or view["version"] >= self.state["version"]:
                self.state = view
            self._cond.notify_all()

    def wait_version(self, version):
        with self._cond:
            arrived = self._cond.wait_for(lambda: self.state is not None and self.state["version"] >= version, WAIT)
        assert arrived, f"nessuna vista con version {version}"
        return self.state

    def call(self, event, data):
        return self.client.call(event, data, timeout=WAIT)


def sit(connect, room, names):
    """Collega i giocatori e fa game:join per tutti; restituisce i posti e la version attuale."""
    seats = [Seat(connect(name)) for name in names]
    for seat in seats:
        assert seat.call("game:join", {"game_id": room.id}) == ok()
    for seat in seats:
        seat.wait_version(room.version)
    return seats, room.version


def play_to_the_end(room, seats, version):
    """Gioca fino alla fine: chi è di turno canta se può, altrimenti gioca la prima carta ammessa."""
    for _ in range(2000):
        views = [seat.wait_version(version) for seat in seats]
        _check_private(views)
        if views[0]["status"] == "finished":
            return views
        turn = views[0]["turn"]["seat"]
        view = views[turn]
        assert all(v["legal"] == {"play": [], "sing": []} for i, v in enumerate(views) if i != turn)
        if view["legal"]["sing"]:
            answer = seats[turn].call("game:sing", {"game_id": room.id, "version": version,
                                                   "suit": view["legal"]["sing"][0]})
        else:
            answer = seats[turn].call("game:play_card", {"game_id": room.id, "version": version,
                                                        "card": view["legal"]["play"][0]})
        assert answer == ok(), answer
        version += 1
    raise AssertionError("la partita non finisce")


def _check_private(views):
    """Ogni vista ha solo le carte del suo posto: le mani non si sovrappongono e combaciano con cards_in_hand."""
    seen = set()
    for view in views:
        hand = {(c["suit"], c["rank"]) for c in view["hand"]}
        assert not hand & seen
        seen |= hand
        me = view["you"]["seat"]
        assert view["players"][me]["cards_in_hand"] == len(view["hand"])


def _check_finished(views, room):
    for view in views:
        assert view["status"] == "finished"
        assert view["turn"] is None
        result = view["result"]
        totals = [s["total"] for s in result["scores"]]
        assert max(totals) >= 150
        if totals[0] == totals[1]:
            assert result["winner_team"] is None
        else:
            assert result["winner_team"] == totals.index(max(totals))
    assert room.finished


# --- Partite intere ---


def test_partita_1v1_fino_a_150(connect, new_room, users):
    room = new_room(["Primo", "Secondo"], "1v1", rated=False, rng=random.Random(1))
    seats, version = sit(connect, room, ["Primo", "Secondo"])
    views = play_to_the_end(room, seats, version)
    _check_finished(views, room)
    assert all(v["rated"] is False and v["mode"] == "1v1" for v in views)
    assert [p["username"] for p in views[0]["players"]] == ["Primo", "Secondo"]
    # Ogni canto l'hanno visto tutti e due (D15)
    assert seats[0].sang == seats[1].sang
    # A partita finita non si gioca più e l'utente non risulta più in partita
    answer = seats[0].call("game:play_card", {"game_id": room.id, "version": room.version,
                                              "card": {"suit": "denari", "rank": 1}})
    assert answer["ok"] is False
    assert find_room_of_user(users["Primo"]) is None


def test_partita_2v2_fino_a_150(connect, new_room):
    names = ["Primo", "Secondo", "Terzo", "Quarto"]
    room = new_room(names, "2v2", rng=random.Random(2))
    seats, version = sit(connect, room, names)
    views = play_to_the_end(room, seats, version)
    _check_finished(views, room)
    assert [(p["seat"], p["team"]) for p in views[0]["players"]] == [(0, 0), (1, 1), (2, 0), (3, 1)]
    assert all(v["rated"] is True and v["mode"] == "2v2" for v in views)


def test_canto_mostrato_a_tutti(connect, new_room):
    # Si cerca una partita in cui chi comincia può cantare subito
    for seed in range(200):
        room = new_room(["Primo", "Secondo"], "1v1", rng=random.Random(seed))
        if room.view_for(room.game.hand.turn_seat)["legal"]["sing"]:
            break
        rooms.remove(room.id)
    seats, version = sit(connect, room, ["Primo", "Secondo"])
    turn = room.game.hand.turn_seat
    suit = seats[turn].state["legal"]["sing"][0]
    assert seats[turn].call("game:sing", {"game_id": room.id, "version": version, "suit": suit}) == ok()
    for seat in seats:
        view = seat.wait_version(version + 1)
        assert view["sings"] == [{"seat": turn, "suit": suit, "points": 40}]
        assert view["trump"] == suit
        assert view["turn"]["seat"] == turn  # dopo il canto si gioca ancora la carta
    expected = {"seat": turn, "suit": suit, "points": 40, "show_seconds": 3,
                "cards": [{"suit": suit, "rank": 10}, {"suit": suit, "rank": 9}]}
    assert seats[0].sang == seats[1].sang == [expected]


# --- Vista ---


def test_vista_con_i_campi_del_contratto(connect, new_room):
    room = new_room(["Primo", "Secondo"], "1v1", target_score=500)
    seats, _ = sit(connect, room, ["Primo", "Secondo"])
    view = seats[0].state
    expected = {k for k in EXAMPLE if not k.startswith("_")}
    assert set(view) == expected
    assert set(view["players"][0]) == set(EXAMPLE["players"][0])
    assert set(view["turn"]) == set(EXAMPLE["turn"])
    assert view["game_id"] == room.id
    assert view["turn"]["seconds_total"] == 30
    assert 0 < view["turn"]["seconds_left"] <= 30
    assert all(p["connected"] and p["reconnect_seconds_left"] is None for p in view["players"])


# --- Mosse rifiutate: errore e niente cambia ---


def _my_turn(seats, room):
    turn = room.game.hand.turn_seat
    return seats[turn], seats[1 - turn], seats[turn].state


def test_mossa_illegale_rifiutata_e_niente_cambia(connect, new_room):
    room = new_room(["Primo", "Secondo"], "1v1")
    seats, version = sit(connect, room, ["Primo", "Secondo"])
    me, _, view = _my_turn(seats, room)
    mine = {(c["suit"], c["rank"]) for c in view["hand"]}
    suit, rank = next((s, r) for s in ("denari", "coppe", "spade", "bastoni") for r in range(1, 11)
                      if (s, r) not in mine)
    before = room.game
    answer = me.call("game:play_card", {"game_id": room.id, "version": version, "card": {"suit": suit, "rank": rank}})
    assert answer["ok"] is False and answer["error"]["code"] == "illegal_move"
    assert room.game is before and room.version == version


def test_mossa_fuori_turno_rifiutata(connect, new_room):
    room = new_room(["Primo", "Secondo"], "1v1")
    seats, version = sit(connect, room, ["Primo", "Secondo"])
    _, other, _ = _my_turn(seats, room)
    card = other.state["hand"][0]
    before = room.game
    answer = other.call("game:play_card", {"game_id": room.id, "version": version, "card": card})
    assert answer["error"]["code"] == "not_your_turn"
    assert room.game is before and room.version == version


def test_vista_vecchia_stale_state_e_vista_attuale(connect, new_room):
    room = new_room(["Primo", "Secondo"], "1v1")
    seats, version = sit(connect, room, ["Primo", "Secondo"])
    me, _, view = _my_turn(seats, room)
    assert me.call("game:play_card", {"game_id": room.id, "version": version, "card": view["legal"]["play"][0]}) == ok()
    # Doppio clic: la stessa mossa con la version vecchia
    answer = me.call("game:play_card", {"game_id": room.id, "version": version, "card": view["legal"]["play"][1]})
    assert answer["error"]["code"] == "stale_state"
    assert room.version == version + 1
    assert me.wait_version(version + 1)["version"] == version + 1


@pytest.mark.parametrize("change", [
    {"game_id": 12}, {"game_id": ""}, {"game_id": "x" * 65},
    {"version": "3"}, {"version": True}, {"version": 0}, {"version": None},
    {"card": "denari-1"}, {"card": {"suit": "denari"}}, {"card": {"suit": "oro", "rank": 1}},
    {"card": {"suit": "denari", "rank": 11}}, {"card": {"suit": "denari", "rank": "1"}},
    {"card": {"suit": "denari", "rank": True}}, {"card": {"suit": "denari", "rank": 1, "extra": 1}},
])
def test_dati_non_validi_rifiutati(connect, new_room, change):
    room = new_room(["Primo", "Secondo"], "1v1")
    seats, version = sit(connect, room, ["Primo", "Secondo"])
    me, _, view = _my_turn(seats, room)
    data = {"game_id": room.id, "version": version, "card": view["legal"]["play"][0], **change}
    before = room.game
    answer = me.call("game:play_card", data)
    assert answer["ok"] is False and answer["error"]["code"] == "invalid_data", answer
    assert room.game is before and room.version == version


def test_richiesta_che_non_e_un_oggetto_rifiutata(connect):
    answer = connect("Primo").call("game:join", "partita", timeout=WAIT)
    assert answer["error"]["code"] == "invalid_data"


def test_seme_non_valido_rifiutato(connect, new_room):
    room = new_room(["Primo", "Secondo"], "1v1")
    seats, version = sit(connect, room, ["Primo", "Secondo"])
    me, _, _ = _my_turn(seats, room)
    answer = me.call("game:sing", {"game_id": room.id, "version": version, "suit": "Coppe"})
    assert answer["error"]["code"] == "invalid_data"


def test_chi_non_e_seduto_non_entra(connect, new_room):
    room = new_room(["Primo", "Secondo"], "1v1")
    terzo = connect("Terzo")
    answer = terzo.call("game:join", {"game_id": room.id}, timeout=WAIT)
    assert answer["error"]["code"] == "not_allowed"
    answer = terzo.call("game:join", {"game_id": "non-esiste"}, timeout=WAIT)
    assert answer["error"]["code"] == "not_found"


def test_mossa_senza_game_join_rifiutata(connect, new_room):
    room = new_room(["Primo", "Secondo"], "1v1")
    turn = room.game.hand.turn_seat
    client = connect(room.players[turn].username)
    card = room.view_for(turn)["legal"]["play"][0]
    answer = client.call("game:play_card", {"game_id": room.id, "version": room.version, "card": card}, timeout=WAIT)
    assert answer["error"]["code"] == "not_allowed"


# --- D14: l'ultima scheda prende il posto ---


def test_ultima_scheda_prende_il_posto(connect, new_room):
    room = new_room(["Primo", "Secondo"], "1v1")
    seats, _ = sit(connect, room, ["Primo", "Secondo"])
    turn = room.game.hand.turn_seat
    old = seats[turn]
    new = Seat(connect(room.players[turn].username))
    assert new.call("game:join", {"game_id": room.id}) == ok()
    view = new.wait_version(room.version)
    assert old.replaced == [{"game_id": room.id}]
    card = view["legal"]["play"][0]
    answer = old.call("game:play_card", {"game_id": room.id, "version": view["version"], "card": card})
    assert answer["error"]["code"] == "not_allowed"
    assert new.call("game:play_card", {"game_id": room.id, "version": view["version"], "card": card}) == ok()


# --- create_room e find_room_of_user ---


def test_create_room_avvisa_i_giocatori(connect, new_room, inbox, users):
    primo, secondo, terzo = connect("Primo"), connect("Secondo"), connect("Terzo")
    starts = [inbox(c, "game:start") for c in (primo, secondo, terzo)]
    pings = inbox(terzo, "test:ping")
    room = new_room(["Primo", "Secondo"], "1v1")
    assert starts[0].wait() and starts[1].wait()
    assert starts[0].items == starts[1].items == [{"game_id": room.id, "url": f"/game/{room.id}"}]
    # Terzo non gioca: un ping mandato dopo gli arriva, e game:start no
    terzo.call("test:ping_user", {"user_id": users["Terzo"]}, timeout=WAIT)
    assert pings.wait()
    assert starts[2].items == []


def test_create_room_rifiuta_dati_sbagliati(users, new_room):
    primo, secondo = player(users, "Primo"), player(users, "Secondo")
    with pytest.raises(RoomError, match="Modalità non valida"):
        create_room([primo, secondo], "3v3", 150, announce=False)
    with pytest.raises(RoomError, match="servono 4 giocatori"):
        create_room([primo, secondo], "2v2", 150, announce=False)
    with pytest.raises(RoomError, match="due posti"):
        create_room([primo, primo], "1v1", 150, announce=False)
    with pytest.raises(RoomError, match="Punteggio non valido"):
        create_room([primo, secondo], "1v1", 200, announce=False)
    assert find_room_of_user(users["Primo"]) is None


def test_find_room_of_user_e_giocatore_gia_in_partita(users, new_room):
    room = new_room(["Primo", "Secondo"], "1v1", announce=False)
    assert find_room_of_user(users["Primo"]) is room
    assert find_room_of_user(users["Secondo"]) is room
    assert find_room_of_user(users["Terzo"]) is None
    with pytest.raises(RoomError, match="Già in partita: Secondo"):
        create_room([player(users, "Terzo"), player(users, "Secondo")], "1v1", 150, announce=False)
    rooms.remove(room.id)
    assert find_room_of_user(users["Primo"]) is None
