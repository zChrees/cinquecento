"""home:refresh (contratto 5.1, dal 23/10/2026, passo 8h della migrazione).

La home della SPA chiede lo stato quando compare con il collegamento già aperto
(tornando dal tavolo senza ricaricare la pagina): la risposta porta gli stessi dati di
home:status. Con il server vero e client simulati controlla:
- la risposta ha online_count e resume, come home:status;
- con una partita in corso c'è il link per rientrare;
- arriva solo a chi l'ha chiesta: le altre schede dello stesso utente non ricevono niente;
- dati che non servono (anche non validi) non cambiano la risposta, come per queue:leave.
"""

import threading
import time

import pytest

from app.realtime.presence import presence
from app.realtime.room import Player
from app.realtime.room_manager import create_room, rooms

WAIT = 5


def _wait_until(condition, what, timeout=WAIT):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return
        time.sleep(0.02)
    pytest.fail(f"non è successo: {what}")


@pytest.fixture(autouse=True)
def nobody_online(server):
    """Ogni prova parte senza schede collegate (come test_home_stato.py)."""
    _wait_until(lambda: presence.count() == 0, "chiusura delle schede delle prove precedenti")


@pytest.fixture
def new_room():
    created = []

    def _new(user_ids):
        room = create_room([Player(u, f"U{u}") for u in user_ids], "1v1", 300)
        created.append(room)
        return room

    yield _new
    for room in created:
        room.run(room._stop_timers)
        rooms.remove(room.id)


def test_risposta_con_lo_stato_della_home(connect):
    client = connect("Primo")
    answer = client.call("home:refresh", {}, timeout=WAIT)
    assert answer == {"ok": True, "data": {"online_count": 1, "resume": None}}


def test_con_una_partita_in_corso_il_link_per_rientrare(connect, server, new_room):
    ids = server["user_ids"]
    room = new_room([ids["Primo"], ids["Secondo"]])
    client = connect("Primo")
    answer = client.call("home:refresh", {}, timeout=WAIT)
    assert answer["ok"] is True
    assert answer["data"]["resume"] == {"game_id": room.id, "url": f"/game/{room.id}",
                                        "mode": "1v1", "target_score": 300}


def test_solo_a_chi_la_chiede(connect, server):
    user_id = server["user_ids"]["Primo"]
    received = []
    lock = threading.Lock()

    def listen(client):
        def receive(data):
            with lock:
                received.append(data)
        client.on("home:status", receive)

    connect("Primo", before=listen)
    _wait_until(lambda: len(received) == 1, "home:status al collegamento dell'altra scheda")
    client = connect("Primo")
    _wait_until(lambda: len(presence._tabs.get(user_id, ())) == 2, "seconda scheda dello stesso utente")
    assert client.call("home:refresh", {}, timeout=WAIT)["ok"] is True
    time.sleep(0.3)  # un home:status in più arriverebbe subito: qui non deve arrivare
    with lock:
        assert len(received) == 1


@pytest.mark.parametrize("payload", [None, "testo", 12, [1, 2], {"qualcosa": 1}])
def test_dati_che_non_servono_non_cambiano_la_risposta(connect, payload):
    client = connect("Primo")
    answer = client.call("home:refresh", payload, timeout=WAIT)
    assert answer == {"ok": True, "data": {"online_count": 1, "resume": None}}
