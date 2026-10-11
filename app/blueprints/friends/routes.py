"""Rotte: richieste di amicizia, lista amici e blocchi (P45; contratto 2.2).

Richieste HTTP in JSON, tutte con il login; quelle che modificano qualcosa (POST,
DELETE) mandano il codice CSRF nell'intestazione X-CSRFToken (contratto 1.5).
Rispondono nella forma del contratto (1.2): {"ok": true, "data": ...} oppure
{"ok": false, "error": {"code", "message"}} con il codice HTTP della tabella.
La logica sta in app/services/friend_service.py.
"""

import functools

from flask import request
from flask_login import current_user

from app.blueprints.friends import bp
from app.realtime.events import EventError, error, ok
from app.services import friend_service

# Codice HTTP di ogni errore del contratto (1.2)
HTTP_STATUS = {
    "invalid_data": 400,
    "not_logged_in": 401,
    "not_allowed": 403,
    "blocked": 403,
    "not_found": 404,
    "not_friends": 403,
    "busy": 409,
    "already_exists": 409,
    "request_from_them": 409,
    "limit_reached": 409,
    "too_fast": 429,
    "expired": 410,
    "server_error": 500,
}


def json_endpoint(fn):
    """Login obbligatorio (senza: not_logged_in, 401, non il rimando alla pagina di accesso)
    e risposta del contratto; un errore imprevisto passa a app/errors.py (server_error, 500)."""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return error("not_logged_in"), 401
        try:
            return ok(fn(*args, **kwargs))
        except EventError as exc:
            return error(exc.code, exc.message, **exc.extra), HTTP_STATUS.get(exc.code, 400)

    return wrapper


def body():
    """Il corpo JSON della richiesta, che deve essere un oggetto."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise EventError("invalid_data", "Il corpo della richiesta deve essere un oggetto JSON.")
    return data


@bp.get("/")
@json_endpoint
def overview():
    return friend_service.overview(current_user.id)


@bp.post("/requests")
@json_endpoint
def send_request():
    data = body()
    return friend_service.send_request(current_user.id, data.get("request_id"), data.get("username"))


@bp.post("/requests/<int:user_id>/accept")
@json_endpoint
def accept_request(user_id):
    friend_service.accept_request(current_user.id, user_id)


@bp.post("/requests/<int:user_id>/decline")
@json_endpoint
def decline_request(user_id):
    friend_service.decline_request(current_user.id, user_id)


@bp.delete("/requests/<int:user_id>")
@json_endpoint
def cancel_request(user_id):
    friend_service.cancel_request(current_user.id, user_id)


@bp.delete("/<int:user_id>")
@json_endpoint
def remove_friend(user_id):
    friend_service.remove_friend(current_user.id, user_id)


@bp.post("/blocks")
@json_endpoint
def block():
    data = body()
    friend_service.block(current_user.id, data.get("request_id"), data.get("user_id"))


@bp.delete("/blocks/<int:user_id>")
@json_endpoint
def unblock(user_id):
    friend_service.unblock(current_user.id, user_id)
