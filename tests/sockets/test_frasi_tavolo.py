"""P55: frasi del tavolo in tempo reale (D24, contratto 3.2).

Client simulati contro il server vero (conftest.py). Il limite di una frase ogni 3
secondi si riduce cambiando MIN_INTERVAL_SECONDS di app/realtime/table_phrases.py.
Si aspettano gli eventi, non tempi fissi; solo per provare che qualcosa NON arriva,
o che il limite è passato, si aspetta un po' più del tempo in gioco.
"""

import logging
import random
import re
import threading
import time

import pytest
import requests
import sqlalchemy as sa

from app.realtime import table_phrases
from app.realtime.events import ok
from app.realtime.room import Player
from app.realtime.room_manager import create_room, rooms
from config import load_config

WAIT = 5
PASSWORD = "Password-di-prova-1"  # la stessa degli utenti di conftest.py
TABLES_THAT_COULD_KEEP_TEXT = ("messaggi", "mosse_partita", "partite")


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
def new_room(users):
    """new_room(["Primo", "Secondo"], "1v1") → stanza creata con create_room, tolta alla fine."""
    created = []

    def _new_room(names, mode="1v1"):
        players = [Player(user_id=users[n], username=n) for n in names]
        room = create_room(players, mode, 150, rng=random.Random(7))
        created.append(room)
        return room

    yield _new_room
    for room in created:
        room.run(room._stop_timers)
        rooms.remove(room.id)


class Seat:
    """Un client: tiene gli eventi ricevuti, nell'ordine di arrivo, e aspetta quello che serve."""

    EVENTS = ("game:phrases", "game:phrase", "game:state")

    def __init__(self, client):
        self.client = client
        self.events = []  # (nome, dati)
        self._cond = threading.Condition()
        for name in self.EVENTS:
            client.on(name, lambda data, name=name: self._on(name, data))

    def _on(self, name, data):
        with self._cond:
            self.events.append((name, data))
            self._cond.notify_all()

    def received(self, name):
        with self._cond:
            return [data for event, data in self.events if event == name]

    def wait_for(self, name, count=1, timeout=WAIT):
        with self._cond:
            assert self._cond.wait_for(lambda: len(self.received(name)) >= count, timeout), \
                f"{name} non è arrivato"
            return self.received(name)[count - 1]

    def call(self, event, data):
        return self.client.call(event, data, timeout=WAIT)


def sit(connect, room, names):
    seats = [Seat(connect(name)) for name in names]
    for seat in seats:
        assert seat.call("game:join", {"game_id": room.id}) == ok()
    for seat in seats:
        seat.wait_for("game:phrases")
    return seats


def send(seat, room, code):
    return seat.call("game:send_phrase", {"game_id": room.id, "code": code})


def code_of(answer):
    return answer["error"]["code"] if not answer["ok"] else "ok"


# --- Elenco (D24) ---


def test_elenco_approvato():
    assert len(table_phrases.PHRASES) == 19
    assert table_phrases.PHRASES["amuni"] == "Amunì!"
    assert table_phrases.PHRASES["calati_juncu"] == "Càlati juncu ca passa la china"
    assert all(re.fullmatch(r"[a-z_]+", code) for code in table_phrases.PHRASES)


def test_limite_in_config():
    assert load_config("testing").TABLE_PHRASE_MIN_INTERVAL_SECONDS == 3
    assert table_phrases.MIN_INTERVAL_SECONDS == 3


def test_elenco_a_chi_entra_prima_della_vista(connect, new_room):
    room = new_room(["Primo", "Secondo"])
    seats = sit(connect, room, ["Primo", "Secondo"])
    for seat in seats:
        seat.wait_for("game:state")
        names = [name for name, _ in seat.events]
        assert names.index("game:phrases") < names.index("game:state")
        phrases = seat.received("game:phrases")[0]["phrases"]
        assert phrases == [{"code": c, "text": t} for c, t in table_phrases.PHRASES.items()]


# --- Invio ---


def test_frase_a_tutti_nel_1v1(connect, new_room):
    room = new_room(["Primo", "Secondo"])
    seats = sit(connect, room, ["Primo", "Secondo"])
    assert send(seats[1], room, "amuni") == ok()
    for seat in seats:  # anche a chi l'ha mandata
        assert seat.wait_for("game:phrase") == {"seat": 1, "code": "amuni"}


def test_frase_a_tutti_nel_2v2_anche_agli_avversari(connect, new_room):
    names = ["Primo", "Secondo", "Terzo", "Quarto"]
    room = new_room(names, "2v2")
    seats = sit(connect, room, names)
    assert send(seats[2], room, "bella_mossa") == ok()
    for seat in seats:
        assert seat.wait_for("game:phrase") == {"seat": 2, "code": "bella_mossa"}


