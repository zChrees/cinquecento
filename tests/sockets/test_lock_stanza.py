"""P23: gli eventi di una stanza passano uno alla volta dal lock della stanza.

50 azioni inviate insieme da 5 client arrivano al server in parallelo (un thread
per evento), ma dentro il lock entra un evento alla volta: il contatore arriva
esattamente a 50 e nessuna risposta è un errore.
"""

import threading

from app.realtime.room import Room
from app.realtime.room_manager import RoomManager

WAIT = 10
CLIENTS = 5
ACTIONS_PER_CLIENT = 10


def test_50_azioni_insieme_elaborate_una_alla_volta(connect, room, server):
    probe = server["probe"]
    probe.reset()
    clients = [connect(name) for name in ("Primo", "Secondo", "Terzo", "Primo", "Secondo")]
    answers = []
    all_done = threading.Event()
    guard = threading.Lock()

    def on_answer(answer):
        with guard:
            answers.append(answer)
            if len(answers) == CLIENTS * ACTIONS_PER_CLIENT:
                all_done.set()

    for _ in range(ACTIONS_PER_CLIENT):
        for client in clients:
            client.emit("test:increment", {"room_id": room.id}, callback=on_answer)

    assert all_done.wait(WAIT), f"arrivate solo {len(answers)} risposte"
    assert all(a["ok"] for a in answers), [a for a in answers if not a["ok"]]
    assert probe.counter == CLIENTS * ACTIONS_PER_CLIENT
    assert sorted(a["data"]["counter"] for a in answers) == list(range(1, 51))
    assert probe.max_inside == 1        # nel lock un evento alla volta
    assert probe.max_entered > 1        # ...ma gli eventi arrivavano davvero in parallelo


# --- Stanza e RoomManager (senza server) ---


def test_run_restituisce_il_risultato_e_si_puo_annidare():
    room = Room("prova")
    assert room.run(lambda: room.run(lambda x: x * 2, 21)) == 42


def test_room_manager_crea_trova_toglie():
    manager = RoomManager()
    a, b = manager.create(), manager.create()
    assert a.id != b.id
    assert len(a.id) >= 12
    assert manager.get(a.id) is a
    assert manager.get(None) is None
    assert manager.get(123) is None
    a.add_member(7)
    assert manager.rooms_of(7) == [a]
    assert manager.remove(a.id) is a
    assert manager.get(a.id) is None
    assert manager.rooms_of(7) == []
    assert len(manager) == 1
