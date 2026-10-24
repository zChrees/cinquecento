"""Elenco delle stanze attive, in memoria (P23, P24). Un solo processo (DECISIONI.md): basta un dizionario.

Il lock del manager protegge solo l'elenco (creare, trovare, togliere una stanza);
quello che succede dentro una stanza passa dal lock della stanza (room.py).

Funzioni esposte da P24, che altri punti usano senza modificare questo file:
- create_room(giocatori, modalità, punteggio): per la coda (P28, P29) e gli inviti (P47);
- find_room_of_user(user_id): per il rientro in partita (P44).

P68: create_room(..., cpu_seats=(1,)) crea la partita contro la CPU (il giocatore
CPU_PLAYER di room.py a quei posti): la CPU può essere in più partite insieme.
P122 (D49): nel 2v2 le CPU sono tre, tutte con user_id 0: il controllo "stesso giocatore
in due posti" guarda solo i giocatori veri.

P88: create_room legge una volta sola il rating di ogni giocatore vero nella modalità
della partita (gli stessi numeri del pannello statistiche, stats_service.stats_of) e
la stanza lo mette nella vista; serve il contesto di Flask, come per il salvataggio (P26).

Cosa contiene:
    RoomError                  l'errore di create_room, per esempio RoomError("Già in partita: Mario.")
    RoomManager                l'elenco delle stanze, con il suo lucchetto
    rooms                      l'unico elenco del programma
    create_room(...)           crea una stanza e fa partire la partita (= rooms.create_room)
    find_room_of_user(user_id) la stanza della partita in corso di un utente, o None

DA DOVE ARRIVANO I DATI: la coda (matchmaking.py), gli inviti (friends_events.py) e la
CPU (lobby_events.py) chiamano create_room con i giocatori; game_events.py cerca la
stanza con rooms.get(game_id) a ogni evento del tavolo; la home e il rientro usano
find_room_of_user.
"""

import logging
import secrets
import threading

# has_app_context: True se si è "dentro Flask" (in un evento o in una richiesta),
# dove si può usare il database
from flask import has_app_context

from app.extensions import socketio
from app.game.engine.errors import EngineError
from app.realtime import room as room_module
from app.realtime.events import user_channel
from app.realtime.room import MODES, Player, Room
from app.services import stats_service

log = logging.getLogger(__name__)


# RoomError eredita da ValueError: chi la prende con "except ValueError" la prende lo stesso
class RoomError(ValueError):
    """create_room rifiutata: giocatori, modalità o punteggio non validi, o un giocatore già in partita."""