def test_frase_anche_a_partita_finita(connect, new_room):
    room = new_room(["Primo", "Secondo"])
    seats = sit(connect, room, ["Primo", "Secondo"])
    assert seats[0].call("game:leave", {"game_id": room.id}) == ok()
    assert room.finished
    assert send(seats[1], room, "bella_partita") == ok()
    assert seats[0].wait_for("game:phrase") == {"seat": 1, "code": "bella_partita"}


# --- Rifiuti ---


def test_chi_non_e_seduto_rifiutato(connect, new_room):
    room = new_room(["Primo", "Secondo"])
    seats = sit(connect, room, ["Primo", "Secondo"])
    assert code_of(send(Seat(connect("Terzo")), room, "ciao")) == "not_allowed"
    time.sleep(0.3)
    assert seats[0].received("game:phrase") == []


def test_scheda_non_al_tavolo_rifiutata(connect, new_room):
    room = new_room(["Primo", "Secondo"])
    sit(connect, room, ["Primo", "Secondo"])
    other = Seat(connect("Primo"))  # per esempio la home, senza game:join
    assert code_of(send(other, room, "ciao")) == "not_allowed"


def test_partita_che_non_esiste(connect):
    answer = connect("Primo").call("game:send_phrase", {"game_id": "non-esiste", "code": "ciao"}, timeout=WAIT)
    assert code_of(answer) == "not_found"


@pytest.mark.parametrize("code", ["sconosciuta", "Amuni", "", None, 3, ["ciao"], "Amunì!"])
def test_codice_non_valido_rifiutato(connect, new_room, code):
    room = new_room(["Primo", "Secondo"])
    seats = sit(connect, room, ["Primo", "Secondo"])
    assert code_of(send(seats[0], room, code)) == "invalid_data"
    assert room.phrase_times == {}  # un rifiuto non conta per il limite


@pytest.mark.parametrize("data", [None, {}, {"game_id": 5, "code": "ciao"}, "ciao"])
def test_dati_non_validi(connect, data):
    answer = connect("Primo").call("game:send_phrase", data, timeout=WAIT)
    assert code_of(answer) == "invalid_data"


# --- Limite di tempo ---


def test_seconda_frase_troppo_presto(connect, new_room, monkeypatch):
    monkeypatch.setattr(table_phrases, "MIN_INTERVAL_SECONDS", 0.3)
    room = new_room(["Primo", "Secondo"])
    seats = sit(connect, room, ["Primo", "Secondo"])
    assert send(seats[0], room, "ciao") == ok()
    answer = send(seats[0], room, "mizzica")
    assert code_of(answer) == "too_fast"
    assert answer["error"]["retry_after"] == 1  # secondi interi, arrotondati per eccesso
    assert send(seats[1], room, "fozza") == ok()  # il limite è per giocatore

    time.sleep(0.35)
    assert send(seats[0], room, "mizzica") == ok()
    seats[1].wait_for("game:phrase", 3)
    assert [p["code"] for p in seats[1].received("game:phrase")] == ["ciao", "fozza", "mizzica"]


def test_limite_vero_di_3_secondi(connect, new_room):
    room = new_room(["Primo", "Secondo"])
    seats = sit(connect, room, ["Primo", "Secondo"])
    assert send(seats[0], room, "ciao") == ok()
    answer = send(seats[0], room, "ciao")
    assert code_of(answer) == "too_fast"
    assert answer["error"]["retry_after"] == 3


# --- Niente nel database né nel log ---


def _counts():
    engine = sa.create_engine(load_config("testing").SQLALCHEMY_DATABASE_URI)
    try:
        with engine.connect() as conn:
            return {t: conn.execute(sa.text(f"SELECT COUNT(*) FROM {t}")).scalar()
                    for t in TABLES_THAT_COULD_KEEP_TEXT}
    finally:
        engine.dispose()


def test_niente_nel_database_ne_nel_log(connect, new_room, caplog):
    caplog.set_level(logging.DEBUG)
    before = _counts()
    room = new_room(["Primo", "Secondo"])
    seats = sit(connect, room, ["Primo", "Secondo"])
    assert send(seats[0], room, "calati_juncu") == ok()
    seats[1].wait_for("game:phrase")
    assert code_of(send(seats[0], room, "chi_fai_dormi")) == "too_fast"
    assert code_of(send(seats[1], room, "frase-inventata")) == "invalid_data"

    assert _counts() == before
    secret = ("calati_juncu", "Càlati juncu", "chi_fai_dormi", "Chi fai, dormi", "frase-inventata")
    for record in caplog.records:
        assert not any(s in record.getMessage() for s in secret), record.getMessage()
