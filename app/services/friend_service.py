"""Amicizie e blocchi (P45; contratto 2.2, decisioni D23, D26, D33 e P8).

- Richiesta a chi ha ESATTAMENTE quello username (D33, maiuscole comprese). Se l'altro
  te ne ha già mandata una ricevi `request_from_them`: l'amicizia non parte da sola (P8).
- Blocco (D23): chi ti ha bloccato risulta inesistente (`not_found`, privacy); se l'hai
  bloccato tu ricevi `blocked`. Il blocco toglie l'amicizia e le richieste tra i due.
- Al massimo FRIENDS_MAX amici per utente (D26): si controlla quando si manda la
  richiesta e quando si accetta, per tutti e due.
- Accettare, rifiutare, annullare, togliere o sbloccare una seconda volta risponde ok
  senza fare niente (contratto 2.2).
- Ogni scrittura blocca prima le righe dei due utenti (friend_repo.lock_users): i
  controlli e la scrittura stanno nella stessa transazione, così due richieste
  contemporanee (doppio clic, due schede) non creano doppioni né superano il limite.
- Le richieste che creano qualcosa portano `request_id` (contratto 1.3): la stessa
  richiesta ripetuta riceve la risposta della prima volta (RecentRequests, in memoria).
- `presence` degli amici: "in_game" se ha una partita in corso (room_manager, P24),
  "online" se ha almeno una scheda collegata in tempo reale (presence.py, P44),
  altrimenti "offline". Gli avvisi quando cambia li manda friends_events.py (P47).
- P47: dopo ogni cambiamento vero l'altro utente riceve friends:changed {"reason"} e la
  sua pagina ricarica la lista. Chi viene bloccato riceve "friend_removed", mai
  "blocked" (non deve sapere di essere stato bloccato: scelta di Giuseppe); "blocked" va
  solo alle schede di chi blocca. Togliere l'amicizia o bloccare annulla l'invito a
  partita aperto tra i due.
Nei log solo numeri di utente, mai username o email.
"""

import logging
import threading
import time

from flask import current_app

from app.extensions import db, socketio
from app.realtime.events import EventError, user_channel
from app.realtime.invites import invites
from app.realtime.presence import presence as online_users
from app.realtime.room_manager import find_room_of_user
from app.repositories import friend_repo, user_repo

log = logging.getLogger(__name__)

REQUEST_ID_MAX = 100
PRESENCE_ORDER = {"online": 0, "in_game": 1, "offline": 2}

NO_SUCH_USER = "Nessun utente con questo username."
NOT_A_USER = "Questo utente non esiste."
SELF_REQUEST = "Non puoi mandare una richiesta a te stesso."
SELF_BLOCK = "Non puoi bloccare te stesso."
YOU_BLOCKED = "Hai bloccato questo utente: sbloccalo prima di mandargli una richiesta."
ALREADY_FRIENDS = "Siete già amici."
ALREADY_SENT = "Gli hai già mandato una richiesta."
REQUEST_FROM_THEM = "Ti ha già mandato una richiesta: accettala."
NO_REQUEST = "Non c'è una richiesta da questo utente."
MY_LIMIT = "Hai già {n} amici: è il massimo."
THEIR_LIMIT = "Questo utente ha già {n} amici: è il massimo."


class RecentRequests:
    """Risposte alle richieste con request_id, tenute in memoria per `seconds` secondi.

    La chiave è (utente, azione, request_id). Le richieste di uno stesso utente
    passano una alla volta (un lock per utente): così anche due tentativi
    contemporanei con lo stesso request_id ricevono la stessa risposta.
    Si ricordano le risposte ok e gli errori del contratto, non gli errori imprevisti.
    """

    def __init__(self, seconds=600, clock=time.monotonic):
        self._seconds = seconds
        self._clock = clock
        self._lock = threading.Lock()
        self._user_locks = {}
        self._results = {}  # chiave -> (ora, ("ok", dati) oppure ("error", EventError))

    def _user_lock(self, user_id):
        with self._lock:
            return self._user_locks.setdefault(user_id, threading.Lock())

    def run(self, user_id, action, request_id, fn):
        key = (user_id, action, request_id)
        with self._user_lock(user_id):
            with self._lock:
                now = self._clock()
                self._results = {k: v for k, v in self._results.items() if now - v[0] < self._seconds}
                saved = self._results.get(key)
            if saved is None:
                try:
                    result = ("ok", fn())
                except EventError as exc:
                    result = ("error", exc)
                with self._lock:
                    self._results[key] = (self._clock(), result)
            else:
                result = saved[1]
        kind, value = result
        if kind == "error":
            raise value
        return value


recent = RecentRequests()


# Dati in ingresso