class RoomManager:
    """L'elenco delle stanze attive: codice della stanza -> Room.

    In parole semplici:
        rooms.create_room(giocatori, "1v1", 300)   crea e avvia una partita
        rooms.get("abc")                           la stanza con quel codice, o None
        rooms.rooms_of(7)                          le stanze dell'utente 7, anche finite
    """

    def __init__(self):
        """Crea l'elenco vuoto.

        In parole semplici:
            RoomManager()
            _rooms è un dizionario codice -> Room; _lock lo protegge (vedi sotto).
        """
        # _lock: un "lucchetto" (come un mutex in C): con "with self._lock:" un solo
        # thread alla volta legge o cambia l'elenco
        self._lock = threading.Lock()
        self._rooms = {}

    def _new_id(self):
        """Un codice nuovo per una stanza, che non c'è già nell'elenco.

        In parole semplici:
            _new_id()
            Per esempio "q3Zr_8kLmP1x": 9 byte a caso scritti come testo per gli
            indirizzi (token_urlsafe), difficile da indovinare. Si chiama con il
            lucchetto già preso, da create e create_room.
        """
        room_id = secrets.token_urlsafe(9)
        while room_id in self._rooms:
            room_id = secrets.token_urlsafe(9)
        return room_id

    def create(self):
        """Crea una stanza vuota con un codice nuovo, difficile da indovinare (è il game_id del contratto).

        In parole semplici:
            create()
            Una stanza senza partita. La usano solo i test (P23); il programma usa
            create_room, qui sotto.
        """
        with self._lock:
            room = Room(self._new_id())
            self._rooms[room.id] = room
            return room

    def create_room(self, players, mode, target_score, rated=True, rng=None, announce=True, cpu_seats=()):
        """Crea la stanza e fa partire la partita; ogni giocatore riceve game:start (contratto 3.2).

        `players` in ordine di posto: nel 2v2 i posti 0 e 2 sono una squadra, 1 e 3 l'altra
        (contratto 3.1). Accetta oggetti Player o utenti (User). `rated` è False solo nel
        1v1 contro un amico (D36). Un giocatore già in una partita in corso → RoomError.
        `cpu_seats` (P68): i posti giocati dalla CPU, che non riceve game:start.

        In parole semplici:
            create_room(players, mode, target_score)
            players:      i giocatori in ordine di posto, per esempio [mario, lucia].
            mode:         "1v1" o "2v2".
            target_score: i punti per vincere, 150, 300 o 500 (li controlla il motore).
            rated:        facoltativo (se manca True): se la partita conta per il rating.
            rng:          facoltativo, il generatore di numeri a caso (i test lo fissano).
            announce:     facoltativo (se manca True): se mandare game:start ai giocatori.
            cpu_seats:    facoltativo (se manca nessuno): i posti della CPU, per esempio (1,).
            Arrivano dalla coda, dagli inviti o dalla partita contro la CPU.

            Va chiamata dentro Flask (P26, P88): la stanza si ricorda l'app per salvare
            la partita a fine gioco, e il rating si legge dal database.
            Restituisce la stanza (Room), già con la partita avviata.
        """
        if mode not in MODES:
            raise RoomError(f'Modalità non valida: "{mode}".')

        # players: ognuno trasformato in Player (Player.of accetta anche un utente User)
        player_list = []
        for player in players:
            player_list.append(Player.of(player))
        players = tuple(player_list)
        if len(players) != MODES[mode]:
            raise RoomError(f"Nel {mode} servono {MODES[mode]} giocatori, non {len(players)}.")

        # humans: i numeri dei giocatori veri (non la CPU, che ha sempre user_id 0);
        # se nell'insieme sono meno che nella lista, qualcuno compare due volte
        humans = []
        for seat in range(len(players)):
            if seat not in cpu_seats:
                humans.append(players[seat].user_id)
        if len(set(humans)) != len(humans):
            raise RoomError("Lo stesso giocatore non può avere due posti.")

        ratings = _ratings_of(players, mode, cpu_seats)  # database: prima del lock dell'elenco
        with self._lock:
            # busy: i nomi dei giocatori veri che sono già in un'altra partita in corso
            busy = []
            for seat in range(len(players)):
                player = players[seat]
                if seat not in cpu_seats and self._room_of(player.user_id) is not None:
                    busy.append(player.username)
            if len(busy) > 0:
                raise RoomError(f"Già in partita: {', '.join(busy)}.")

            room = Room(self._new_id())
            try:
                room.start(players, target_score, rated=rated, rng=rng, cpu_seats=cpu_seats, ratings=ratings)
            except EngineError as exc:
                # "from None": il nuovo errore non si porta dietro quello del motore nel log
                raise RoomError(str(exc)) from None
            self._rooms[room.id] = room

        # Fuori dal lucchetto: gli avvisi di inizio partita (P47) e game:start a ogni giocatore vero
        room_module.notify(room_module.start_listeners, room.human_ids, room._app)  # P47
        if announce:
            for user_id in room.human_ids:
                socketio.emit("game:start", {"game_id": room.id, "url": f"/game/{room.id}"},
                              to=user_channel(user_id))
        return room

    def find_room_of_user(self, user_id):
        """La stanza della partita in corso di quell'utente, o None.

        In parole semplici:
            find_room_of_user(7)
            La usano la home (l'avviso "Rientra", P44), la coda e gli inviti di
            friend_service.py (chi è già in partita non può entrare in un'altra) e la
            cancellazione dell'account (auth_service.py: non si cancella a metà partita).
        """
        with self._lock:
            return self._room_of(user_id)

    def _room_of(self, user_id):
        """Come find_room_of_user, ma con il lucchetto già preso da chi la chiama.

        In parole semplici:
            _room_of(user_id)
            Scorre tutte le stanze (una ricerca lineare) e restituisce la prima con una
            partita avviata, non finita, di cui l'utente è giocatore; None se non c'è.
        """
        for room in self._rooms.values():
            if room.game is not None and not room.finished and room.has_member(user_id):
                return room
        return None

    def get(self, room_id):
        """La stanza con quel codice, o None.

        In parole semplici:
            get("abc")
            room_id: il codice mandato dalla pagina (game_id). Se non è un testo la
            risposta è None, senza errore. La usa game_events.py a ogni evento del tavolo.
        """
        with self._lock:
            if not isinstance(room_id, str):
                return None
            return self._rooms.get(room_id)

    def remove(self, room_id):
        """Toglie la stanza dall'elenco e la restituisce (None se non c'era).

        In parole semplici:
            remove("abc")
            Nota: oggi la chiamano solo i test; le stanze finite restano in memoria
            finché il server non si riavvia (R4 di REVIEW.md).
        """
        with self._lock:
            # pop: toglie la chiave e restituisce il valore; None se la chiave non c'è
            return self._rooms.pop(room_id, None)

    def rooms_of(self, user_id):
        """Tutte le stanze di cui l'utente è giocatore, anche finite.

        In parole semplici:
            rooms_of(7)
            Prima copia l'elenco con il lucchetto, poi lo scorre senza: has_member di
            ogni stanza prende il lucchetto della stanza, e tenerne due insieme
            potrebbe bloccare due thread a vicenda.
        """
        with self._lock:
            all_rooms = list(self._rooms.values())
        result = []
        for room in all_rooms:
            if room.has_member(user_id):
                result.append(room)
        return result

    def __len__(self):
        """Quante stanze ci sono: len(rooms) chiama questa funzione."""
        with self._lock:
            return len(self._rooms)


def _ratings_of(players, mode, cpu_seats):
    """Per posto, il rating del giocatore in quella modalità ({"value", "provisional"}, P88),
    None per la CPU. Fuori da Flask, o se il database non risponde, None per tutti: la
    partita parte lo stesso, senza rating al tavolo.

    In parole semplici:
        _ratings_of(players, mode, cpu_seats)
        Arrivano da create_room. Restituisce per esempio
        ({"value": 1520, "provisional": False}, None) nel 1v1 contro la CPU, oppure None.
    """
    if not has_app_context():
        return None
    try:
        ratings = []
        for seat in range(len(players)):
            if seat in cpu_seats:
                ratings.append(None)
                continue
            rating = stats_service.stats_of(players[seat].user_id)["ratings"][mode]
            ratings.append({"value": rating["value"], "provisional": rating["provisional"]})
        return tuple(ratings)
    except Exception:
        # nel log solo i numeri degli utenti, mai i loro dati
        user_ids = []
        for player in players:
            user_ids.append(player.user_id)
        log.exception("Rating dei giocatori %s non letti", user_ids)
        return None


# rooms: l'unico elenco del programma; create_room e find_room_of_user sono le sue
# funzioni, con un nome corto da importare (from app.realtime.room_manager import create_room)
rooms = RoomManager()
create_room = rooms.create_room
find_room_of_user = rooms.find_room_of_user
