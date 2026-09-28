"""P25: timer del turno, scollegamento e rientro, abbandono (D12, D13).

Client simulati contro il server vero (conftest.py). I tempi si riducono a pochi
decimi di secondo cambiando TURN_SECONDS e RECONNECT_SECONDS di app/realtime/room.py
prima di creare la stanza (la stanza li legge quando la partita parte).
Si aspettano gli eventi (le viste), non tempi fissi; solo per provare che qualcosa
NON succede si aspetta un po' più del tempo in gioco.
"""

import random
import re
import threading
import time

import pytest
import requests
import sqlalchemy as sa

from app.realtime import room as room_module
from app.realtime.events import ok
from app.realtime.room import Player
from app.realtime.room_manager import create_room, find_room_of_user, rooms
from config import load_config

WAIT = 5
PASSWORD = "Password-di-prova-1"  # la stessa degli utenti di conftest.py
NO_MOVES = {"play": [], "sing": []}


@pytest.fixture(scope="module")
def users(server):
    """Gli utenti di conftest.py più "Quarto" (serve al 2v2), registrato se non c'è già."""
    engine = sa.create_engine(load_config("testing").SQLALCHEMY_DATABASE_URI)
    try:
        with engine.connect() as conn:
            quarto = conn.execute(sa.text("SELECT id FROM utenti WHERE nome_utente = 'Quarto'")).scalar()
        if quarto is None:
            session = requests.Session()
            page = session.get(f"{server['url']}/auth/register", timeout=WAIT).text
            token = re.search(r'name="csrf_token" type="hidden" value="([^"]+)"', page)[1]
            response = session.post(f"{server['url']}/auth/register", data={
                "csrf_token": token, "username": "Quarto", "email": "quarto@esempio.it",
                "password": PASSWORD, "confirm": PASSWORD,
            }, allow_redirects=False, timeout=WAIT)
            assert response.status_code == 302
            with engine.connect() as conn:
                quarto = conn.execute(sa.text("SELECT id FROM utenti WHERE nome_utente = 'Quarto'")).scalar()
    finally:
        engine.dispose()
    return {**server["user_ids"], "Quarto": quarto}


@pytest.fixture
def new_room(users, monkeypatch):
    """new_room(["Primo", "Secondo"], "1v1", turn=..., reconnect=...) → stanza con quei tempi."""
    created = []

    def _new_room(names, mode="1v1", turn=30, reconnect=60, **options):
        monkeypatch.setattr(room_module, "TURN_SECONDS", turn)
        monkeypatch.setattr(room_module, "RECONNECT_SECONDS", reconnect)
        players = [Player(user_id=users[n], username=n) for n in names]
        room = create_room(players, mode, 150, rng=random.Random(7), **options)
        created.append(room)
        return room

    yield _new_room
    for room in created:
        room.run(room._stop_timers)  # niente mosse automatiche dopo la prova
        rooms.remove(room.id)


class Seat:
    """Un giocatore al tavolo: tiene tutte le viste ricevute e aspetta quella che serve."""

    def __init__(self, client):
        self.client = client
        self.views = []
        self._cond = threading.Condition()
        client.on("game:state", self._on_state)

    def _on_state(self, view):
        with self._cond:
            self.views.append(view)
            self._cond.notify_all()

    @property
    def last(self):
        with self._cond:
            return max(self.views, key=lambda v: v["version"]) if self.views else None

    def wait_for(self, check, timeout=WAIT):
        """La prima vista (in ordine di arrivo) che soddisfa `check`."""
        with self._cond:
            found = []

            def match():
                found[:] = [v for v in self.views if check(v)][:1]
                return bool(found)

            assert self._cond.wait_for(match, timeout), "la vista attesa non è arrivata"
            return found[0]

    def call(self, event, data):
        return self.client.call(event, data, timeout=WAIT)


def sit(connect, room, names):
    seats = [Seat(connect(name)) for name in names]
    for seat in seats:
        assert seat.call("game:join", {"game_id": room.id}) == ok()
    version = room.version
    for seat in seats:
        seat.wait_for(lambda v, version=version: v["version"] >= version)
    return seats


def finished_by_abandon(view):
    return view["status"] == "finished" and view["result"] is not None and view["result"]["reason"] == "abandon"


# --- Timer del turno (D12) ---


def shorten_turn(room, seconds):
    """Turno ridotto dopo che tutti sono seduti: il timer riparte adesso, sotto il lock.

    Con il turno corto già alla creazione, le mosse automatiche partono mentre i client
    si collegano: se tocca a chi risponde, la sua carta chiude la presa, va in
    last_trick e non compare mai in trick (test instabile, P25).
    """
    def _shorten():
        room.turn_seconds = seconds
        room._start_turn()

    room.run(_shorten)


