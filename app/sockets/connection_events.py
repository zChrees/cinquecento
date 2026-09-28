"""Collegamento e scollegamento (P23).

Si collega solo chi ha fatto il login: gli altri ricevono l'errore di connessione
con il messaggio `not_logged_in` (contratto 1.4). Ogni scheda entra nel canale del
suo utente, così il server può scrivere a tutte le schede di quell'utente.
Nei log solo il numero dell'utente, mai dati personali.
"""

import logging

from flask import request
from flask_login import current_user
from flask_socketio import ConnectionRefusedError, join_room

from app.realtime.events import NOT_LOGGED_IN, user_channel

log = logging.getLogger(__name__)


def on_connect(auth=None):
    if not current_user.is_authenticated:
        raise ConnectionRefusedError(NOT_LOGGED_IN)
    join_room(user_channel(current_user.id))
    log.info("Collegato l'utente %s (connessione %s)", current_user.id, request.sid)


def on_disconnect(reason=None):
    if current_user.is_authenticated:
        log.info("Scollegato l'utente %s (connessione %s)", current_user.id, request.sid)


def register(socketio):
    socketio.on_event("connect", on_connect)
    socketio.on_event("disconnect", on_disconnect)
