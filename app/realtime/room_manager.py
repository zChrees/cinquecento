"""Elenco delle stanze attive, in memoria (P23). Un solo processo (DECISIONI.md): basta un dizionario.

Il lock del manager protegge solo l'elenco (creare, trovare, togliere una stanza);
quello che succede dentro una stanza passa dal lock della stanza (room.py).
"""

import secrets
import threading

from app.realtime.room import Room


class RoomManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._rooms = {}

    def create(self):
        """Crea una stanza con un codice nuovo, difficile da indovinare (è il game_id del contratto)."""
        with self._lock:
            room_id = secrets.token_urlsafe(9)
            while room_id in self._rooms:
                room_id = secrets.token_urlsafe(9)
            room = self._rooms[room_id] = Room(room_id)
            return room

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
