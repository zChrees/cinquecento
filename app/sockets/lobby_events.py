"""Entrata e uscita dalle code di matchmaking (P28, P29; contratto 4): queue:join, queue:leave.
P68: cpu:start, la partita contro la CPU (P122: anche nel 2v2).

- Tutto quello che arriva dalla pagina si controlla qui: un dato non valido si rifiuta
  con `invalid_data`, senza correzioni.
- queue:join porta `request_id` (contratto 1.3): lo stesso tentativo ripetuto riceve la
  risposta della prima volta (RecentRequests di P45), senza entrare in coda due volte.
- R7 (REVIEW.md): queue:join gira sotto il lock degli inviti, come cpu:start e
  invite:start, e risponde `busy` anche con un invito aperto.
- queue:join mette in coda un giocatore singolo, nel 1v1 o nel 2v2 (P29). La coppia
  già formata (l'amico compagno nel 2v2) non passa da qui: entra con invite:start (P47),
  che chiama matchmaker.join_pair.
- Annullare da un giocatore della coppia fa uscire tutta la coppia (partner_left).
- La coda e gli abbinamenti stanno in app/realtime/matchmaking.py.
- cpu:start `{"request_id", "target_score", "mode"}` (P68, D43; P122, D49: `mode`
  obbligatorio come in queue:join): crea subito la partita, senza rating e senza
  salvataggio; arriva game:start come dalla coda. Tu sei sempre al posto 0 (chi comincia
  lo tira a sorte il motore). Nel 1v1 la CPU è all'1; nel 2v2 "CPU 1", la compagna, è al
  2 (di fronte), "CPU 2" all'1 e "CPU 3" al 3. Tutte le CPU hanno user_id 0 (D49): la
  pagina le riconosce da `cpu`. `busy` se l'utente è già in coda, in partita o ha un
  invito aperto. Gira sotto il lock degli inviti, come invite:start: un invito non si
  apre mentre la partita parte.

Cosa contiene:
    on_join(data)        queue:join, entra in coda
    on_leave(data)       queue:leave, esce dalla coda
    _join_queue(...)     l'ingresso in coda sotto il lock degli inviti (R7)
    on_cpu_start(data)   cpu:start, partita contro la CPU
    register(socketio)   registra i tre gestori

DA DOVE ARRIVANO I DATI: dalla carta-modal della Partita Veloce nella home
(frontend/src/components/ModeModal.tsx e HomePage.tsx), che manda request_id, mode e
target_score.
"""

# replace: una copia di una dataclass "congelata" con alcuni campi cambiati
from dataclasses import replace

from flask import current_app, request
from flask_login import current_user

from app.realtime.events import EventError, handler
from app.realtime.invites import invites
from app.realtime.matchmaking import matchmaker
from app.realtime.room import CPU_PLAYER, Player
from app.realtime.room_manager import RoomError, create_room
from app.services.friend_service import RecentRequests
from config import BaseConfig

REQUEST_ID_MAX = 100
MODES = ("1v1", "2v2")

# recent: le risposte date di recente, per chiave anti-doppione (request_id)
recent = RecentRequests()

# P122 (D49): i posti delle CPU per modalità, con i nomi; il giocatore vero è al posto 0
CPU_NAMES = {
    "1v1": {1: "CPU"},
    "2v2": {1: "CPU 2", 2: "CPU 1", 3: "CPU 3"},  # CPU 1 è la compagna, di fronte
}


def _join_data(data):
    """`request_id`, `mode` e `target_score`, comuni a queue:join e cpu:start (P122).

    In parole semplici:
        _join_data(data)
        data: quello che ha mandato la pagina, per esempio
              {"request_id": "a1b2", "mode": "1v1", "target_score": 300}.
        Restituisce i tre valori controllati, in una tupla (request_id, mode, target_score);
        un valore non valido si rifiuta con invalid_data.
    """
    checked = _request(data)
    request_id = checked[0]
    target_score = checked[1]
    mode = data.get("mode")
    if not isinstance(mode, str) or mode not in MODES:
        raise EventError("invalid_data", "Modalità non valida.")
    return request_id, mode, target_score


def _request(data):
    """`request_id` e `target_score`.

    In parole semplici:
        _request(data)
        request_id: un testo da 1 a REQUEST_ID_MAX caratteri (la chiave anti-doppione).
        target_score: un intero tra i punteggi ammessi (TARGET_SCORES di config.py);
        True e False si rifiutano anche se in Python sono numeri.
        Restituisce la tupla (request_id, target_score).
    """
    if not isinstance(data, dict):
        raise EventError("invalid_data", "Richiesta non valida.")
    request_id = data.get("request_id")
    if not isinstance(request_id, str) or len(request_id) < 1 or len(request_id) > REQUEST_ID_MAX:
        raise EventError("invalid_data", "Richiesta non valida.")
    target_score = data.get("target_score")
    if (not isinstance(target_score, int) or isinstance(target_score, bool)
            or target_score not in BaseConfig.TARGET_SCORES):
        raise EventError("invalid_data", "Punti per vincere non validi.")
    return request_id, target_score


