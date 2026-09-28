"""Entrata e uscita dalle code di matchmaking (P28, contratto 4): queue:join, queue:leave.

- Tutto quello che arriva dalla pagina si controlla qui: un dato non valido si rifiuta
  con `invalid_data`, senza correzioni.
- queue:join porta `request_id` (contratto 1.3): lo stesso tentativo ripetuto riceve la
  risposta della prima volta (RecentRequests di P45), senza entrare in coda due volte.
- La coda e gli abbinamenti stanno in app/realtime/matchmaking.py.
"""

from flask import current_app, request
from flask_login import current_user

from app.realtime.events import EventError, handler
from app.realtime.matchmaking import matchmaker
from app.services.friend_service import RecentRequests
from config import BaseConfig

REQUEST_ID_MAX = 100
MODES = ("1v1", "2v2")

recent = RecentRequests()


def _join_data(data):
    if not isinstance(data, dict):
        raise EventError("invalid_data", "Richiesta non valida.")
    request_id = data.get("request_id")
    if not isinstance(request_id, str) or not 1 <= len(request_id) <= REQUEST_ID_MAX:
        raise EventError("invalid_data", "Richiesta non valida.")
    mode = data.get("mode")
    if not isinstance(mode, str) or mode not in MODES:
        raise EventError("invalid_data", "Modalità non valida.")
    target_score = data.get("target_score")
    if (not isinstance(target_score, int) or isinstance(target_score, bool)
            or target_score not in BaseConfig.TARGET_SCORES):
        raise EventError("invalid_data", "Punti per vincere non validi.")
    if mode == "2v2":
        raise EventError("not_allowed", "La coda 2v2 non è ancora attiva.")  # arriva con P29
    return request_id, mode, target_score


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


def register(socketio):
    socketio.on_event("queue:join", on_join)
    socketio.on_event("queue:leave", on_leave)
