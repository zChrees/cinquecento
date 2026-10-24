"""R4 (REVIEW.md): una stanza finita si toglie dalla memoria FINISHED_ROOM_SECONDS dopo la fine.

- Subito dopo la fine la stanza c'è ancora (il risultato si vede, si può ricaricare);
  dopo l'attesa non c'è più e game:join risponde not_found.
- Una partita in corso non si toglie; anche la partita contro la CPU (che non si salva) sì.
I test accorciano l'attesa con monkeypatch; la rimozione non manda eventi, quindi si
aspetta che rooms.get restituisca None, con un limite di tempo.
"""

import time

import pytest

from app.realtime import room_manager
from app.realtime.events import ok
from app.realtime.room import CPU_PLAYER, Player
from app.realtime.room_manager import create_room, rooms

WAIT = 5


@pytest.fixture
def players(server):
    """I due giocatori veri di conftest.py, come Player."""
    ids = server["user_ids"]
    return [Player(user_id=ids["Primo"], username="Primo"), Player(user_id=ids["Secondo"], username="Secondo")]


@pytest.fixture
def created():
    """L'elenco delle stanze create dal test: alla fine si tolgono quelle rimaste."""
    made = []
    yield made
    for room in made:
        rooms.remove(room.id)


def wait_removed(room_id):
    """Aspetta che la stanza sparisca dall'elenco; False se dopo WAIT secondi c'è ancora."""
    deadline = time.monotonic() + WAIT
    while time.monotonic() < deadline:
        if rooms.get(room_id) is None:
            return True
        time.sleep(0.02)
    return False


def test_la_stanza_finita_si_toglie_dopo_l_attesa(monkeypatch, server, connect, players, created):
    monkeypatch.setattr(room_manager, "FINISHED_ROOM_SECONDS", 0.3)
    room = create_room(players, "1v1", 150)
    created.append(room)
    client = connect("Primo")
    assert client.call("game:join", {"game_id": room.id}, timeout=WAIT) == ok()

    assert room.abandon(1)
    assert rooms.get(room.id) is room, "subito dopo la fine la stanza deve esserci ancora"
    assert wait_removed(room.id), "la stanza finita non si è tolta"

    answer = client.call("game:join", {"game_id": room.id}, timeout=WAIT)
    assert answer["ok"] is False
    assert answer["error"]["code"] == "not_found"


def test_la_partita_in_corso_resta_e_quella_contro_la_cpu_si_toglie(monkeypatch, server, players, created):
    monkeypatch.setattr(room_manager, "FINISHED_ROOM_SECONDS", 0.1)
    playing = create_room(players, "1v1", 150)
    created.append(playing)
    # Terzo contro la CPU (Primo e Secondo sono già in partita: create_room li rifiuterebbe)
    terzo = Player(user_id=server["user_ids"]["Terzo"], username="Terzo")
    against_cpu = create_room([terzo, CPU_PLAYER], "1v1", 150, rated=False, cpu_seats=(1,))
    created.append(against_cpu)

    # La partita contro la CPU finisce per abbandono (non si salva, D43): si toglie lo stesso
    assert against_cpu.abandon(0)
    assert wait_removed(against_cpu.id), "la partita contro la CPU finita non si è tolta"
    # Quella in corso, creata prima, c'è ancora
    assert rooms.get(playing.id) is playing
    assert not playing.finished


def test_una_stanza_fatta_senza_create_room_non_programma_niente(room):
    """Le stanze di prova (rooms.create, fixture room) non hanno on_finish: _save non lo chiama."""
    assert room.on_finish is None
