"""Stanza in memoria (P23): chi c'è dentro e il lock che mette in fila i suoi eventi.

Regola (CLAUDE.md, "Stanze di gioco"): ogni evento di una stanza si elabora sotto
il lock di quella stanza, e timer e mosse passano dalla stessa via, `room.run(...)`.
La partita vera (motore, vista, version) la aggiunge P24.
"""

import threading

from app.realtime.events import room_channel


class Room:
    def __init__(self, room_id):
        self.id = room_id
        self.channel = room_channel(room_id)
        self.lock = threading.RLock()
        self.members = set()  # user_id dei giocatori

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
