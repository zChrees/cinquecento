"""Amici online e inviti a partita (P47; contratto 5.2 e 5.3; D27, D36).

Inviti: invite:send, invite:accept, invite:decline, invite:cancel, invite:start.
- Tutto quello che arriva dalla pagina si controlla qui: un dato non valido si rifiuta
  con `invalid_data`, senza correzioni. invite:send porta `request_id` (contratto 1.3).
- Si invita solo un amico (`not_friends`) collegato (`offline`); nessuno dei due può
  essere in partita, in coda o con un altro invito aperto (`busy`).
- L'invitato riceve invite:received; a ogni cambio di stato tutti e due ricevono
  invite:update {"invite_id", "status"} (invites.on_change).
- invite:start (chi ha invitato, dopo "accepted"): nel 1v1 crea la partita senza
  rating (D36) e tutti e due ricevono game:start; nel 2v2 (P59) conta quanti amici del
  gruppo hanno accettato: con uno la coppia entra nella coda (matchmaker.join_pair,
  P29), con due il gruppo di tre (matchmaker.join_group), e la risposta è lo stato
  della coda; con tre la partita parte subito, a squadre tirate a sorte e senza
  rating. Gli inviti del gruppo ancora in attesa diventano "cancelled".
- Chi chiude tutte le schede perde i suoi inviti aperti ("cancelled",
  connection_events.py).

Amici online (friends:presence {"user_id", "presence"}): agli amici collegati di chi
entra online, esce, comincia o finisce una partita (notify_presence). friends:changed
lo manda friend_service.py dopo ogni cambiamento di amicizie e blocchi.
Nei log solo numeri di utente.

Cosa contiene:
    notify_presence(user_ids, app)   friends:presence agli amici collegati
    on_send, on_accept, on_decline, on_cancel, on_start
                                     un gestore per ogni evento degli inviti
    register(socketio)               registra i gestori e gli avvisi di inizio e fine partita

DA DOVE ARRIVANO I DATI: dalla home React (frontend/src/pages/HomePage.tsx, con la
carta-modal "Gioca con un amico" e la finestra dell'invito ricevuto, InviteDialog.tsx),
che manda user_id (l'amico), mode, target_score, request_id o invite_id.
"""

import logging
import secrets

# nullcontext: un "with" che non fa niente, quando non serve entrare nell'app Flask
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

# recent: le risposte date di recente, per chiave anti-doppione (request_id)
recent = friend_service.RecentRequests()
INVITE_ID_MAX = 64


# --- Amici online (5.2) ---


def notify_presence(user_ids, app=None):
    """friends:presence agli amici collegati di quegli utenti. Serve il database: dentro
    Flask si usa l'app corrente, da un thread quella data; senza nessuna delle due non fa niente.

    In parole semplici:
        notify_presence([7])
        notify_presence(user_ids, app)
        user_ids: gli utenti il cui stato è cambiato (online, offline, in partita).
        app:      facoltativo, l'applicazione Flask; la passa la stanza, che chiama da
                  un thread fuori da una richiesta.
        Per ogni utente, ogni suo amico collegato riceve {"user_id", "presence"}.
    """
    if app is None and not has_app_context():
        return
    try:
        # context: con un'app data si "entra" in quella; dentro Flask non serve (nullcontext)
        if app is not None:
            context = app.app_context()
        else:
            context = nullcontext()
        with context:
            for user_id in user_ids:
                data = {"user_id": user_id, "presence": friend_service.presence(user_id)}
                for friend in friend_repo.friends_of(user_id):
                    if presence.is_online(friend.id):
                        socketio.emit("friends:presence", data, to=user_channel(friend.id))
    except Exception:
        # Un avviso agli amici non riuscito non deve fermare il collegamento o la partita
        log.exception("friends:presence non mandato per gli utenti %s", list(user_ids))


