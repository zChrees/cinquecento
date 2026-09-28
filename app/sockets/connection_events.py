"""Collegamento e scollegamento (P23).

Si collega solo chi ha fatto il login: gli altri ricevono l'errore di connessione
con il messaggio `not_logged_in` (contratto 1.4). Ogni scheda entra nel canale del
suo utente, così il server può scrivere a tutte le schede di quell'utente.
Nei log solo il numero dell'utente, mai dati personali.

P25: se la scheda che si scollega era quella al tavolo di una partita, il suo posto
risulta scollegato, gli altri ricevono la vista nuova e parte il tempo per rientrare
(room.disconnect).
"""

import logging

from flask import request
from flask_login import current_user
from flask_socketio import ConnectionRefusedError, join_room

from app.realtime.events import NOT_LOGGED_IN, user_channel
from app.realtime.room_manager import rooms

log = logging.getLogger(__name__)


def on_connect(auth=None):
    if not current_user.is_authenticated:
        raise ConnectionRefusedError(NOT_LOGGED_IN)
    join_room(user_channel(current_user.id))
    log.info("Collegato l'utente %s (connessione %s)", current_user.id, request.sid)


def on_disconnect(reason=None):
    if current_user.is_authenticated:
        log.info("Scollegato l'utente %s (connessione %s)", current_user.id, request.sid)
        for room in rooms.rooms_of(current_user.id):
            room.run(_leave_table, room, request.sid)


def _leave_table(room, sid):
    """Sotto il lock della stanza: se `sid` era al tavolo, gli altri vedono il posto scollegato."""
    if room.disconnect(sid) is not None:
        room.broadcast_states()


def register(socketio):
    socketio.on_event("connect", on_connect)
    socketio.on_event("disconnect", on_disconnect)
