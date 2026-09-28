"""P31: i casi limite che capitano davvero a chi gioca.

- Doppio clic su una carta: due mosse con la stessa version, una sola passa.
- Mossa fuori turno e dati sbagliati: errore, e la partita continua.
- Stesso utente in due schede: l'ultima prende il posto (D14); in coda la seconda
  scheda è "già in coda", e lo stesso request_id non crea doppioni.
- Disconnessione a metà partita: gli altri vedono il posto scollegato, chi rientra
  ritrova la sua mano e continua.
- Senza login il collegamento si rifiuta.
"""

import threading

import pytest
import socketio as sio_client

from tests.e2e.helpers import WAIT, request_id, sit, wait_game_start


def start_1v1(users, target_score=150):
    """Due utenti nuovi abbinati dalla coda 1v1, già al tavolo: (utenti, schede per posto, game_id, version)."""
    players = users(2)
    tabs = [user.tab() for user in players]
    for tab in tabs:
        answer = tab.call("queue:join", {"request_id": request_id(), "mode": "1v1", "target_score": target_score})
        assert answer["ok"] is True, answer
    game_id = wait_game_start(tabs)
    seats, version = sit(tabs, game_id)
    by_seat = [next(u for u in players if u.username == seats[0].state(version)["players"][s]["username"])
               for s in range(2)]
    return by_seat, seats, game_id, version


def test_doppio_clic_una_sola_carta(users):
    _players, seats, game_id, version = start_1v1(users)
    turn = seats[0].state(version)["turn"]["seat"]
    view = seats[turn].state(version)
    move = {"game_id": game_id, "version": version, "card": view["legal"]["play"][0]}
    answers = [None, None]
    barrier = threading.Barrier(2)

    def click(index):
        barrier.wait()
        answers[index] = seats[turn].call("game:play_card", move)

    clicks = [threading.Thread(target=click, args=(i,)) for i in range(2)]
    for thread in clicks:
        thread.start()
    for thread in clicks:
        thread.join(WAIT)
    codes = sorted("ok" if a["ok"] else a["error"]["code"] for a in answers)
    assert codes == ["ok", "stale_state"], answers
    after = seats[turn].state(version + 1)
    assert len(after["hand"]) == len(view["hand"]) - 1
    assert len(after["trick"]["cards"]) == 1
    # Nessuna vista con una version più alta: la seconda carta non è stata giocata
    assert max(v["version"] for v in seats[turn].received("game:state")) == version + 1


def test_fuori_turno_e_dati_sbagliati_non_fermano_la_partita(users):
    _players, seats, game_id, version = start_1v1(users)
    turn = seats[0].state(version)["turn"]["seat"]
    other = 1 - turn
    card = seats[other].state(version)["hand"][0]
    answer = seats[other].call("game:play_card", {"game_id": game_id, "version": version, "card": card})
    assert answer["ok"] is False and answer["error"]["code"] == "not_your_turn"
    for bad in ({"game_id": game_id, "version": version, "card": "denari-1"},
                {"game_id": game_id, "version": "1", "card": card},
                {"game_id": game_id},
                "partita"):
        answer = seats[turn].call("game:play_card", bad)
        assert answer["ok"] is False and answer["error"]["code"] == "invalid_data", (bad, answer)
    # La stanza risponde ancora: la mossa giusta passa
    play = {"game_id": game_id, "version": version, "card": seats[turn].state(version)["legal"]["play"][0]}
    assert seats[turn].call("game:play_card", play) == {"ok": True}
    seats[other].state(version + 1)


def test_stesso_utente_in_due_schede_al_tavolo(users):
    players, seats, game_id, version = start_1v1(users)
    turn = seats[0].state(version)["turn"]["seat"]
    old = seats[turn]
    new = players[turn].tab()
    assert new.call("game:join", {"game_id": game_id}) == {"ok": True}
    assert old.wait_for("game:replaced") == {"game_id": game_id}
    view = new.wait_for("game:state")  # la vista può arrivare dopo la risposta a game:join
    move = {"game_id": game_id, "version": view["version"], "card": view["legal"]["play"][0]}
    answer = old.call("game:play_card", move)
    assert answer["ok"] is False and answer["error"]["code"] == "not_allowed"
    assert new.call("game:play_card", move) == {"ok": True}
    seats[1 - turn].state(view["version"] + 1)


def test_stesso_utente_in_due_schede_in_coda(users):
    (anna,) = users(1)
    first, second = anna.tab(), anna.tab()
    join = {"request_id": request_id(), "mode": "1v1", "target_score": 500}
    answer = first.call("queue:join", join)
    assert answer["ok"] is True
    # Lo stesso tentativo (stesso request_id) riceve la stessa risposta, senza doppioni
    again = first.call("queue:join", join)
    assert again["ok"] is True and again["data"]["mode"] == "1v1"
    # Un altro tentativo dalla seconda scheda: già in coda
    busy = second.call("queue:join", {"request_id": request_id(), "mode": "1v1", "target_score": 500})
    assert busy["ok"] is False and busy["error"]["code"] == "busy"
    # "Annulla" in una scheda: esce dalla coda anche l'altra
    assert first.call("queue:leave", {}) == {"ok": True}
    for tab in (first, second):
        assert tab.wait_for("queue:left") == {"reason": "cancelled"}


def test_disconnessione_a_meta_e_rientro(users):
    players, seats, game_id, version = start_1v1(users)
    turn = seats[0].state(version)["turn"]["seat"]
    other = 1 - turn
    hand_before = seats[other].state(version)["hand"]

    seats[other].close()  # per esempio il telefono perde la rete
    # Solo le viste dopo che tutti e due erano seduti: prima l'altro risultava non ancora arrivato
    watching = seats[turn].wait_for("game:state",
                                    lambda v: v["version"] > version and not v["players"][other]["connected"])
    left = watching["players"][other]["reconnect_seconds_left"]
    assert left is not None and 0 < left <= 60

    back = players[other].tab()
    home = back.wait_for("home:status")
    assert home["resume"]["game_id"] == game_id  # la home propone di rientrare
    assert back.call("game:join", {"game_id": game_id}) == {"ok": True}
    view = back.wait_for("game:state")
    assert view["hand"] == hand_before
    assert view["players"][other]["connected"] is True and view["players"][other]["reconnect_seconds_left"] is None
    seats[turn].wait_for("game:state", lambda v: v["version"] >= view["version"] and v["players"][other]["connected"])

    # Si continua: chi è di turno gioca, chi è rientrato riceve la vista nuova
    current = seats[turn].latest_state()
    play = {"game_id": game_id, "version": current["version"], "card": current["legal"]["play"][0]}
    assert seats[turn].call("game:play_card", play) == {"ok": True}
    assert back.state(current["version"] + 1)["trick"]["cards"][0]["seat"] == turn


def test_senza_login_niente_collegamento(server):
    client = sio_client.Client(reconnection=False)
    with pytest.raises(sio_client.exceptions.ConnectionError):
        client.connect(server["url"], transports=["websocket"], wait_timeout=WAIT)
