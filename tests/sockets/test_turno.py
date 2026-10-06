"""P94: turno da 15 secondi, che parte dopo le pause del tavolo.

- Le pause del server sono le stesse della pagina (js/pages/game.js): un test le confronta.
- table_pause dà la pausa giusta per ogni mossa (carta dentro la presa, presa chiusa con e
  senza pescata, mano nuova, mano finita con una calata).
- Con il server vero, dopo una presa il conto alla rovescia parte solo a pausa finita, e
  intanto la vista dice che il turno è pieno.
- P118: all'inizio della partita la pagina mostra mescolata e distribuzione: il primo turno
  parte dopo, contando da quando l'ultimo giocatore vero arriva al tavolo (non da un rientro).
"""

import random
import re
import threading
import time
from dataclasses import replace
from pathlib import Path

import pytest

from app.game.engine.actions import LayDownAction, PlayCardAction
from app.game.engine.cards import Card, Suit
from app.game.engine.deck import full_deck
from app.game.engine.game import apply_game, game_legal_actions, new_game
from app.game.engine.singing import Sing
from app.game.engine.state import HandState, LastTrick, TrickPlay
from app.realtime import room as room_module
from app.realtime.events import ok
from app.realtime.room import CPU_PLAYER, Player, first_deal_pause, table_pause
from app.realtime.room_manager import create_room, rooms
from config import BaseConfig

WAIT = 5
GAME_JS = (Path(__file__).resolve().parents[2] / "app" / "static" / "js" / "pages" / "game.js").read_text(
    encoding="utf-8")


@pytest.fixture(autouse=True)
def table_pauses(monkeypatch, no_table_pauses):
    """Qui le pause servono: conftest.py le toglie agli altri test della suite."""
    monkeypatch.setattr(room_module, "PAUSE_SCALE", 1)


def page_ms(name):
    return int(re.search(rf"const {name} = (\d+);", GAME_JS).group(1))


@pytest.mark.parametrize(("page", "server"), [
    ("LAST_TRICK_MS", "LAST_TRICK_SECONDS"),
    ("SUMMARY_MS", "SUMMARY_SECONDS"),
    ("THROW_MS", "THROW_SECONDS"),
    ("DRAW_MS", "DRAW_SECONDS"),
    ("SHUFFLE_MS", "SHUFFLE_SECONDS"),
    ("DEAL_STEP_MS", "DEAL_STEP_SECONDS"),
])
def test_pause_uguali_a_quelle_della_pagina(page, server):
    assert page_ms(page) == round(getattr(room_module, server) * 1000)


def test_turno_da_15_secondi():
    assert BaseConfig.TURN_SECONDS == 15
    assert room_module.TURN_SECONDS == 15


# --- table_pause, sulle partite del motore ---------------------------------------------


def play_first(game):
    seat = game.hand.turn_seat
    return apply_game(game, PlayCardAction(seat, game_legal_actions(game, seat).play[0]), rng=random.Random(0))


@pytest.mark.parametrize(("players", "pause"), [(2, 1.5), (4, 2.4)])
def test_pausa_dopo_una_presa_con_la_pescata(players, pause):
    game = new_game(players, 500, rng=random.Random(1))
    for _ in range(players - 1):
        after = play_first(game)
        assert table_pause(game, after) == 0  # una carta dentro la presa: nessuna pausa
        game = after
    closed = play_first(game)
    assert closed.hand.deck and not closed.hand.trick
    # 1v1: l'ultima presa (1,5 s) dura più del volo e delle due pescate (0,4 + 2 x 0,5);
    # 2v2: il volo e quattro pescate (0,4 + 4 x 0,5 = 2,4 s) durano di più
    assert table_pause(game, closed) == pytest.approx(pause)