def check_request_id(value):
    if not isinstance(value, str) or not 1 <= len(value) <= REQUEST_ID_MAX:
        raise EventError("invalid_data", "Manca request_id, oppure non è valido.")
    return value


def check_user_id(value):
    # bool è un int per Python: True non è un numero di utente
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise EventError("invalid_data", "user_id deve essere il numero di un utente.")
    return value


def check_username(value):
    """Lo username scritto per cercare un utente, senza spazi all'inizio e alla fine (P63:
    dal telefono capita di aggiungerne uno). Non è una correzione silenziosa di un dato
    valido: uno username non contiene mai spazi (D7). Uno spazio in mezzo resta, e
    l'utente non si trova."""
    maximum = current_app.config["USERNAME_MAX"]
    if isinstance(value, str):
        value = value.strip()
    if not isinstance(value, str) or not 1 <= len(value) <= maximum:
        raise EventError("invalid_data", f"Scrivi uno username (al massimo {maximum} caratteri).")
    return value


# Lettura


def overview(user_id):
    """Lista del contratto (GET /friends/): amici, richieste, bloccati e contatori."""
    unread = friend_repo.unread_by_sender(user_id)
    friends = [
        {**_user(u), "presence": presence(u.id), "unread": unread.get(u.id, 0)}
        for u in friend_repo.friends_of(user_id)
    ]
    friends.sort(key=lambda f: PRESENCE_ORDER[f["presence"]])  # stabile: dentro ogni gruppo resta l'ordine per nome
    requests_in = [{**_user(u), "sent_at": iso_utc(at)} for u, at in friend_repo.requests_in(user_id)]
    requests_out = [{**_user(u), "sent_at": iso_utc(at)} for u, at in friend_repo.requests_out(user_id)]
    return {
        "friends": friends,
        "requests_in": requests_in,
        "requests_out": requests_out,
        "blocked": [_user(u) for u in friend_repo.blocked_by(user_id)],
        "counters": {"requests_in": len(requests_in), "unread_messages": sum(unread.values())},
    }


def presence(user_id):
    if find_room_of_user(user_id) is not None:
        return "in_game"
    return "online" if online_users.is_online(user_id) else "offline"


def _changed(user_id, reason):
    """friends:changed (contratto 5.2) a tutte le schede di quell'utente (P47)."""
    socketio.emit("friends:changed", {"reason": reason}, to=user_channel(user_id))


def _user(user):
    return {"user_id": user.id, "username": user.username, "avatar": user.avatar}


def iso_utc(moment):
    """Data e ora del database (UTC) nel formato del contratto: 2026-09-28T14:03:12.000Z."""
    return moment.strftime("%Y-%m-%dT%H:%M:%S.") + f"{moment.microsecond // 1000:03d}Z"


# Scritture


def send_request(user_id, request_id, username):
    check_request_id(request_id)
    username = check_username(username)
    return recent.run(user_id, "request", request_id, lambda: _sent(_write(_send_request, user_id, username)))


def _sent(result):
    _changed(result["user_id"], "request_received")
    return result


# P65: gli avvisi arrivano a tutti e due, anche alle schede di chi ha fatto l'azione:
# la home (lista degli amici da invitare) e le altre schede rileggono la lista. Prima
# chi accettava una richiesta non vedeva il nuovo amico nella carta "Gioca con un amico"
# finché non ricaricava la pagina.


def accept_request(user_id, other_id):
    if _write(_accept_request, user_id, check_user_id(other_id)):
        _changed(other_id, "request_accepted")
        _changed(user_id, "request_accepted")


def decline_request(user_id, other_id):
    if _write(_delete_pending, user_id, other_id, user_id):
        _changed(other_id, "request_declined")
        _changed(user_id, "request_declined")


def cancel_request(user_id, other_id):
    if _write(_delete_pending, user_id, user_id, other_id):
        _changed(other_id, "request_declined")  # la richiesta che aveva ricevuto non c'è più
        _changed(user_id, "request_declined")


def remove_friend(user_id, other_id):
    if _write(_remove_friend, user_id, other_id):
        invites.cancel_all_of(user_id, only_with=other_id)
        _changed(other_id, "friend_removed")
        _changed(user_id, "friend_removed")


def block(user_id, request_id, other_id):
    check_request_id(request_id)
    check_user_id(other_id)
    return recent.run(user_id, "block", request_id, lambda: _blocked(user_id, other_id))


def _blocked(user_id, other_id):
    removed = _write(_block, user_id, other_id)
    invites.cancel_all_of(user_id, only_with=other_id)
    if removed:
        _changed(other_id, "friend_removed")  # sparisce dalla sua lista, senza sapere del blocco
    _changed(user_id, "blocked")  # le altre schede di chi blocca