def test_turno_scaduto_il_server_gioca_la_mossa_automatica(connect, new_room):
    room = new_room(["Primo", "Secondo"], turn=30)
    seats = sit(connect, room, ["Primo", "Secondo"])
    first = seats[0].last
    assert first["trick"]["cards"] == []  # nessuna mossa prima del timer: chi ha il turno apre la presa
    turn = first["turn"]["seat"]
    legal = seats[turn].last["legal"]["play"]
    shorten_turn(room, 0.3)
    assert room.view_for(0)["turn"]["seconds_total"] == 0.3

    after = seats[0].wait_for(lambda v: any(c["seat"] == turn for c in v["trick"]["cards"]))
    played = next(c["card"] for c in after["trick"]["cards"] if c["seat"] == turn)
    assert played in legal  # una carta ammessa
    assert after["sings"] == []  # la mossa automatica non canta mai
    assert after["turn"]["seat"] != turn  # il turno è passato all'altro
    assert after["status"] == "playing"


def test_mossa_giocata_prima_del_timer_una_sola_carta(connect, new_room):
    room = new_room(["Primo", "Secondo"], turn=30)
    seats = sit(connect, room, ["Primo", "Secondo"])
    view = seats[0].last
    turn = view["turn"]["seat"]
    old_turn = room._turn_token
    answer = seats[turn].call("game:play_card", {"game_id": room.id, "version": view["version"],
                                                "card": seats[turn].last["legal"]["play"][0]})
    assert answer == ok()
    version = room.version
    room._turn_expired(old_turn)  # il timer del turno appena finito arriva in ritardo
    assert room.version == version  # non ha giocato niente
    assert sum(p["cards_in_hand"] for p in room.view_for(0)["players"]) == 9


def test_il_timer_riparte_a_ogni_turno(connect, new_room):
    room = new_room(["Primo", "Secondo"], turn=30)
    seats = sit(connect, room, ["Primo", "Secondo"])
    view = seats[0].last
    turn = view["turn"]["seat"]
    time.sleep(0.3)
    seats[turn].call("game:play_card", {"game_id": room.id, "version": view["version"],
                                        "card": seats[turn].last["legal"]["play"][0]})
    fresh = seats[0].wait_for(lambda v: v["turn"] is not None and v["turn"]["seat"] != turn)
    assert fresh["turn"]["seconds_left"] > 29.5


# --- Scollegamento e rientro ---


def test_scollegato_e_rientro_in_tempo(connect, new_room):
    room = new_room(["Primo", "Secondo"], reconnect=1.0)
    seats = sit(connect, room, ["Primo", "Secondo"])
    before = room.version
    seats[1].client.disconnect()

    view = seats[0].wait_for(lambda v: v["version"] > before and not v["players"][1]["connected"])
    left = view["players"][1]["reconnect_seconds_left"]
    assert left is not None and 0 < left <= 1.0
    assert view["players"][0]["reconnect_seconds_left"] is None

    back = Seat(connect("Secondo"))
    assert back.call("game:join", {"game_id": room.id}) == ok()
    mine = back.wait_for(lambda v: v["players"][1]["connected"])
    assert mine["you"]["seat"] == 1 and len(mine["hand"]) == 5  # di nuovo la sua vista
    assert mine["players"][1]["reconnect_seconds_left"] is None
    again = seats[0].wait_for(lambda v: v["version"] > view["version"] and v["players"][1]["connected"])
    assert again["players"][1]["reconnect_seconds_left"] is None

    time.sleep(1.3)  # oltre il tempo per rientrare: non deve succedere niente
    assert not room.finished
    assert not any(finished_by_abandon(v) for v in seats[0].views)


def test_non_rientrato_in_tempo_partita_persa_per_abbandono(connect, new_room, users):
    room = new_room(["Primo", "Secondo"], reconnect=0.4)
    seats = sit(connect, room, ["Primo", "Secondo"])
    seats[1].client.disconnect()

    view = seats[0].wait_for(finished_by_abandon)
    assert view["result"]["abandoned_seats"] == [1]
    assert view["result"]["winner_team"] == 0
    assert view["turn"] is None and view["legal"] == NO_MOVES
    assert view["players"][1]["reconnect_seconds_left"] is None
    assert room.finished
    assert find_room_of_user(users["Primo"]) is None and find_room_of_user(users["Secondo"]) is None

    # Rientrare dopo non cambia niente, e non si gioca più
    late = Seat(connect("Secondo"))
    assert late.call("game:join", {"game_id": room.id}) == ok()
    assert finished_by_abandon(late.wait_for(lambda v: v["players"][1]["connected"]))
    answer = late.call("game:play_card", {"game_id": room.id, "version": room.version,
                                          "card": {"suit": "denari", "rank": 1}})
    assert answer["ok"] is False and answer["error"]["code"] == "not_allowed"


