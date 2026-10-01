"""P88: il rating di ogni giocatore nella vista (contratto 3.3, `players[].rating`).

Con il server vero (conftest.py): create_room legge il rating dei giocatori una volta
sola, quando la partita comincia, con gli stessi numeri del pannello statistiche
(stats_service.stats_of, P30): valore arrotondato e "provvisorio", nella modalità della
partita; null per la CPU (P68) e per una stanza creata fuori da Flask.
"""

import threading

import pytest
import sqlalchemy as sa

from app.extensions import db
from app.models.rating import Rating
from app.models.user import User
from app.realtime.events import ok
from app.realtime.room import CPU_PLAYER, Player, utc_now
from app.realtime.room_manager import create_room, rooms
from app.repositories import rating_repo
from app.services import auth_service, stats_service

WAIT = 5
PASSWORD = "Password-di-prova-1"


@pytest.fixture(scope="module")
def app(server):
    return server["app"]


@pytest.fixture(scope="module")
def users(app, server):
    """Primo, Secondo e Terzo di conftest.py più "Quarto" (solo se non c'è: lo registrano anche altri file)."""
    with app.app_context():
        quarto = db.session.scalar(sa.select(User.id).where(User.username == "Quarto"))
        if quarto is None:
            quarto = auth_service.register("Quarto", "quarto@esempio.it", PASSWORD).id
            db.session.commit()
    return {**server["user_ids"], "Quarto": quarto}


@pytest.fixture
def ratings(app, users):
    """ratings({("Primo", "1v1"): 1623.5, ...}) scrive le righe di rating; alla fine le toglie."""
    written = []

    def _write(values):
        with app.app_context():
            for (name, mode), value in values.items():
                rating_repo.add(users[name], mode, value, 80.0, 0.06, utc_now())
                written.append((users[name], mode))
            db.session.commit()

    yield _write
    with app.app_context():
        for user_id, mode in written:
            db.session.execute(sa.delete(Rating).where(Rating.user_id == user_id, Rating.mode == mode))
        db.session.commit()


@pytest.fixture
def new_room(app, users):
    """new_room(["Primo", "Secondo"], "1v1") → stanza creata dentro Flask, come fanno coda e inviti."""
    created = []

    def _new_room(names, mode, **options):
        players = [CPU_PLAYER if name == "CPU" else Player(users[name], name) for name in names]
        with app.app_context():
            room = create_room(players, mode, 150, **options)
        created.append(room)
        return room

    yield _new_room
    for room in created:
        room.run(room._stop_timers)
        rooms.remove(room.id)


def _stats(app, user_id, mode):
    with app.app_context():
        rating = stats_service.stats_of(user_id)["ratings"][mode]
    return {"value": rating["value"], "provisional": rating["provisional"]}


def test_1v1_rating_nella_vista_vera(app, users, ratings, new_room, connect):
    """Dal tavolo vero: ognuno vede il rating di tutti e due, come nel pannello statistiche."""
    ratings({("Primo", "1v1"): 1623.5, ("Primo", "2v2"): 1400.0})
    room = new_room(["Primo", "Secondo"], "1v1")
    client = connect("Primo")
    views = []
    arrived = threading.Event()
    client.on("game:state", lambda view: (views.append(view), arrived.set()))
    assert client.call("game:join", {"game_id": room.id}, timeout=WAIT) == ok()
    assert arrived.wait(WAIT), "nessuna vista"
    players = views[-1]["players"]
    # Primo: 1623,5 arrotondato per eccesso, ed è il valore 1v1 (non quello 2v2);
    # Secondo non ha la riga: 1500 e provvisorio (D9)
    assert [p["rating"] for p in players] == [{"value": 1624, "provisional": True},
                                             {"value": 1500, "provisional": True}]
    assert [p["rating"] for p in players] == [_stats(app, users[n], "1v1") for n in ("Primo", "Secondo")]


def test_2v2_rating_della_modalita_uguale_per_tutti(app, users, ratings, new_room):
    ratings({("Primo", "2v2"): 1712.2, ("Terzo", "2v2"): 1388.0, ("Terzo", "1v1"): 1900.0})
    names = ["Primo", "Secondo", "Terzo", "Quarto"]
    room = new_room(names, "2v2")
    views = [room.view_for(seat) for seat in range(4)]
    expected = [_stats(app, users[n], "2v2") for n in names]
    assert expected[0]["value"] == 1712 and expected[2]["value"] == 1388
    for view in views:
        assert [p["rating"] for p in view["players"]] == expected


def test_il_rating_resta_quello_di_inizio_partita(app, users, ratings, new_room):
    ratings({("Primo", "1v1"): 1550.0})
    room = new_room(["Primo", "Secondo"], "1v1")
    with app.app_context():
        db.session.execute(sa.update(Rating).where(Rating.user_id == users["Primo"], Rating.mode == "1v1")
                           .values(value=1800.0))
        db.session.commit()
    assert room.view_for(0)["players"][0]["rating"]["value"] == 1550


def test_anche_la_partita_tra_amici_che_non_conta_mostra_il_rating(users, ratings, new_room):
    ratings({("Secondo", "1v1"): 1490.4})
    room = new_room(["Primo", "Secondo"], "1v1", rated=False)
    assert room.view_for(0)["players"][1]["rating"] == {"value": 1490, "provisional": True}


def test_la_cpu_non_ha_rating(new_room, monkeypatch):
    from app.realtime import room as room_module

    monkeypatch.setattr(room_module, "CPU_SECONDS", 60)  # la CPU non deve giocare durante il test
    room = new_room(["Primo", "CPU"], "1v1", rated=False, cpu_seats=(1,))
    players = room.view_for(0)["players"]
    assert players[0]["rating"] == {"value": 1500, "provisional": True}
    assert players[1]["rating"] is None


def test_stanza_creata_fuori_da_flask_senza_rating(users):
    room = create_room([Player(users["Primo"], "Primo"), Player(users["Secondo"], "Secondo")], "1v1", 150)
    try:
        assert [p["rating"] for p in room.view_for(0)["players"]] == [None, None]
    finally:
        room.run(room._stop_timers)
        rooms.remove(room.id)


def test_database_che_non_risponde_la_partita_parte_lo_stesso(users, new_room, monkeypatch, caplog):
    def broken(_user_id):
        raise sa.exc.OperationalError("SELECT", {}, Exception("giù"))

    monkeypatch.setattr(stats_service, "stats_of", broken)
    room = new_room(["Primo", "Secondo"], "1v1")
    assert [p["rating"] for p in room.view_for(0)["players"]] == [None, None]
    assert room.game is not None
    assert "Rating dei giocatori" in caplog.text
