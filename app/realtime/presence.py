"""Chi è online (P44): utente -> schede collegate in tempo reale, in memoria.

- Un utente è online se ha almeno una scheda collegata; con due schede conta una volta
  sola (contratto 5.1, `online_count`).
- Le schede le aggiunge e le toglie connection_events.py, al collegamento e allo
  scollegamento. `add` e `remove` dicono se l'utente è appena entrato o uscito: solo
  allora cambia il numero di utenti online.
- Lo usano la home (home_events.py) e la coda (chi chiude l'ultima scheda esce, P28);
  servirà anche a P47 per il pallino degli amici.
Un solo processo (DECISIONI.md): basta un dizionario sotto un lock.
"""

import threading


class Presence:
    def __init__(self):
        self._lock = threading.Lock()
        self._tabs = {}  # user_id -> set di sid

    def add(self, user_id, sid):
        """Segna la scheda `sid` collegata; True se l'utente prima non era online."""
        with self._lock:
            tabs = self._tabs.setdefault(user_id, set())
            was_offline = not tabs
            tabs.add(sid)
            return was_offline

    def remove(self, user_id, sid):
        """Toglie la scheda `sid`; True se era l'ultima (l'utente è uscito)."""
        with self._lock:
            tabs = self._tabs.get(user_id)
            if not tabs or sid not in tabs:
                return False
            tabs.discard(sid)
            if tabs:
                return False
            del self._tabs[user_id]
            return True

    def is_online(self, user_id):
        with self._lock:
            return user_id in self._tabs

    def online_users(self):
        with self._lock:
            return list(self._tabs)

    def count(self):
        with self._lock:
            return len(self._tabs)


presence = Presence()
