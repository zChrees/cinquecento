"""P92: carte del compagno scoperte a mazzo finito e consiglio (D46), con il server vero.

Quattro client Socket.IO simulati in una partita 2v2. La mano si prepara a mazzo finito,
con la briscola, sostituendola nella stanza sotto il suo lock prima che i giocatori si
siedano. Si aspettano gli eventi, non tempi fissi: per sapere che a un giocatore non è
arrivato un consiglio gli si fa rifare game:join, e la vista arriva dopo ogni evento
mandato prima (l'ordine per ogni client è quello di invio).
"""

import json
import re
import threading
from dataclasses import replace

import pytest
import requests
import sqlalchemy as sa

from app.game.engine.cards import Card, Suit
from app.game.engine.deck import full_deck
from app.game.engine.singing import Sing
from app.game.engine.state import HandState, LastTrick, TrickPlay
from app.realtime.events import ok
from app.realtime.room import Player
from app.realtime.room_manager import create_room, rooms
from config import load_config

WAIT = 5
PASSWORD = "Password-di-prova-1"  # la stessa degli utenti di conftest.py
NAMES = ["Primo", "Secondo", "Terzo", "Quarto"]
# A mazzo finito, briscola bastoni, di turno il posto 2 (il compagno del posto 0)
HANDS = (
    ("coppe-1", "spade-3", "denari-7"),
    ("coppe-2", "spade-4", "denari-6"),
    ("bastoni-1", "coppe-5", "spade-6"),
    ("bastoni-2", "coppe-7", "spade-7"),
)


