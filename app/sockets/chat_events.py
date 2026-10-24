"""Chat tra amici (P48, contratto 5.4): chat:history, chat:send, chat:read.

- Ingressi sottili: controlli e scritture stanno in app/services/chat_service.py.
- Un messaggio salvato arriva con chat:message al destinatario (tutte le sue schede)
  e alle altre schede di chi l'ha scritto; la scheda che l'ha mandato lo riceve nella
  risposta.
- Il testo dei messaggi non va mai nei log.

Cosa contiene:
    on_history(data)    chat:history, i messaggi con un amico
    on_send(data)       chat:send, un messaggio nuovo
    on_read(data)       chat:read, i messaggi di un amico segnati come letti
    register(socketio)  registra i tre gestori

DA DOVE ARRIVANO I DATI: dalla finestra della chat della pagina
(frontend/src/components/ChatWindow.tsx), che manda un dizionario con user_id
(l'amico) e, a seconda dell'evento, before_id, request_id e text.
"""

from flask import request
from flask_login import current_user

from app.extensions import socketio
from app.realtime.events import EventError, handler, user_channel
from app.services import chat_service


def _data(data):
    """Controlla che i dati dell'evento siano un dizionario e li restituisce.

    In parole semplici:
        _data(data)
        Se la pagina manda qualcosa che non è un oggetto JSON, la richiesta si rifiuta
        con invalid_data. I singoli campi li controlla chat_service.
    """
    if not isinstance(data, dict):
        raise EventError("invalid_data", "Richiesta non valida.")
    return data


# @handler (app/realtime/events.py): controlla login e limite di frequenza e
# trasforma quello che il gestore restituisce nella risposta del contratto
@handler
def on_history(data=None):
    """chat:history: i messaggi con un amico, dal più recente indietro.

    In parole semplici:
        data: {"user_id": 12, "before_id": null} (before_id per le pagine più vecchie).
        Restituisce quello che dà chat_service.history.
    """
    data = _data(data)
    return chat_service.history(current_user.id, data.get("user_id"), data.get("before_id"))


@handler
def on_send(data=None):
    """chat:send: manda un messaggio a un amico.

    In parole semplici:
        data: {"request_id": "...", "user_id": 12, "text": "Ciao!"}.
        chat_service.send controlla e salva il messaggio, poi chiama deliver (qui
        sotto) per mandarlo alle schede giuste.
    """
    data = _data(data)
    me = current_user.id
    sid = request.sid

    def deliver(message):
        """Manda il messaggio salvato al destinatario e alle altre schede di chi scrive.

        In parole semplici:
            deliver(message)
            message: il messaggio come lo restituisce chat_service (con to_user_id).
            La scheda che l'ha mandato si salta (skip_sid): lo riceve nella risposta.
        """
        socketio.emit("chat:message", {"message": message}, to=user_channel(message["to_user_id"]))
        socketio.emit("chat:message", {"message": message}, to=user_channel(me), skip_sid=sid)

    return chat_service.send(me, data.get("request_id"), data.get("user_id"), data.get("text"), deliver)


@handler
def on_read(data=None):
    """chat:read: i messaggi di quell'amico sono stati letti.

    In parole semplici:
        data: {"user_id": 12}. Non restituisce dati (la risposta è solo {"ok": true}).
    """
    data = _data(data)
    chat_service.read(current_user.id, data.get("user_id"))


def register(socketio):
    """Registra i gestori di chat:history, chat:send e chat:read."""
    socketio.on_event("chat:history", on_history)
    socketio.on_event("chat:send", on_send)
    socketio.on_event("chat:read", on_read)