def _game_changed(user_ids, app):
    """Inizio o fine di una partita: gli amici dei giocatori vedono lo stato nuovo.

    In parole semplici:
        _game_changed(user_ids, app)
        La chiama la stanza (start_listeners e finish_listeners di room.py), da un
        thread a parte; senza app (stanza creata fuori da Flask) non fa niente.
    """
    if app is not None:
        notify_presence(user_ids, app)


# --- Inviti (5.3) ---


def _send_update(invite):
    """invite:update a chi ha invitato e a chi è stato invitato.

    In parole semplici:
        _send_update(invite)
        La chiama invites a ogni cambio di stato (è il suo on_change, qui sotto).
    """
    data = {"invite_id": invite.invite_id, "status": invite.status}
    for player in (invite.sender, invite.recipient):
        socketio.emit("invite:update", data, to=user_channel(player.user_id))


invites.on_change = _send_update


def _is_int(value):
    """True se `value` è un intero vero (True e False, che in Python sono anche numeri, no)."""
    return isinstance(value, int) and not isinstance(value, bool)


def _invite_id(data):
    """Il codice dell'invito mandato dalla pagina, controllato (un testo da 1 a INVITE_ID_MAX caratteri)."""
    if not isinstance(data, dict):
        raise EventError("invalid_data", "Richiesta non valida.")
    invite_id = data.get("invite_id")
    if not isinstance(invite_id, str) or len(invite_id) == 0 or len(invite_id) > INVITE_ID_MAX:
        raise EventError("invalid_data", "Invito non valido.")
    return invite_id


def _send_data(data):
    """I dati di invite:send, controllati.

    In parole semplici:
        _send_data(data)
        data: per esempio {"request_id": "a1b2", "user_id": 12, "mode": "1v1", "target_score": 300}.
        Restituisce la tupla (request_id, user_id, mode, target_score); un valore non
        valido si rifiuta con invalid_data.
    """
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
    """busy se l'utente è in partita o in coda (gli inviti aperti li controlla invites).

    In parole semplici:
        _check_free(user_id, name)
        name: facoltativo, il nome dell'amico, per il messaggio; senza (o vuoto) il
        messaggio parla a chi ha fatto la richiesta.
    """
    if find_room_of_user(user_id) is not None or user_id in matchmaker.queue:
        if name:
            message = f"{name} sta già giocando o è in coda."
        else:
            message = "Sei già in partita o in coda."
        raise EventError("busy", message)


def _send(me, other_id, mode, target_score):
    """Manda l'invito, dopo i controlli: amicizia, amico collegato, tutti e due liberi.

    In parole semplici:
        _send(me, other_id, mode, target_score)
        me: l'utente che invita. other_id: il numero dell'amico.
        L'amico riceve invite:received; chi invita riceve l'invito nella risposta.
    """
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


# @handler (app/realtime/events.py): controlla login e limite di frequenza e
# trasforma quello che il gestore restituisce nella risposta del contratto
@handler
def on_send(data=None):
    """invite:send: invita un amico.

    In parole semplici:
        Lo stesso request_id ripetuto riceve la stessa risposta (recent.run), senza
        mandare due inviti.
    """
    checked = _send_data(data)
    request_id = checked[0]
    other_id = checked[1]
    mode = checked[2]
    target_score = checked[3]
    # _get_current_object: l'utente vero, non il "segnaposto" di Flask-Login
    me = current_user._get_current_object()

    def send():
        """L'invito vero (lo chiama recent.run, se il tentativo è nuovo)."""
        return _send(me, other_id, mode, target_score)

    return recent.run(me.id, "invite:send", request_id, send)


@handler
def on_accept(data=None):
    """invite:accept: l'invitato accetta (deve essere libero: non in partita né in coda)."""
    invite_id = _invite_id(data)
    _check_free(current_user.id)
    invites.accept(invite_id, current_user.id)


@handler
def on_decline(data=None):
    """invite:decline: l'invitato rifiuta."""
    invites.decline(_invite_id(data), current_user.id)