def end_hand(players):
    hands = (("coppe-1", "bastoni-3"), ("coppe-2", "spade-4"), ("denari-1", "denari-3"),
             ("spade-5", "spade-6"))[:players]
    hands = tuple(tuple(Card.from_code(code) for code in hand) for hand in hands)
    rest = [c for c in full_deck() if not any(c in hand for hand in hands)]
    return HandState(
        num_players=players, hands=hands, deck=(), trick=(), leader_seat=0, turn_seat=0,
        sings=(Sing(1, Suit.BASTONI, 40),),
        captured=(tuple(rest[: len(rest) // 2]), tuple(rest[len(rest) // 2:])),
        last_trick=LastTrick(0, tuple(TrickPlay(seat, rest[seat]) for seat in range(players))),
    )


def test_pausa_dopo_una_presa_a_mazzo_finito():
    game = replace(new_game(2, 500, rng=random.Random(1)), hand=end_hand(2))
    after = play_first(game)
    assert table_pause(after, play_first(after)) == pytest.approx(1.5)  # niente pescata: solo l'ultima presa


@pytest.mark.parametrize(("players", "deal"), [(2, 1.3 + 9 * 0.08 + 0.5), (4, 1.3 + 19 * 0.08 + 0.5)])
def test_pausa_a_inizio_mano(players, deal):
    game = replace(new_game(players, 500, rng=random.Random(1)), hand=end_hand(players))
    after = game
    for _ in range(players * 2):  # due prese: la mano finisce
        before, after = after, play_first(after)
    assert after.hand_number == 2
    assert table_pause(before, after) == pytest.approx(1.5 + 5 + deal)
    if players == 2:
        # Con una calata (P84) al posto dell'ultima presa si vedono le carte calate per 3 s
        laid = apply_game(game, LayDownAction(0), rng=random.Random(0))
        assert table_pause(game, laid) == pytest.approx(3 + 5 + deal)


def test_niente_pausa_se_scalata_a_zero(monkeypatch):
    monkeypatch.setattr(room_module, "PAUSE_SCALE", 0)
    game = replace(new_game(2, 500, rng=random.Random(1)), hand=end_hand(2))
    assert table_pause(game, apply_game(game, LayDownAction(0), rng=random.Random(0))) == 0


@pytest.mark.parametrize(("players", "cards"), [(2, 10), (4, 20)])
def test_pausa_della_prima_distribuzione(players, cards):
    # P118: mescolata, una carta ogni DEAL_STEP e il volo dell'ultima, come startDeal di game.js
    assert first_deal_pause(players) == pytest.approx(1.3 + (cards - 1) * 0.08 + 0.5)


def test_prima_distribuzione_scalata_a_zero(monkeypatch):
    monkeypatch.setattr(room_module, "PAUSE_SCALE", 0)
    assert first_deal_pause(2) == 0


# --- Con il server vero ---------------------------------------------------------------


@pytest.fixture
def players(server):
    ids = server["user_ids"]
    made = []
    yield [Player(user_id=ids["Primo"], username="Primo"), Player(user_id=ids["Secondo"], username="Secondo")], made
    for room in made:
        room.run(room._stop_timers)
        rooms.remove(room.id)


class Seat:
    def __init__(self, client):
        self.client = client
        self.views = []
        self._cond = threading.Condition()
        client.on("game:state", self._on_state)

    def _on_state(self, view):
        with self._cond:
            self.views.append((time.monotonic(), view))
            self._cond.notify_all()

    def wait_for(self, check, what):
        with self._cond:
            arrived = self._cond.wait_for(lambda: any(check(view) for _, view in self.views), WAIT)
            assert arrived, f"non è arrivata {what}"
            return next((at, view) for at, view in self.views if check(view))


def test_il_turno_parte_dopo_la_pausa_della_presa(connect, players, monkeypatch):
    people, made = players
    monkeypatch.setattr(room_module, "TURN_SECONDS", 0.4)
    monkeypatch.setattr(room_module, "LAST_TRICK_SECONDS", 0.8)  # 1v1: più lunga di volo e pescata
    monkeypatch.setattr(room_module, "THROW_SECONDS", 0.1)
    monkeypatch.setattr(room_module, "DRAW_SECONDS", 0.1)
    room = create_room(people, "1v1", 150, rated=False, rng=random.Random(3), announce=False)
    made.append(room)
    seats = [Seat(connect(name)) for name in ("Primo", "Secondo")]
    for seat in seats:
        assert seat.client.call("game:join", {"game_id": room.id}, timeout=WAIT) == ok()
    # Si gioca la prima presa a mano, svelti, prima che scada il turno
    for _ in range(2):
        with room.lock:
            seat = room.game.hand.turn_seat
            card = game_legal_actions(room.game, seat).play[0]
            version = room.version
        answer = seats[seat].client.call("game:play_card", {"game_id": room.id, "version": version,
                                                           "card": {"suit": card.suit.value,
                                                                    "rank": card.rank.value}}, timeout=WAIT)
        assert answer == ok(), answer
    closed_version = version + 1
    closed_at, closed = seats[0].wait_for(lambda v: v["version"] == closed_version, "la vista della presa chiusa")
    assert closed["last_trick"] is not None and not closed["trick"]["cards"]
    assert closed["turn"]["seconds_left"] == closed["turn"]["seconds_total"] == 0.4  # pausa: turno pieno
    # Nessuno gioca: la mossa automatica arriva solo dopo la pausa (0,8 s) e il turno (0,4 s)
    auto_at, _ = seats[0].wait_for(lambda v: v["version"] == closed_version + 1, "la mossa automatica")
    assert [move.kind for move in room._moves][-1] == "mossa_automatica"
    assert auto_at - closed_at >= 1.2 - 0.1


# --- P118: il primo turno dopo la distribuzione della prima mano ----------------------


def _turn_starts_in(room):
    with room.lock:
        return room._turn_started - time.monotonic(), room._turn_token


def test_il_primo_turno_parte_dopo_la_distribuzione(connect, players):
    people, made = players
    deal = first_deal_pause(2)
    room = create_room(people, "1v1", 150, rated=False, rng=random.Random(5), announce=False)
    made.append(room)
    starts_in, token = _turn_starts_in(room)
    assert deal - 0.3 <= starts_in <= deal  # già alla creazione, per chi non arriva mai al tavolo
    seats = [Seat(connect(name)) for name in ("Primo", "Secondo")]
    assert seats[0].client.call("game:join", {"game_id": room.id}, timeout=WAIT) == ok()
    assert _turn_starts_in(room)[1] == token  # manca ancora un giocatore: niente di nuovo
    time.sleep(0.5)  # il secondo arriva più tardi: la distribuzione riparte da lui
    assert seats[1].client.call("game:join", {"game_id": room.id}, timeout=WAIT) == ok()
    starts_in, token_all = _turn_starts_in(room)
    assert token_all == token + 1 and deal - 0.3 <= starts_in <= deal
    _, view = seats[1].wait_for(lambda v: v["players"][0]["connected"] and v["players"][1]["connected"],
                                "la vista con tutti e due al tavolo")
    assert view["turn"]["seconds_left"] == view["turn"]["seconds_total"]  # durante la distribuzione: pieno
    # Un rientro (scheda nuova dello stesso giocatore) non fa ripartire niente
    again = Seat(connect("Secondo"))
    assert again.client.call("game:join", {"game_id": room.id}, timeout=WAIT) == ok()
    assert _turn_starts_in(room)[1] == token_all


def test_dopo_la_prima_mossa_l_arrivo_non_cambia_il_turno(connect, players):
    people, made = players
    room = create_room(people, "1v1", 150, rated=False, rng=random.Random(6), announce=False)
    made.append(room)
    first = Seat(connect("Primo"))
    assert first.client.call("game:join", {"game_id": room.id}, timeout=WAIT) == ok()
    with room.lock:
        seat = room.game.hand.turn_seat
        card = game_legal_actions(room.game, seat).play[0]
        room.play(seat, card)  # si gioca prima che arrivi il secondo
        token = room._turn_token
    second = Seat(connect("Secondo"))
    assert second.client.call("game:join", {"game_id": room.id}, timeout=WAIT) == ok()
    assert _turn_starts_in(room)[1] == token


def test_contro_la_cpu_la_prima_mossa_aspetta_la_distribuzione(connect, players, monkeypatch):
    people, made = players
    monkeypatch.setattr(room_module, "CPU_SECONDS", 0.01)
    deal = first_deal_pause(2)
    for seed in range(40):  # una partita in cui comincia la CPU
        room = create_room([people[0], CPU_PLAYER], "1v1", 150, rated=False, rng=random.Random(seed),
                           announce=False, cpu_seats=(1,))
        made.append(room)
        if room.game.hand.turn_seat == 1:
            break
        room.run(room._stop_timers)
        rooms.remove(room.id)
        made.pop()
    else:
        pytest.fail("nessuna partita in cui comincia la CPU")
    seat = Seat(connect("Primo"))
    joined_at = time.monotonic()
    assert seat.client.call("game:join", {"game_id": room.id}, timeout=WAIT) == ok()
    played_at, _ = seat.wait_for(lambda v: v["trick"]["cards"], "la carta della CPU")
    assert played_at - joined_at >= deal - 0.1
