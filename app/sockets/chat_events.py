"""Chat tra amici (P48, contratto 5.4): chat:history, chat:send, chat:read.

- Ingressi sottili: controlli e scritture stanno in app/services/chat_service.py.
- Un messaggio salvato arriva con chat:message al destinatario (tutte le sue schede)
  e alle altre schede di chi l'ha scritto; la scheda che l'ha mandato lo riceve nella
  risposta.
- Il testo dei messaggi non va mai nei log.
"""

from flask import request
from flask_login import current_user

from app.extensions import socketio
from app.realtime.events import EventError, handler, user_channel
from app.services import chat_service


def _data(data):
    if not isinstance(data, dict):
        raise EventError("invalid_data", "Richiesta non valida.")
    return data


@handler
def on_history(data=None):
    data = _data(data)
    return chat_service.history(current_user.id, data.get("user_id"), data.get("before_id"))


@handler
def on_send(data=None):
    data = _data(data)
    me, sid = current_user.id, request.sid

    def deliver(message):
        socketio.emit("chat:message", {"message": message}, to=user_channel(message["to_user_id"]))
        socketio.emit("chat:message", {"message": message}, to=user_channel(me), skip_sid=sid)

    return chat_service.send(me, data.get("request_id"), data.get("user_id"), data.get("text"), deliver)


@handler
def on_read(data=None):
    data = _data(data)
    chat_service.read(current_user.id, data.get("user_id"))


def register(socketio):
    socketio.on_event("chat:history", on_history)
    socketio.on_event("chat:send", on_send)
    socketio.on_event("chat:read", on_read)
