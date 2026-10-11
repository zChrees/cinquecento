"""Entrata e uscita dalle code di matchmaking (P28, P29; contratto 4): queue:join, queue:leave.
P68: cpu:start, la partita contro la CPU (P122: anche nel 2v2).

- Tutto quello che arriva dalla pagina si controlla qui: un dato non valido si rifiuta
  con `invalid_data`, senza correzioni.
- queue:join porta `request_id` (contratto 1.3): lo stesso tentativo ripetuto riceve la
  risposta della prima volta (RecentRequests di P45), senza entrare in coda due volte.
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
"""

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

recent = RecentRequests()

# P122 (D49): i posti delle CPU per modalità, con i nomi; il giocatore vero è al posto 0
CPU_NAMES = {
    "1v1": {1: "CPU"},
    "2v2": {1: "CPU 2", 2: "CPU 1", 3: "CPU 3"},  # CPU 1 è la compagna, di fronte
}


def _join_data(data):
    """`request_id`, `mode` e `target_score`, comuni a queue:join e cpu:start (P122)."""
    request_id, target_score = _request(data)
    mode = data.get("mode")
    if not isinstance(mode, str) or mode not in MODES:
        raise EventError("invalid_data", "Modalità non valida.")
    return request_id, mode, target_score


def _request(data):
    """`request_id` e `target_score`."""
    if not isinstance(data, dict):
        raise EventError("invalid_data", "Richiesta non valida.")
    request_id = data.get("request_id")
    if not isinstance(request_id, str) or not 1 <= len(request_id) <= REQUEST_ID_MAX:
        raise EventError("invalid_data", "Richiesta non valida.")
    target_score = data.get("target_score")
    if (not isinstance(target_score, int) or isinstance(target_score, bool)
            or target_score not in BaseConfig.TARGET_SCORES):
        raise EventError("invalid_data", "Punti per vincere non validi.")
    return request_id, target_score


@handler
def on_join(data=None):
    request_id, mode, target_score = _join_data(data)
    user, sid, app = current_user._get_current_object(), request.sid, current_app._get_current_object()
    return recent.run(user.id, "queue:join", request_id,
                      lambda: matchmaker.join(app, user, mode, target_score, sid))


@handler
def on_leave(data=None):
    """Annulla: risponde ok anche se l'utente non era in coda (contratto 4)."""
    matchmaker.leave(current_user.id)


@handler
def on_cpu_start(data=None):
    """Partita contro la CPU (P68, P122): risponde ok con `{"game_id"}`."""
    request_id, mode, target_score = _join_data(data)
    user = current_user._get_current_object()
    return recent.run(user.id, "cpu:start", request_id, lambda: _start_cpu(user, mode, target_score))


def _start_cpu(user, mode, target_score):
    names = CPU_NAMES[mode]
    players = [Player.of(user)] + [replace(CPU_PLAYER, username=names[seat]) for seat in sorted(names)]
    with invites.lock:
        if user.id in matchmaker.queue:
            raise EventError("busy", "Sei già in coda: annulla la ricerca prima di giocare contro la CPU.")
        if invites.open_of(user.id) is not None:
            raise EventError("busy", "Hai un invito aperto: annullalo prima di giocare contro la CPU.")
        try:
            room = create_room(players, mode, target_score, rated=False, cpu_seats=tuple(names))
        except RoomError:
            raise EventError("busy", "Sei già in partita.") from None
    return {"game_id": room.id}


def register(socketio):
    socketio.on_event("queue:join", on_join)
    socketio.on_event("queue:leave", on_leave)
    socketio.on_event("cpu:start", on_cpu_start)