def unblock(user_id, other_id):
    if _write(_unblock, user_id, other_id):
        _changed(user_id, "blocked")  # solo chi sblocca: l'elenco dei bloccati è cambiato; l'altro non lo sa


def _write(action, *args):
    """Esegue `action` in una transazione: commit se va bene, altrimenti rollback.

    Prima chiude la transazione aperta dalle letture precedenti (per esempio il
    caricamento dell'utente del login) e apre la nuova in READ COMMITTED: con il
    livello predefinito di MySQL (REPEATABLE READ) le letture vedrebbero i dati
    com'erano alla prima lettura, e dopo aver aspettato il lock degli utenti non
    vedrebbero la richiesta appena salvata da un'altra scheda.
    """
    db.session.rollback()
    db.session.connection(execution_options={"isolation_level": "READ COMMITTED"})
    try:
        result = action(*args)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return result


def _send_request(user_id, username):
    target = user_repo.get_by_username(username)
    if target is None:
        raise EventError("not_found", NO_SUCH_USER)
    if target.id == user_id:
        raise EventError("invalid_data", SELF_REQUEST)
    if target.id not in friend_repo.lock_users(user_id, target.id):
        raise EventError("not_found", NO_SUCH_USER)
    if friend_repo.get_block(target.id, user_id) is not None:
        raise EventError("not_found", NO_SUCH_USER)  # chi ti ha bloccato risulta inesistente (P8)
    if friend_repo.get_block(user_id, target.id) is not None:
        raise EventError("blocked", YOU_BLOCKED)

    row = friend_repo.get_pair(user_id, target.id)
    if row is not None:
        if row.status == friend_repo.ACCEPTED:
            raise EventError("already_exists", ALREADY_FRIENDS)
        if row.requester_id == user_id:
            raise EventError("already_exists", ALREADY_SENT)
        raise EventError("request_from_them", REQUEST_FROM_THEM)
    _check_limits(user_id, target.id)

    row = friend_repo.add_request(user_id, target.id)
    log.info("Richiesta di amicizia da %s a %s", user_id, target.id)
    return {**_user(target), "sent_at": iso_utc(row.requested_at)}


def _accept_request(user_id, other_id):
    friend_repo.lock_users(user_id, other_id)
    row = friend_repo.get_pair(user_id, other_id)
    if row is not None and row.status == friend_repo.ACCEPTED:
        return False  # già amici: seconda volta, niente da fare
    if row is None or row.requester_id != other_id:
        raise EventError("not_found", NO_REQUEST)
    _check_limits(user_id, other_id)
    friend_repo.accept(row)
    log.info("Amicizia accettata tra %s e %s", other_id, user_id)
    return True


def _delete_pending(user_id, requester_id, addressee_id):
    friend_repo.lock_users(requester_id, addressee_id)
    row = friend_repo.get_pair(requester_id, addressee_id)
    if row is not None and row.status == friend_repo.PENDING and row.requester_id == requester_id:
        friend_repo.delete(row)
        return True
    return False


def _remove_friend(user_id, other_id):
    friend_repo.lock_users(user_id, other_id)
    row = friend_repo.get_pair(user_id, other_id)
    if row is not None and row.status == friend_repo.ACCEPTED:
        friend_repo.delete(row)
        log.info("Amicizia tolta tra %s e %s", user_id, other_id)
        return True
    return False


def _block(user_id, other_id):
    if other_id == user_id:
        raise EventError("invalid_data", SELF_BLOCK)
    if other_id not in friend_repo.lock_users(user_id, other_id):
        raise EventError("not_found", NOT_A_USER)
    if friend_repo.get_block(user_id, other_id) is None:
        friend_repo.add_block(user_id, other_id)
        log.info("L'utente %s ha bloccato %s", user_id, other_id)
    row = friend_repo.get_pair(user_id, other_id)
    if row is not None:
        friend_repo.delete(row)  # il blocco toglie amicizia e richieste (D23)
        return True  # l'altro aveva l'amicizia o una richiesta: la sua lista cambia
    return False


def _unblock(user_id, other_id):
    friend_repo.lock_users(user_id, other_id)
    row = friend_repo.get_block(user_id, other_id)
    if row is not None:
        friend_repo.delete(row)
        return True
    return False


def _check_limits(user_id, other_id):
    maximum = current_app.config["FRIENDS_MAX"]
    if friend_repo.count_friends(user_id) >= maximum:
        raise EventError("limit_reached", MY_LIMIT.format(n=maximum))
    if friend_repo.count_friends(other_id) >= maximum:
        raise EventError("limit_reached", THEIR_LIMIT.format(n=maximum))
