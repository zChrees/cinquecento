"""Collegamento e scollegamento (P23).

Si collega solo chi ha fatto il login: gli altri ricevono l'errore di connessione
con il messaggio `not_logged_in` (contratto 1.4). Ogni scheda entra nel canale del
suo utente, così il server può scrivere a tutte le schede di quell'utente.
Nei log solo il numero dell'utente, mai dati personali.

P25: se la scheda che si scollega era quella al tavolo di una partita, il suo posto
risulta scollegato, gli altri ricevono la vista nuova e parte il tempo per rientrare
(room.disconnect).

P28: una scheda che si collega mentre l'utente è in coda riceve subito queue:status;
chi chiude la sua ultima scheda esce dalla coda (scelta di Giuseppe), così non viene
abbinato a una partita a cui non arriverebbe.

P44: ogni scheda collegata entra in presence.py; appena collegata riceve home:status.
Quando un utente entra online (prima scheda) o esce (ultima scheda), tutti gli altri
utenti collegati ricevono home:status con il numero nuovo.

P47: in quei due momenti anche gli amici collegati ricevono friends:presence; chi
chiude l'ultima scheda perde i suoi inviti aperti ("cancelled").

Cosa contiene:
    on_connect(auth)        una scheda si collega
    on_disconnect(reason)   una scheda si scollega
    register(socketio)      registra i due gestori

DA DOVE ARRIVANO I DATI: Socket.IO chiama on_connect e on_disconnect da solo, quando
il browser apre o chiude il collegamento (in frontend/src/socket/client.ts). L'utente
è quello del login (current_user di Flask-Login), la scheda è request.sid.
"""

import logging

from flask import request
from flask_login import current_user
from flask_socketio import ConnectionRefusedError, emit, join_room

from app.realtime.events import NOT_LOGGED_IN, user_channel
from app.realtime.invites import invites
from app.realtime.matchmaking import matchmaker
from app.realtime.presence import presence
from app.realtime.room_manager import rooms
from app.sockets import friends_events, home_events

log = logging.getLogger(__name__)


def on_connect(auth=None):
    """Una scheda si collega al tempo reale.

    In parole semplici:
        on_connect(auth)
        auth: facoltativo, i dati che il client manda al collegamento (qui non si usano).
        1. senza login il collegamento si rifiuta (ConnectionRefusedError);
        2. la scheda entra nel canale del suo utente e in presence;
        3. riceve subito home:status; se l'utente è appena entrato online, lo sanno
           anche gli altri utenti e i suoi amici;
        4. se l'utente è in coda, la scheda riceve anche queue:status.
        emit (senza "to") manda l'evento solo a questa scheda.
    """
    if not current_user.is_authenticated:
        raise ConnectionRefusedError(NOT_LOGGED_IN)
    join_room(user_channel(current_user.id))
    log.info("Collegato l'utente %s (connessione %s)", current_user.id, request.sid)
    # arrived: True se è la prima scheda dell'utente (è appena entrato online)
    arrived = presence.add(current_user.id, request.sid)
    emit("home:status", home_events.home_status(current_user.id))
    if arrived:
        home_events.broadcast_status(exclude=current_user.id)
        friends_events.notify_presence([current_user.id])
    queue = matchmaker.queue.status(current_user.id)
    if queue is not None:
        emit("queue:status", queue)


def on_disconnect(reason=None):
    """Una scheda si scollega (chiusa, rete persa, o scollegata dal server).

    In parole semplici:
        on_disconnect(reason)
        reason: facoltativo, il motivo dato da Socket.IO (qui non si usa).
        1. la scheda si toglie da presence, per prima cosa;
        2. se era al tavolo di una partita, il suo posto risulta scollegato;
        3. se era l'ultima scheda dell'utente: esce dalla coda, i suoi inviti si
           annullano, gli altri utenti e i suoi amici lo vedono uscire.
        Senza login (per esempio un account appena cancellato) non fa niente.
    """
    if current_user.is_authenticated:
        log.info("Scollegato l'utente %s (connessione %s)", current_user.id, request.sid)
        last_tab = presence.remove(current_user.id, request.sid)  # per primo: un errore dopo non lo lascia online
        for room in rooms.rooms_of(current_user.id):
            room.run(_leave_table, room, request.sid)
        if last_tab:
            matchmaker.leave(current_user.id, reason="cancelled")
            invites.cancel_all_of(current_user.id)
            home_events.broadcast_status()
            friends_events.notify_presence([current_user.id])


def _leave_table(room, sid):
    """Sotto il lock della stanza: se `sid` era al tavolo, gli altri vedono il posto scollegato.

    In parole semplici:
        _leave_table(room, sid)
        La chiama on_disconnect con room.run, per ogni stanza dell'utente.
    """
    if room.disconnect(sid) is not None:
        room.broadcast_states()


def register(socketio):
    """Registra i gestori di "connect" e "disconnect" (gli eventi del collegamento)."""
    socketio.on_event("connect", on_connect)
    socketio.on_event("disconnect", on_disconnect)