@handler
def on_cancel(data=None):
    """invite:cancel: chi ha invitato annulla."""
    invites.cancel(_invite_id(data), current_user.id)


@handler
def on_start(data=None):
    """"Gioca" di chi ha invitato: 1v1 → partita senza rating. 2v2 (P59), con gli amici
    che hanno accettato: uno → la coppia in coda; due → il gruppo di tre in coda (coppia
    a sorte); tre → partita subito, squadre a sorte, senza rating. Gli inviti del gruppo
    ancora in attesa si annullano.

    In parole semplici:
        data: {"invite_id": "inv_..."}.
        Tutto sotto il lucchetto degli inviti, così un doppio clic non avvia due
        partite. Restituisce None (la partita arriva con game:start) oppure, quando si
        entra in coda, lo stato della coda.
    """
    invite_id = _invite_id(data)
    app = current_app._get_current_object()
    sid = request.sid
    with invites.lock:  # un doppio clic non avvia due partite
        invite = invites.accepted_of_sender(invite_id, current_user.id)
        # group: nel 2v2 tutti gli inviti aperti di chi invita; nel 1v1 solo questo
        if invite.mode == "2v2":
            group = invites.group_of(invite.sender.user_id)
        else:
            group = [invite]
        # accepted: gli inviti del gruppo già accettati
        accepted = []
        for other in group:
            if other.status == "accepted":
                accepted.append(other)

        # tutti devono essere ancora collegati e liberi
        for other in accepted:
            if not presence.is_online(other.recipient.user_id):
                raise EventError("offline", f"{other.recipient.username} non è più collegato.")
        _check_free(invite.sender.user_id)
        for other in accepted:
            _check_free(other.recipient.user_id, other.recipient.username)

        # friends: gli amici che giocano (chi ha accettato)
        friends = []
        for other in accepted:
            friends.append(other.recipient)

        result = None
        if invite.mode == "1v1":
            _create([invite.sender] + friends, "1v1", invite.target_score)
        elif len(friends) == 1:
            result = matchmaker.join_pair(app, invite.sender, friends[0], invite.target_score, sid)
        elif len(friends) == 2:
            result = matchmaker.join_group(app, invite.sender, friends, invite.target_score, sid)
        else:
            seats = [invite.sender] + friends
            secrets.SystemRandom().shuffle(seats)  # squadre (posti 0 e 2, 1 e 3) e posti a sorte
            _create(seats, "2v2", invite.target_score)

        # gli inviti accettati diventano "started", quelli ancora in attesa si annullano
        for other in group:
            if other.status == "accepted":
                invites.mark_started(other)
            else:
                invites.cancel(other.invite_id, invite.sender.user_id)
    return result


def _create(seats, mode, target_score):
    """Partita tra amici, senza rating (D36; P59 per il 2v2 di quattro amici).

    In parole semplici:
        _create(seats, mode, target_score)
        seats: i giocatori in ordine di posto. Se uno è già in partita, busy.
    """
    try:
        create_room(seats, mode, target_score, rated=False)
    except RoomError:
        raise EventError("busy", "Uno di voi è già in partita.") from None


def register(socketio):
    """Registra i gestori degli inviti e l'avviso agli amici a inizio e fine partita.

    In parole semplici:
        register(socketio)
        _game_changed si aggiunge una volta sola a start_listeners e finish_listeners
        (se create_app si chiama più volte, come nei test, non si raddoppia).
    """
    socketio.on_event("invite:send", on_send)
    socketio.on_event("invite:accept", on_accept)
    socketio.on_event("invite:decline", on_decline)
    socketio.on_event("invite:cancel", on_cancel)
    socketio.on_event("invite:start", on_start)
    for listeners in (room_module.start_listeners, room_module.finish_listeners):
        if _game_changed not in listeners:
            listeners.append(_game_changed)
