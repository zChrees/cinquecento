"""Chi è online (P44): utente -> schede collegate in tempo reale, in memoria.

- Un utente è online se ha almeno una scheda collegata; con due schede conta una volta
  sola (contratto 5.1, `online_count`).
- Le schede le aggiunge e le toglie connection_events.py, al collegamento e allo
  scollegamento. `add` e `remove` dicono se l'utente è appena entrato o uscito: solo
  allora cambia il numero di utenti online.
- Lo usano la home (home_events.py) e la coda (chi chiude l'ultima scheda esce, P28);
  servirà anche a P47 per il pallino degli amici.
Un solo processo (DECISIONI.md): basta un dizionario sotto un lock.

Cosa contiene:
    Presence                 l'elenco degli utenti online e delle loro schede
    presence                 l'unico elenco del programma, per esempio presence.count() = 3
    disconnect_user(user_id) scollega tutte le schede di un utente

Una "scheda" è identificata dal suo sid ("session id"), il codice che Socket.IO dà a
ogni collegamento, per esempio "Xk3...": la stessa persona con due schede aperte ha
due sid.

DA DOVE ARRIVANO I DATI: connection_events.py chiama add e remove; la home, la coda,
gli amici e gli inviti chiedono chi è online; disconnect_user la chiamano il logout
(app/blueprints/auth/api.py) e la cancellazione dell'account.
"""

import threading

from app.extensions import socketio


class Presence:
    """L'elenco degli utenti online, con le loro schede.

    In parole semplici:
        presence.add(7, "sid1")    l'utente 7 ha aperto una scheda
        presence.is_online(7)      True
        presence.remove(7, "sid1") l'ha chiusa: True, perché era l'ultima
        Ogni metodo prende il lucchetto: più thread lo usano insieme senza problemi.
    """

    def __init__(self):
        """Crea l'elenco vuoto.

        In parole semplici:
            Presence()
            _tabs è un dizionario user_id -> insieme (set) dei sid delle sue schede,
            per esempio {7: {"sid1", "sid2"}, 12: {"sid3"}}.
        """
        # _lock: un "lucchetto" (come un mutex in C): con "with self._lock:" un solo
        # thread alla volta legge o cambia _tabs
        self._lock = threading.Lock()
        self._tabs = {}  # user_id -> set di sid

    def add(self, user_id, sid):
        """Segna la scheda `sid` collegata; True se l'utente prima non era online.

        In parole semplici:
            add(user_id, sid)
            user_id: il numero dell'utente, per esempio 7.
            sid:     il codice della scheda. Arrivano da on_connect di connection_events.py.
            Restituisce True se è la sua prima scheda (è appena entrato), False se ne
            aveva già altre.
        """
        with self._lock:
            # setdefault: se l'utente non c'è, gli mette un insieme vuoto; poi lo restituisce
            tabs = self._tabs.setdefault(user_id, set())
            # un insieme vuoto vale "falso": was_offline è True se non aveva schede
            was_offline = len(tabs) == 0
            tabs.add(sid)
            return was_offline

    def remove(self, user_id, sid):
        """Toglie la scheda `sid`; True se era l'ultima (l'utente è uscito).

        In parole semplici:
            remove(user_id, sid)
            Arrivano da on_disconnect di connection_events.py.
            Restituisce True solo se, tolta questa scheda, l'utente non ne ha più;
            False se ne ha ancora o se la scheda non era nell'elenco.
        """
        with self._lock:
            tabs = self._tabs.get(user_id)
            if not tabs or sid not in tabs:
                return False
            tabs.discard(sid)
            if len(tabs) > 0:
                return False
            del self._tabs[user_id]
            return True

    def is_online(self, user_id):
        """True se l'utente ha almeno una scheda collegata.

        In parole semplici:
            is_online(7)
            La usano gli amici (il pallino verde) e gli inviti (offline).
        """
        with self._lock:
            return user_id in self._tabs

    def online_users(self):
        """I numeri degli utenti online, in una lista nuova.

        In parole semplici:
            online_users()
            Per esempio [7, 12]. È una copia: chi la usa non tocca _tabs fuori dal lucchetto.
        """
        with self._lock:
            return list(self._tabs)

    def count(self):
        """Quanti utenti sono online (non quante schede).

        In parole semplici:
            count()
            Per esempio 2 con l'utente 7 in due schede e il 12 in una. È il numero
            "giocatori online" della home.
        """
        with self._lock:
            return len(self._tabs)

    def tabs_of(self, user_id):
        """I sid delle schede di un utente, in una lista nuova (vuota se non è online).

        In parole semplici:
            tabs_of(7)
            Per esempio ["sid1", "sid2"]. La usa disconnect_user, qui sotto.
        """
        with self._lock:
            return list(self._tabs.get(user_id, ()))


# presence: l'unico elenco del programma (un solo processo)
presence = Presence()


def disconnect_user(user_id):
    """Scollega tutte le schede di quell'utente (P32: "Esci" e cancellazione dell'account).

    Ogni scollegamento passa da connection_events.on_disconnect, come quando si chiude
    una scheda: con l'ultima l'utente esce dalla coda e i suoi inviti si annullano, e al
    tavolo parte il tempo per rientrare. Va chiamata quando l'utente ha ancora il login:
    on_disconnect fa la pulizia solo per un utente riconosciuto. Il client Socket.IO non
    si ricollega da solo dopo uno scollegamento deciso dal server.

    In parole semplici:
        disconnect_user(user_id)
        user_id: il numero dell'utente che esce o cancella l'account. Arriva dal
        logout e dalla cancellazione dell'account, prima di logout_user.
    """
    for sid in presence.tabs_of(user_id):
        socketio.server.disconnect(sid, namespace="/")