# @handler (app/realtime/events.py): controlla login e limite di frequenza e
# trasforma quello che il gestore restituisce nella risposta del contratto
@handler
def on_join(data=None):
    """queue:join: entra nella coda della Partita Veloce.

    In parole semplici:
        Controlla i dati, poi chiede a recent di eseguire join_queue una volta sola per
        quel request_id: lo stesso tentativo ripetuto (doppio clic, rete lenta) riceve
        la stessa risposta. Restituisce lo stato della coda (queue:status).
    """
    checked = _join_data(data)
    request_id = checked[0]
    mode = checked[1]
    target_score = checked[2]
    # _get_current_object: l'utente e l'app veri, non i "segnaposto" di Flask, che
    # funzionano solo durante la richiesta
    user = current_user._get_current_object()
    sid = request.sid
    app = current_app._get_current_object()

    def join_queue():
        """L'ingresso vero in coda (lo chiama recent.run, se il tentativo è nuovo)."""
        return _join_queue(app, user, mode, target_score, sid)

    return recent.run(user.id, "queue:join", request_id, join_queue)


def _join_queue(app, user, mode, target_score, sid):
    """L'ingresso in coda, sotto il lucchetto degli inviti (R7 di REVIEW.md).

    In parole semplici:
        _join_queue(app, user, mode, target_score, sid)
        Come cpu:start e invite:start, gira con invites.lock preso: così queue:join e
        cpu:start mandati insieme da due schede passano uno alla volta, e il secondo vede
        quello che ha fatto il primo (in partita o in coda: busy). Prima queue:join
        controllava "non in partita" senza lucchetto, e l'utente poteva finire in coda e
        in partita insieme. Con un invito aperto (mandato o ricevuto) risponde busy, come
        dice il contratto (busy: "in partita, in coda o ha un invito in sospeso").
        Restituisce lo stato della coda (matchmaker.join).
    """
    with invites.lock:
        if invites.open_of(user.id) is not None:
            raise EventError("busy", "Hai un invito aperto: annullalo prima di cercare una partita.")
        return matchmaker.join(app, user, mode, target_score, sid)


@handler
def on_leave(data=None):
    """Annulla: risponde ok anche se l'utente non era in coda (contratto 4).

    In parole semplici:
        queue:leave non ha dati; con una coppia esce anche il compagno (partner_left).
    """
    matchmaker.leave(current_user.id)


@handler
def on_cpu_start(data=None):
    """Partita contro la CPU (P68, P122): risponde ok con `{"game_id"}`.

    In parole semplici:
        Come on_join, con la stessa chiave anti-doppione; la partita la crea _start_cpu.
    """
    checked = _join_data(data)
    request_id = checked[0]
    mode = checked[1]
    target_score = checked[2]
    user = current_user._get_current_object()

    def start():
        """La partita vera (la chiama recent.run, se il tentativo è nuovo)."""
        return _start_cpu(user, mode, target_score)

    return recent.run(user.id, "cpu:start", request_id, start)


def _start_cpu(user, mode, target_score):
    """Crea la partita contro la CPU: l'utente al posto 0, le CPU agli altri.

    In parole semplici:
        _start_cpu(user, mode, target_score)
        Per ogni posto di CPU_NAMES[mode], in ordine (sorted), una copia di CPU_PLAYER
        con il suo nome. Con il lucchetto degli inviti: chi è in coda o ha un invito
        aperto non può iniziare. Restituisce {"game_id": "..."}.
    """
    names = CPU_NAMES[mode]
    players = [Player.of(user)]
    for seat in sorted(names):
        players.append(replace(CPU_PLAYER, username=names[seat]))
    with invites.lock:
        if user.id in matchmaker.queue:
            raise EventError("busy", "Sei già in coda: annulla la ricerca prima di giocare contro la CPU.")
        if invites.open_of(user.id) is not None:
            raise EventError("busy", "Hai un invito aperto: annullalo prima di giocare contro la CPU.")
        try:
            # tuple(names): i posti delle CPU, cioè le chiavi del dizionario, per esempio (1,)
            room = create_room(players, mode, target_score, rated=False, cpu_seats=tuple(names))
        except RoomError:
            raise EventError("busy", "Sei già in partita.") from None
    return {"game_id": room.id}


def register(socketio):
    """Registra i gestori di queue:join, queue:leave e cpu:start."""
    socketio.on_event("queue:join", on_join)
    socketio.on_event("queue:leave", on_leave)
    socketio.on_event("cpu:start", on_cpu_start)