def end_hand(hands=HANDS, turn=2, deck=()):
    hands = tuple(tuple(Card.from_code(code) for code in hand) for hand in hands)
    deck = tuple(Card.from_code(code) for code in deck)
    rest = [c for c in full_deck() if not any(c in hand for hand in hands) and c not in deck]
    return HandState(
        num_players=4, hands=hands, deck=deck, trick=(), leader_seat=turn, turn_seat=turn,
        sings=(Sing(1, Suit.BASTONI, 40),),
        captured=(tuple(rest[: len(rest) // 2]), tuple(rest[len(rest) // 2:])),
        last_trick=LastTrick(turn, tuple(TrickPlay((turn + step) % 4, rest[step]) for step in range(4))),
    )


@pytest.fixture(scope="module")
def users(server):
    """Gli utenti di conftest.py più "Quarto", solo se non c'è già (lo registrano anche altri file)."""
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


@pytest.fixture(autouse=True)
def clean(users):
    def _clean():
        for user_id in users.values():
            for room in rooms.rooms_of(user_id):
                room.run(room._stop_timers)
                rooms.remove(room.id)

    _clean()
    yield
    _clean()


class Seat:
    def __init__(self, client):
        self.client = client
        self.state = None
        self.advice = []
        self._cond = threading.Condition()
        client.on("game:state", self._on_state)
        client.on("game:advice", self._on_advice)

    def _on_state(self, view):
        with self._cond:
            if self.state is None or view["version"] >= self.state["version"]:
                self.state = view
            self._cond.notify_all()

    def _on_advice(self, data):
        with self._cond:
            self.advice.append(data)
            self._cond.notify_all()

    def wait_for(self, check, what):
        with self._cond:
            arrived = self._cond.wait_for(lambda: check(self), WAIT)
        assert arrived, f"non è arrivato {what}"

    def call(self, event, data):
        return self.client.call(event, data, timeout=WAIT)

    def fresh_state(self, game_id):
        """Rifà game:join e aspetta la vista: arriva dopo ogni evento mandato prima a questo client."""
        with self._cond:
            self.state = None
        assert self.call("game:join", {"game_id": game_id}) == ok()
        self.wait_for(lambda seat: seat.state is not None, "la vista")
        return self.state


def prepared(users, mode="2v2", hand=None):
    names = NAMES if mode == "2v2" else NAMES[:2]
    room = create_room([Player(user_id=users[n], username=n) for n in names], mode, 500, rated=False)
    with room.lock:
        room.game = replace(room.game, hand=hand or end_hand(), first_seat=2)
        room._start_turn()
    return room


def sit(connect, room, names=NAMES):
    seats = [Seat(connect(name)) for name in names]
    for seat in seats:
        assert seat.call("game:join", {"game_id": room.id}) == ok()
    for seat in seats:
        seat.wait_for(lambda s: s.state is not None and s.state["version"] >= room.version, "la vista")
    return seats


def codes(cards):
    return [f"{c['suit']}-{c['rank']}" for c in cards]


def card(code):
    suit, rank = code.split("-")
    return {"suit": suit, "rank": int(rank)}


def test_ognuno_vede_le_carte_del_compagno_e_non_degli_avversari(connect, users):
    room = prepared(users)
    seats = sit(connect, room)
    for index, seat in enumerate(seats):
        view = seat.state
        assert codes(view["partner_hand"]) == list(HANDS[(index + 2) % 4])
        assert view["advice"] is None
        text = json.dumps(view)
        assert all(json.dumps(card(code)) in text for code in HANDS[(index + 2) % 4])  # il confronto funziona
        for opponent in ((index + 1) % 4, (index + 3) % 4):
            for code in HANDS[opponent]:
                assert json.dumps(card(code)) not in text  # le carte degli avversari mai


def test_prima_del_mazzo_finito_niente_carte_del_compagno(connect, users):
    room = prepared(users, hand=end_hand(deck=("denari-1", "denari-2", "denari-3", "denari-4")))
    seats = sit(connect, room)
    assert all(seat.state["partner_hand"] is None for seat in seats)
    answer = seats[0].call("game:advise", {"game_id": room.id, "card": card("bastoni-1")})
    assert answer["ok"] is False and answer["error"]["code"] == "illegal_move"
    assert answer["error"]["message"] == "Le carte del compagno si vedono solo a mazzo finito, con la briscola."


def test_il_consiglio_arriva_solo_al_compagno(connect, users):
    room = prepared(users)
    seats = sit(connect, room)
    answer = seats[0].call("game:advise", {"game_id": room.id, "card": card("coppe-5")})
    assert answer == ok(), answer
    seats[2].wait_for(lambda s: s.advice, "il consiglio")
    assert seats[2].advice == [{"seat": 0, "card": card("coppe-5")}]
    # Agli altri non arriva niente: la loro vista nuova arriva dopo il consiglio, se ci fosse stato
    for other in (0, 1, 3):
        view = seats[other].fresh_state(room.id)
        assert seats[other].advice == [] and view["advice"] is None
    # Chi lo riceve lo ritrova nella vista, per esempio rientrando
    assert seats[2].fresh_state(room.id)["advice"] == {"seat": 0, "card": card("coppe-5")}


def test_un_consiglio_alla_volta_e_si_toglie(connect, users):
    room = prepared(users)
    seats = sit(connect, room)
    for code in ("coppe-5", "spade-6"):
        assert seats[0].call("game:advise", {"game_id": room.id, "card": card(code)}) == ok()
    assert seats[2].fresh_state(room.id)["advice"] == {"seat": 0, "card": card("spade-6")}
    assert seats[0].call("game:advise", {"game_id": room.id, "card": None}) == ok()
    seats[2].wait_for(lambda s: len(s.advice) == 3, "il consiglio tolto")
    assert seats[2].advice[-1] == {"seat": 0, "card": None}
    assert seats[2].fresh_state(room.id)["advice"] is None


def test_il_consiglio_sparisce_quando_il_compagno_gioca(connect, users):
    room = prepared(users)
    seats = sit(connect, room)
    assert seats[0].call("game:advise", {"game_id": room.id, "card": card("bastoni-1")}) == ok()
    view = seats[2].fresh_state(room.id)
    assert view["advice"] == {"seat": 0, "card": card("bastoni-1")}
    # Il compagno gioca un'altra carta: è solo un consiglio
    played = seats[2].call("game:play_card", {"game_id": room.id, "version": view["version"],
                                              "card": card("spade-6")})
    assert played == ok(), played
    seats[2].wait_for(lambda s: s.state["version"] > view["version"], "la vista dopo la carta")
    assert seats[2].state["advice"] is None
    assert [move.kind for move in room._moves] == ["gioca_carta"]  # il consiglio non è una mossa


def test_consigli_rifiutati(connect, users):
    room = prepared(users)
    seats = sit(connect, room)
    # Una carta che il compagno non ha (è dell'avversario)
    answer = seats[0].call("game:advise", {"game_id": room.id, "card": card("coppe-2")})
    assert answer["ok"] is False and answer["error"]["code"] == "illegal_move"
    assert answer["error"]["message"] == "Il tuo compagno non ha questa carta."
    for data in ({"game_id": room.id}, {"game_id": room.id, "card": {"suit": "coppe"}},
                 {"game_id": room.id, "card": "coppe-5"}):
        answer = seats[0].call("game:advise", data)
        assert answer["ok"] is False and answer["error"]["code"] == "invalid_data", data
    assert seats[2].fresh_state(room.id)["advice"] is None and seats[2].advice == []


def test_nel_1v1_niente_compagno(connect, users):
    hand = replace(end_hand(), num_players=2, hands=end_hand().hands[:2], turn_seat=0, leader_seat=0,
                   last_trick=LastTrick(0, end_hand().last_trick.plays[:2]))
    room = prepared(users, mode="1v1", hand=hand)
    seats = sit(connect, room, NAMES[:2])
    assert "partner_hand" not in seats[0].state and "advice" not in seats[0].state
    answer = seats[0].call("game:advise", {"game_id": room.id, "card": card("coppe-2")})
    assert answer["ok"] is False and answer["error"]["message"] == "Il consiglio al compagno c'è solo nel 2v2."