def test_chi_non_arriva_al_tavolo_non_ha_limite(connect, new_room):
    """Scelta (b) di Antonio: nessun conto alla rovescia, la mossa automatica gioca per lui."""
    room = new_room(["Primo", "Secondo"], turn=0.2, reconnect=0.2)
    seats = sit(connect, room, ["Primo"])
    first = seats[0].last
    assert first["players"][1]["connected"] is False
    assert first["players"][1]["reconnect_seconds_left"] is None

    def seat_1_played(v):
        cards = v["trick"]["cards"] + (v["last_trick"]["cards"] if v["last_trick"] else [])
        return any(c["seat"] == 1 for c in cards)

    view = seats[0].wait_for(seat_1_played)
    assert view["status"] == "playing"
    assert not any(finished_by_abandon(v) for v in seats[0].views)


def test_scheda_che_non_e_al_tavolo_non_scollega_il_posto(connect, new_room):
    room = new_room(["Primo", "Secondo"])
    sit(connect, room, ["Primo", "Secondo"])
    version = room.version
    other = connect("Primo")  # per esempio la home aperta in un'altra scheda
    other.disconnect()
    time.sleep(0.3)
    assert room.version == version
    assert room.view_for(0)["players"][0]["connected"] is True


def test_scheda_sostituita_non_scollega_il_posto(connect, new_room):
    room = new_room(["Primo", "Secondo"], reconnect=0.4)
    seats = sit(connect, room, ["Primo", "Secondo"])
    newer = Seat(connect("Primo"))
    assert newer.call("game:join", {"game_id": room.id}) == ok()
    seats[0].client.disconnect()  # la scheda vecchia, già sostituita (D14)
    time.sleep(0.8)
    assert not room.finished
    assert room.view_for(1)["players"][0]["connected"] is True


# --- Abbandono con "Esci" (game:leave) ---


def test_esci_partita_persa_per_abbandono(connect, new_room):
    room = new_room(["Primo", "Secondo"])
    seats = sit(connect, room, ["Primo", "Secondo"])
    assert seats[0].call("game:leave", {"game_id": room.id}) == ok()

    view = seats[1].wait_for(finished_by_abandon)
    assert view["result"]["abandoned_seats"] == [0]
    assert view["result"]["winner_team"] == 1
    assert [s["team"] for s in view["result"]["scores"]] == [0, 1]
    assert room.finished

    version = room.version
    assert seats[0].call("game:leave", {"game_id": room.id}) == ok()  # seconda volta: niente cambia
    assert room.version == version
    answer = seats[1].call("game:play_card", {"game_id": room.id, "version": version,
                                              "card": {"suit": "denari", "rank": 1}})
    assert answer["ok"] is False and answer["error"]["code"] == "not_allowed"


def test_esci_nel_2v2_perde_tutta_la_squadra(connect, new_room):
    names = ["Primo", "Secondo", "Terzo", "Quarto"]
    room = new_room(names, "2v2")
    seats = sit(connect, room, names)
    assert seats[1].call("game:leave", {"game_id": room.id}) == ok()
    for seat in (seats[0], seats[2], seats[3]):
        view = seat.wait_for(finished_by_abandon)
        assert view["result"]["abandoned_seats"] == [1]
        assert view["result"]["winner_team"] == 0  # la squadra dei posti 1 e 3 perde (D13)


def test_esci_solo_da_chi_e_seduto_al_tavolo(connect, new_room):
    room = new_room(["Primo", "Secondo"])
    sit(connect, room, ["Primo", "Secondo"])
    answer = connect("Terzo").call("game:leave", {"game_id": room.id}, timeout=WAIT)
    assert answer["error"]["code"] == "not_allowed"
    answer = connect("Primo").call("game:leave", {"game_id": room.id}, timeout=WAIT)  # senza game:join
    assert answer["error"]["code"] == "not_allowed"
    assert not room.finished


@pytest.mark.parametrize("data", [None, {}, {"game_id": 5}, {"game_id": ""}])
def test_esci_con_dati_non_validi(connect, data):
    answer = connect("Primo").call("game:leave", data, timeout=WAIT)
    assert answer["error"]["code"] == "invalid_data"


def test_esci_da_una_partita_che_non_esiste(connect):
    answer = connect("Primo").call("game:leave", {"game_id": "non-esiste"}, timeout=WAIT)
    assert answer["error"]["code"] == "not_found"


def test_a_partita_finita_i_timer_si_fermano(connect, new_room):
    room = new_room(["Primo", "Secondo"], turn=0.2, reconnect=0.2)
    seats = sit(connect, room, ["Primo", "Secondo"])
    seats[0].call("game:leave", {"game_id": room.id})
    seats[1].wait_for(finished_by_abandon)
    version = room.version
    seats[1].client.disconnect()
    time.sleep(0.6)  # più di un turno e di un rientro: nessuna mossa, nessun nuovo abbandono
    assert room.abandoned_seats == (0,)
    assert room.version == version + 1  # solo lo scollegamento
