"""Stato della home (P44, contratto 5.1): home:status {"online_count", "resume"}.

- presence.py da solo: lo stesso utente con due schede conta una volta.
- Con il server vero e client simulati: home:status appena collegati; il numero sale e
  scende con le connessioni e arriva agli altri utenti collegati; chi ha una partita in
  corso riceve il link per rientrare, che sparisce quando la partita finisce.
"""

import threading
import time

import pytest

from app.realtime.presence import Presence, presence
from app.realtime.room import Player
from app.realtime.room_manager import create_room, rooms
from app.sockets.home_events import home_status

WAIT = 5

# --- presence.py da solo --------------------------------------------------------


def test_due_schede_contano_una_volta():
    p = Presence()
    assert p.add(1, "a") is True
    assert p.add(1, "b") is False
    assert p.add(2, "c") is True
    assert p.count() == 2 and p.is_online(1)
    assert p.remove(1, "a") is False  # ha ancora la scheda "b"
    assert p.count() == 2
    assert p.remove(1, "b") is True
    assert p.count() == 1 and not p.is_online(1)
    assert p.online_users() == [2]


def test_togliere_una_scheda_sconosciuta_non_cambia_niente():
    p = Presence()
    p.add(1, "a")
    assert p.remove(1, "x") is False
    assert p.remove(9, "a") is False
    assert p.count() == 1


# --- Con il server vero ---------------------------------------------------------


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

    def wait_for(self, test, timeout=WAIT):
        with self._cond:
            ok = self._cond.wait_for(lambda: any(test(item) for item in self.items), timeout)
        assert ok, f"home:status atteso non arrivato; ricevuti: {self.items}"

    @property
    def last(self):
        with self._cond:
            return self.items[-1]


def _wait_until(condition, what, timeout=WAIT):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return
        time.sleep(0.02)
    pytest.fail(f"non è successo: {what}")


@pytest.fixture
def home(connect):
    """home("Primo") → (client, eventi home:status), in ascolto già prima del collegamento."""

    def _home(name):
        box = {}
        client = connect(name, before=lambda c: box.update(events=Events(c, "home:status")))
        return client, box["events"]

    return _home


@pytest.fixture(autouse=True)
def nobody_online(server):
    """Ogni prova parte senza schede collegate (quelle delle prove precedenti si chiudono da sole)."""
    _wait_until(lambda: presence.count() == 0, "chiusura delle schede delle prove precedenti")


@pytest.fixture
def new_room():
    created = []

    def _new(user_ids, mode="1v1", target=150):
        room = create_room([Player(u, f"U{u}") for u in user_ids], mode, target)
        created.append(room)
        return room

    yield _new
    for room in created:
        room.run(room._stop_timers)
        rooms.remove(room.id)


def test_stato_appena_collegati(home):
    _, events = home("Primo")
    events.wait_for(lambda s: True)
    assert events.items[0] == {"online_count": 1, "resume": None}


def test_il_numero_sale_e_scende_e_arriva_agli_altri(home, server):
    ids = server["user_ids"]
    _primo, primo_events = home("Primo")
    primo_events.wait_for(lambda s: s["online_count"] == 1)

    secondo, secondo_events = home("Secondo")
    secondo_events.wait_for(lambda s: s["online_count"] == 2)
    primo_events.wait_for(lambda s: s["online_count"] == 2)

    secondo.disconnect()
    primo_events.wait_for(lambda s: s["online_count"] == 1 and primo_events.last["online_count"] == 1)
    assert not presence.is_online(ids["Secondo"])


def test_due_schede_dello_stesso_utente_contano_una_volta(home, server):
    ids = server["user_ids"]
    scheda_a, _events_a = home("Primo")
    _scheda_b, events_b = home("Primo")
    events_b.wait_for(lambda s: True)
    assert events_b.items[0]["online_count"] == 1

    scheda_a.disconnect()
    _wait_until(lambda: len(presence._tabs.get(ids["Primo"], ())) == 1, "chiusura della prima scheda")
    assert presence.is_online(ids["Primo"]) and presence.count() == 1


def test_chi_ha_una_partita_in_corso_riceve_il_link_per_rientrare(home, server, new_room):
    ids = server["user_ids"]
    room = new_room([ids["Primo"], ids["Secondo"]], target=300)
    _, events = home("Primo")
    events.wait_for(lambda s: s["resume"] is not None)
    assert events.items[0]["resume"] == {"game_id": room.id, "url": f"/game/{room.id}",
                                         "mode": "1v1", "target_score": 300}


def test_a_fine_partita_il_link_sparisce(home, server, new_room):
    ids = server["user_ids"]
    room = new_room([ids["Primo"], ids["Secondo"]])
    _, primo_events = home("Primo")
    _, secondo_events = home("Secondo")
    primo_events.wait_for(lambda s: s["resume"] is not None)

    assert room.run(room.abandon, 1) is True  # la partita finisce (abbandono di Secondo)
    primo_events.wait_for(lambda s: s["resume"] is None)
    secondo_events.wait_for(lambda s: s["resume"] is None)


def test_resume_nel_2v2():
    room = create_room([Player(u, f"U{u}") for u in (901, 902, 903, 904)], "2v2", 500)
    try:
        assert home_status(903)["resume"] == {"game_id": room.id, "url": f"/game/{room.id}",
                                              "mode": "2v2", "target_score": 500}
        assert home_status(905)["resume"] is None
    finally:
        room.run(room._stop_timers)
        rooms.remove(room.id)
