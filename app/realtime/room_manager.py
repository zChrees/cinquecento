"""Elenco delle stanze attive, in memoria (P23, P24). Un solo processo (DECISIONI.md): basta un dizionario.

Il lock del manager protegge solo l'elenco (creare, trovare, togliere una stanza);
quello che succede dentro una stanza passa dal lock della stanza (room.py).

Funzioni esposte da P24, che altri punti usano senza modificare questo file:
- create_room(giocatori, modalità, punteggio): per la coda (P28, P29) e gli inviti (P47);
- find_room_of_user(user_id): per il rientro in partita (P44).
"""

import secrets
import threading

from app.extensions import socketio
from app.game.engine.errors import EngineError
from app.realtime import room as room_module
from app.realtime.events import user_channel
from app.realtime.room import MODES, Player, Room


class RoomError(ValueError):
    """create_room rifiutata: giocatori, modalità o punteggio non validi, o un giocatore già in partita."""


class RoomManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._rooms = {}

    def _new_id(self):
        room_id = secrets.token_urlsafe(9)
        while room_id in self._rooms:
            room_id = secrets.token_urlsafe(9)
        return room_id

    def create(self):
        """Crea una stanza vuota con un codice nuovo, difficile da indovinare (è il game_id del contratto)."""
        with self._lock:
            room = Room(self._new_id())
            self._rooms[room.id] = room
            return room

    def create_room(self, players, mode, target_score, rated=True, rng=None, announce=True):
        """Crea la stanza e fa partire la partita; ogni giocatore riceve game:start (contratto 3.2).

        `players` in ordine di posto: nel 2v2 i posti 0 e 2 sono una squadra, 1 e 3 l'altra
        (contratto 3.1). Accetta oggetti Player o utenti (User). `rated` è False solo nel
        1v1 contro un amico (D36). Un giocatore già in una partita in corso → RoomError.
        """
        if mode not in MODES:
            raise RoomError(f'Modalità non valida: "{mode}".')
        players = tuple(Player.of(p) for p in players)
        if len(players) != MODES[mode]:
            raise RoomError(f"Nel {mode} servono {MODES[mode]} giocatori, non {len(players)}.")
        if len({p.user_id for p in players}) != len(players):
            raise RoomError("Lo stesso giocatore non può avere due posti.")
        with self._lock:
            busy = [p.username for p in players if self._room_of(p.user_id) is not None]
            if busy:
                raise RoomError(f"Già in partita: {', '.join(busy)}.")
            room = Room(self._new_id())
            try:
                room.start(players, target_score, rated=rated, rng=rng)
            except EngineError as exc:
                raise RoomError(str(exc)) from None
            self._rooms[room.id] = room
        room_module.notify(room_module.start_listeners, (p.user_id for p in players), room._app)  # P47
        if announce:
            for player in players:
                socketio.emit("game:start", {"game_id": room.id, "url": f"/game/{room.id}"},
                              to=user_channel(player.user_id))
        return room

    def find_room_of_user(self, user_id):
        """La stanza della partita in corso di quell'utente, o None."""
        with self._lock:
            return self._room_of(user_id)

    def _room_of(self, user_id):
        for room in self._rooms.values():
            if room.game is not None and not room.finished and room.has_member(user_id):
                return room
        return None

    def get(self, room_id):
        with self._lock:
            return self._rooms.get(room_id) if isinstance(room_id, str) else None

    def remove(self, room_id):
        with self._lock:
            return self._rooms.pop(room_id, None)

    def rooms_of(self, user_id):
        with self._lock:
            rooms = list(self._rooms.values())
        return [room for room in rooms if room.has_member(user_id)]

    def __len__(self):
        with self._lock:
            return len(self._rooms)


rooms = RoomManager()
create_room = rooms.create_room
find_room_of_user = rooms.find_room_of_user
