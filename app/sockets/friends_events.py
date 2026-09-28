"""Amici online e inviti a partita (P47; contratto 5.2 e 5.3; D27, D36).

Inviti: invite:send, invite:accept, invite:decline, invite:cancel, invite:start.
- Tutto quello che arriva dalla pagina si controlla qui: un dato non valido si rifiuta
  con `invalid_data`, senza correzioni. invite:send porta `request_id` (contratto 1.3).
- Si invita solo un amico (`not_friends`) collegato (`offline`); nessuno dei due può
  essere in partita, in coda o con un altro invito aperto (`busy`).
- L'invitato riceve invite:received; a ogni cambio di stato tutti e due ricevono
  invite:update {"invite_id", "status"} (invites.on_change).
- invite:start (chi ha invitato, dopo "accepted"): nel 1v1 crea la partita senza
  rating (D36) e tutti e due ricevono game:start; nel 2v2 la coppia entra nella coda
  (matchmaker.join_pair, P29) e la risposta è lo stato della coda.
- Chi chiude tutte le schede perde i suoi inviti aperti ("cancelled",
  connection_events.py).

Amici online (friends:presence {"user_id", "presence"}): agli amici collegati di chi
entra online, esce, comincia o finisce una partita (notify_presence). friends:changed
lo manda friend_service.py dopo ogni cambiamento di amicizie e blocchi.
Nei log solo numeri di utente.
"""

import logging
from contextlib import nullcontext

from flask import current_app, has_app_context, request
from flask_login import current_user

from app.extensions import socketio
from app.realtime import room as room_module
from app.realtime.events import EventError, handler, user_channel
from app.realtime.invites import invites
from app.realtime.matchmaking import matchmaker
from app.realtime.presence import presence
from app.realtime.room import MODES, Player
from app.realtime.room_manager import RoomError, create_room, find_room_of_user
from app.repositories import friend_repo, user_repo
from app.services import friend_service
from config import BaseConfig

log = logging.getLogger(__name__)

recent = friend_service.RecentRequests()
INVITE_ID_MAX = 64


# --- Amici online (5.2) ---


def notify_presence(user_ids, app=None):
    """friends:presence agli amici collegati di quegli utenti. Serve il database: dentro
    Flask si usa l'app corrente, da un thread quella data; senza nessuna delle due non fa niente."""
    if app is None and not has_app_context():
        return
    try:
        with app.app_context() if app is not None else nullcontext():
            for user_id in user_ids:
                data = {"user_id": user_id, "presence": friend_service.presence(user_id)}
                for friend in friend_repo.friends_of(user_id):
                    if presence.is_online(friend.id):
                        socketio.emit("friends:presence", data, to=user_channel(friend.id))
    except Exception:
        # Un avviso agli amici non riuscito non deve fermare il collegamento o la partita
        log.exception("friends:presence non mandato per gli utenti %s", list(user_ids))


def _game_changed(user_ids, app):
    if app is not None:
        notify_presence(user_ids, app)


# --- Inviti (5.3) ---


def _send_update(invite):
    data = {"invite_id": invite.invite_id, "status": invite.status}
    for player in (invite.sender, invite.recipient):
        socketio.emit("invite:update", data, to=user_channel(player.user_id))


invites.on_change = _send_update


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _invite_id(data):
    if not isinstance(data, dict):
        raise EventError("invalid_data", "Richiesta non valida.")
    invite_id = data.get("invite_id")
    if not isinstance(invite_id, str) or not 0 < len(invite_id) <= INVITE_ID_MAX:
        raise EventError("invalid_data", "Invito non valido.")
    return invite_id


def _send_data(data):
    if not isinstance(data, dict):
        raise EventError("invalid_data", "Richiesta non valida.")
    request_id = friend_service.check_request_id(data.get("request_id"))
    user_id = data.get("user_id")
    if not _is_int(user_id) or user_id <= 0:
        raise EventError("invalid_data", "user_id deve essere il numero di un utente.")
    mode = data.get("mode")
    if not isinstance(mode, str) or mode not in MODES:
        raise EventError("invalid_data", "Modalità non valida.")
    target_score = data.get("target_score")
    if not _is_int(target_score) or target_score not in BaseConfig.TARGET_SCORES:
        raise EventError("invalid_data", "Punti per vincere non validi.")
    return request_id, user_id, mode, target_score


def _check_free(user_id, name=None):
    """busy se l'utente è in partita o in coda (gli inviti aperti li controlla invites)."""
    if find_room_of_user(user_id) is not None or user_id in matchmaker.queue:
        raise EventError("busy", f"{name} sta già giocando o è in coda." if name
                         else "Sei già in partita o in coda.")


def _send(me, other_id, mode, target_score):
    if other_id == me.id:
        raise EventError("invalid_data", "Non puoi invitare te stesso.")
    row = friend_repo.get_pair(me.id, other_id)
    if row is None or row.status != friend_repo.ACCEPTED:
        raise EventError("not_friends", "Puoi invitare solo i tuoi amici.")
    other = user_repo.get_by_id(other_id)
    if other is None:
        raise EventError("not_friends", "Puoi invitare solo i tuoi amici.")
    if not presence.is_online(other_id):
        raise EventError("offline", f"{other.username} non è collegato.")
    _check_free(me.id)
    _check_free(other_id, other.username)
    invite = invites.send(Player.of(me), Player.of(other), mode, target_score)
    data = invites.data(invite)
    socketio.emit("invite:received", data, to=user_channel(other_id))
    return data


@handler
def on_send(data=None):
    request_id, other_id, mode, target_score = _send_data(data)
    me = current_user._get_current_object()
    return recent.run(me.id, "invite:send", request_id, lambda: _send(me, other_id, mode, target_score))


@handler
def on_accept(data=None):
    invite_id = _invite_id(data)
    _check_free(current_user.id)
    invites.accept(invite_id, current_user.id)


@handler
def on_decline(data=None):
    invites.decline(_invite_id(data), current_user.id)


@handler
def on_cancel(data=None):
    invites.cancel(_invite_id(data), current_user.id)


@handler
def on_start(data=None):
    """"Gioca" di chi ha invitato: 1v1 → partita senza rating; 2v2 → la coppia in coda."""
    invite_id = _invite_id(data)
    app, sid = current_app._get_current_object(), request.sid
    with invites.lock:  # un doppio clic non avvia due partite
        invite = invites.accepted_of_sender(invite_id, current_user.id)
        if not presence.is_online(invite.recipient.user_id):
            raise EventError("offline", f"{invite.recipient.username} non è più collegato.")
        _check_free(invite.sender.user_id)
        _check_free(invite.recipient.user_id, invite.recipient.username)
        if invite.mode == "1v1":
            try:
                create_room([invite.sender, invite.recipient], "1v1", invite.target_score, rated=False)
            except RoomError:
                raise EventError("busy", "Uno dei due è già in partita.") from None
            result = None
        else:
            result = matchmaker.join_pair(app, invite.sender, invite.recipient, invite.target_score, sid)
        invites.mark_started(invite)
    return result


def register(socketio):
    socketio.on_event("invite:send", on_send)
    socketio.on_event("invite:accept", on_accept)
    socketio.on_event("invite:decline", on_decline)
    socketio.on_event("invite:cancel", on_cancel)
    socketio.on_event("invite:start", on_start)
    for listeners in (room_module.start_listeners, room_module.finish_listeners):
        if _game_changed not in listeners:
            listeners.append(_game_changed)
