"""R7 (REVIEW.md): coda, CPU e inviti sotto lo stesso lock.

- queue:join con un invito aperto (mandato o ricevuto) risponde busy, come dice il contratto.
- queue:join aspetta il lock degli inviti, come cpu:start: se nel frattempo l'utente è
  entrato in partita (qui la partita la crea il test tenendo il lock, come farebbe cpu:start
  da un'altra scheda), risponde busy e l'utente non finisce in coda. Prima entrava in coda
  lo stesso: in coda e in partita insieme.
- Se la coda abbina qualcuno che nel frattempo è entrato in partita, create_room rifiuta:
  gli altri tornano in coda e lui riceve queue:left "cancelled" (prima nessun avviso, e la
  sua pagina restava "in coda").
"""

import threading
import time
import uuid

import pytest

from app.realtime.invites import invites
from app.realtime.matchmaking import matchmaker
from app.realtime.room import Player
from app.realtime.room_manager import create_room, find_room_of_user, rooms

WAIT = 5


class Events:
    """Raccoglie gli eventi di un nome; wait(n) aspetta che ne siano arrivati n."""

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


def _join(client, target_score=150, mode="1v1"):
    return client.call("queue:join", {"request_id": uuid.uuid4().hex, "mode": mode,
                                      "target_score": target_score}, timeout=WAIT)


def _player(ids, name):
    return Player(user_id=ids[name], username=name)


@pytest.fixture
def ids(server):
    return server["user_ids"]


@pytest.fixture(autouse=True)
def clean(server):
    """Coda, inviti e partite degli utenti di prova vuoti prima e dopo ogni prova."""
    users = server["user_ids"].values()

    def clean_all():
        for user_id in users:
            matchmaker.queue.leave(user_id)
            invites.cancel_all_of(user_id)
            room = find_room_of_user(user_id)
            if room is not None:
                room.run(room._stop_timers)
                rooms.remove(room.id)

    clean_all()
    yield
    clean_all()


def test_con_un_invito_aperto_non_si_entra_in_coda(connect, ids):
    invites.send(_player(ids, "Secondo"), _player(ids, "Primo"), "1v1", 150)  # Primo l'ha ricevuto
    answer = _join(connect("Primo"))
    assert answer["ok"] is False and answer["error"]["code"] == "busy"
    assert answer["error"]["message"] == "Hai un invito aperto: annullalo prima di cercare una partita."
    assert ids["Primo"] not in matchmaker.queue
    # Anche chi l'ha mandato
    answer = _join(connect("Secondo"))
    assert answer["ok"] is False and answer["error"]["code"] == "busy"
    assert ids["Secondo"] not in matchmaker.queue


def test_queue_join_aspetta_il_lock_e_vede_la_partita_appena_creata(connect, ids):
    client = connect("Primo")
    answers = []
    worker = threading.Thread(target=lambda: answers.append(_join(client)), daemon=True)
    with invites.lock:
        worker.start()
        # queue:join è arrivato al server e aspetta il lock: non risponde e Primo non è in coda
        time.sleep(0.5)
        assert answers == [], "queue:join non aspetta il lock degli inviti"
        assert ids["Primo"] not in matchmaker.queue
        # Intanto Primo entra in partita (come cpu:start da un'altra scheda, che tiene il lock)
        create_room([_player(ids, "Primo"), _player(ids, "Terzo")], "1v1", 150)
    worker.join(WAIT)
    assert len(answers) == 1, "queue:join non ha risposto"
    assert answers[0]["ok"] is False and answers[0]["error"]["code"] == "busy"
    assert ids["Primo"] not in matchmaker.queue, "in partita e in coda insieme"


def test_chi_non_torna_in_coda_riceve_queue_left(connect, ids):
    primo, secondo = connect("Primo"), connect("Secondo")
    left_primo, left_secondo = Events(primo, "queue:left"), Events(secondo, "queue:left")
    starts = Events(secondo, "game:start")
    assert _join(primo)["ok"] is True
    # Primo è in coda e intanto (per un'altra via) entra in partita con Terzo
    create_room([_player(ids, "Primo"), _player(ids, "Terzo")], "1v1", 150)
    # Arriva Secondo: la coda abbina Primo e Secondo, create_room rifiuta (Primo è in partita)
    assert _join(secondo)["ok"] is True
    assert left_primo.wait(), "Primo non ha ricevuto queue:left"
    assert left_primo.items[0] == {"reason": "cancelled"}
    assert ids["Primo"] not in matchmaker.queue
    # Secondo torna in coda (l'ordine delle voci non è fisso: si aspetta), senza queue:left né game:start
    deadline = time.monotonic() + WAIT
    while ids["Secondo"] not in matchmaker.queue:
        assert time.monotonic() < deadline, "Secondo non è tornato in coda"
        time.sleep(0.02)
    assert left_secondo.items == [] and starts.items == []
