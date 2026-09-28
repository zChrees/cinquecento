"""Stanza in memoria: chi c'è dentro, il lock che mette in fila i suoi eventi e la partita (P23, P24).

Regola (CLAUDE.md, "Stanze di gioco"): ogni evento di una stanza si elabora sotto
il lock di quella stanza, e timer e mosse passano dalla stessa via, `room.run(...)`.

P24: la stanza tiene la partita del motore, il numero `version` della vista (sale a
ogni cambiamento, anche di connessione) e la connessione al tavolo di ogni posto.
Ogni giocatore riceve solo la propria vista. Timer, riconnessione e abbandono: P25.
"""

import secrets
import threading
import time
from dataclasses import dataclass

from app.extensions import socketio
from app.game.engine.actions import PlayCardAction, SingAction
from app.game.engine.cards import Card, Rank
from app.game.engine.game import apply_game, new_game
from app.game.engine.views import card_to_dict, player_view
from app.realtime.events import room_channel
from config import BaseConfig

MODES = {"1v1": 2, "2v2": 4}
TURN_SECONDS = BaseConfig.TURN_SECONDS  # il timer che gioca da solo lo aggiunge P25
SING_SHOW_SECONDS = 3  # D15: per quanto la pagina mostra Re e Cavallo cantati


@dataclass(frozen=True)
class Player:
    user_id: int
    username: str
    avatar: str | None = None

    @classmethod
    def of(cls, user):
        """Da un Player o da un utente (User di app.models): se ne copiano solo i dati da mostrare."""
        if isinstance(user, cls):
            return user
        return cls(user_id=user.id, username=user.username, avatar=user.avatar)


class Room:
    def __init__(self, room_id):
        self.id = room_id
        self.channel = room_channel(room_id)
        self.lock = threading.RLock()
        self.members = set()  # user_id dei giocatori

        # Partita (P24): None finché start() non la fa partire
        self.players = ()  # Player per posto
        self.rated = True
        self.game = None
        self.version = 0
        self.sids = {}  # posto -> connessione al tavolo (l'ultima scheda che ha fatto game:join, D14)
        self._rng = None
        self._turn_started = None

    # --- Lock e membri (P23) ---

    def run(self, action, *args, **kwargs):
        """Esegue `action` sotto il lock della stanza: un evento alla volta."""
        with self.lock:
            return action(*args, **kwargs)

    def add_member(self, user_id):
        with self.lock:
            self.members.add(user_id)

    def remove_member(self, user_id):
        with self.lock:
            self.members.discard(user_id)

    def has_member(self, user_id):
        with self.lock:
            return user_id in self.members

    # --- Partita (P24) ---

    def start(self, players, target_score, rated=True, rng=None):
        """Mette i giocatori ai posti (nell'ordine dato) e fa partire la partita del motore."""
        with self.lock:
            self._rng = rng if rng is not None else secrets.SystemRandom()
            self.players = tuple(players)
            self.members = {p.user_id for p in self.players}
            self.rated = rated
            self.game = new_game(len(self.players), target_score, self._rng)
            self.version = 1
            self._turn_started = time.monotonic()

    @property
    def finished(self):
        return self.game is not None and self.game.finished

    def seat_of(self, user_id):
        for seat, player in enumerate(self.players):
            if player.user_id == user_id:
                return seat
        return None

    def join(self, seat, sid):
        """Collega la scheda `sid` al posto; restituisce la connessione sostituita (D14) o None."""
        with self.lock:
            old = self.sids.get(seat)
            self.sids[seat] = sid
            if old != sid:
                self.version += 1
            return old if old not in (None, sid) else None

    def is_table_connection(self, seat, sid):
        with self.lock:
            return self.sids.get(seat) == sid

    def play(self, seat, card: Card):
        """Gioca una carta (il motore controlla turno e regole); poi sale la version."""
        with self.lock:
            self._apply(PlayCardAction(seat, card))

    def sing(self, seat, suit):
        """Canta un seme; restituisce l'evento game:sang da mostrare a tutti (D15)."""
        with self.lock:
            before = len(self.game.hand.sings)
            self._apply(SingAction(seat, suit))
            done = self.game.hand.sings[before]
            return {
                "seat": seat,
                "suit": done.suit.value,
                "points": done.points,
                "cards": [card_to_dict(Card(suit, Rank.KING)), card_to_dict(Card(suit, Rank.KNIGHT))],
                "show_seconds": SING_SHOW_SECONDS,
            }

    def _apply(self, action):
        before = self.game
        self.game = apply_game(self.game, action, self._rng)
        self.version += 1
        if self.game.finished or self.game.hand.turn_seat != before.hand.turn_seat \
                or self.game.hand_number != before.hand_number:
            self._turn_started = time.monotonic()

    def view_for(self, seat):
        """La vista del contratto (3.3) per quel posto: quella del motore più i campi della stanza."""
        with self.lock:
            view = player_view(self.game, seat)
            view = {"game_id": self.id, "version": self.version, "rated": self.rated, **view}
            for entry in view["players"]:
                player = self.players[entry["seat"]]
                entry.update(
                    user_id=player.user_id,
                    username=player.username,
                    avatar=player.avatar,
                    connected=entry["seat"] in self.sids,
                    reconnect_seconds_left=None,  # P25
                )
            if view["turn"] is not None:
                elapsed = time.monotonic() - self._turn_started
                view["turn"].update(seconds_total=TURN_SECONDS,
                                    seconds_left=round(max(0.0, TURN_SECONDS - elapsed), 1))
            return view

    def send_state(self, seat):
        """Manda a un posto la sua vista, sulla sua connessione al tavolo (se c'è)."""
        with self.lock:
            sid = self.sids.get(seat)
            if sid is not None:
                socketio.emit("game:state", self.view_for(seat), to=sid)

    def broadcast_states(self):
        """Ogni giocatore collegato riceve la propria vista: mai quella degli altri."""
        with self.lock:
            for seat in range(len(self.players)):
                self.send_state(seat)
