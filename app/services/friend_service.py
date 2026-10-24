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

Cosa contiene:
    RecentRequests / recent        le risposte già date, per request_id (anche chat e coda le usano)
    check_request_id(v)            controlla request_id: check_request_id("a1b2") -> "a1b2"
    check_user_id(v)               controlla un numero di utente: check_user_id(7) -> 7
    check_username(v)              controlla uno username: check_username(" Nina") -> "Nina"
    overview(user_id)              la lista del pannello amici (GET /api/friends/)
    presence(user_id)              "online", "in_game" o "offline"
    iso_utc(moment)                un'ora del database come testo: "2026-09-28T14:03:12.000Z"
    send_request(me, rid, name)    manda una richiesta di amicizia
    accept_request(me, other)      accetta la richiesta di other
    decline_request(me, other)     rifiuta la richiesta di other
    cancel_request(me, other)      annulla la richiesta mandata a other
    remove_friend(me, other)       toglie l'amicizia
    block(me, rid, other)          blocca other
    unblock(me, other)             sblocca other

DA DOVE ARRIVANO I DATI: il pannello amici della SPA (FriendsPanel.tsx, con le
richieste di frontend/src/api/friends.ts) chiama le rotte /api/friends/...
(app/blueprints/friends/routes.py), che passano a queste funzioni il numero
dell'utente collegato (current_user.id) e i dati del JSON o dell'indirizzo; presence
la usa anche app/sockets/friends_events.py per gli avvisi "online" e "in partita".
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
# PRESENCE_ORDER: l'ordine dei gruppi nella lista degli amici (prima chi è online)
PRESENCE_ORDER = {"online": 0, "in_game": 1, "offline": 2}

# I messaggi che vede l'utente
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

    In parole semplici:
        RecentRequests(seconds, clock)
        Una "classe": un tipo nuovo che tiene insieme dei dati (qui le risposte già
        date) e le funzioni che li usano (i "metodi", come run). È simile a una
        struct del C con le sue funzioni; self è l'oggetto stesso.
        seconds: facoltativo; per quanto si ricorda una risposta (600 = 10 minuti)
        clock:   facoltativo; la funzione che dà l'ora (time.monotonic, un orologio che
                 non torna mai indietro); i test ne passano una finta
        Ne creano una ciascuno questo file (recent), chat_service.py,
        app/sockets/friends_events.py e app/sockets/lobby_events.py.
    """

    def __init__(self, seconds=600, clock=time.monotonic):
        self._seconds = seconds
        self._clock = clock
        # _lock: il "lucchetto" (threading.Lock) dei due dizionari: le richieste
        # arrivano in thread diversi, e con "with self._lock:" una sola alla volta li usa
        self._lock = threading.Lock()
        # _user_locks: utente -> il suo lucchetto, per esempio {7: <Lock>}
        self._user_locks = {}
        # _results: chiave -> (ora, ("ok", dati) oppure ("error", EventError)), per esempio
        # {(7, "request", "a1b2"): (5031.2, ("ok", {"user_id": 8, ...}))}
        self._results = {}

    def _user_lock(self, user_id):
        """Il lucchetto di un utente, creato la prima volta.

        In parole semplici:
            _user_lock(7)
            setdefault(chiave, valore): restituisce il valore della chiave e, se non
            c'è, prima ce lo mette.
        """
        with self._lock:
            return self._user_locks.setdefault(user_id, threading.Lock())

    def run(self, user_id, action, request_id, fn):
        """Esegue fn una volta sola per (utente, azione, request_id) e ne restituisce il risultato.

        In parole semplici:
            run(user_id, action, request_id, fn)
            Per esempio run(7, "request", "a1b2", attempt): la prima volta chiama
            attempt() e si ricorda la risposta; ripetuto con la stessa chiave entro
            `seconds` restituisce la stessa risposta (o rilancia lo stesso errore)
            senza chiamare di nuovo fn.
            user_id:    il numero dell'utente collegato
            action:     il nome dell'azione, per esempio "request", "block", "chat:send"
            request_id: il codice del tentativo mandato dalla pagina (check_request_id)
            fn:         la funzione da eseguire, senza parametri. In C sarebbe un
                        puntatore a funzione, result (*fn)(void)
        """
        key = (user_id, action, request_id)
        with self._user_lock(user_id):
            # Si dimenticano le risposte troppo vecchie, poi si cerca quella di questa chiave
            with self._lock:
                now = self._clock()
                kept = {}
                for saved_key, saved_value in self._results.items():
                    if now - saved_value[0] < self._seconds:
                        kept[saved_key] = saved_value
                self._results = kept
                saved = self._results.get(key)

            # Prima volta: si esegue fn e si salva la risposta (anche un errore del
            # contratto, EventError). try / except: un errore lanciato dentro fn si
            # prende qui invece di uscire subito dalla funzione. Gli altri errori
            # escono e non si salvano
            if saved is None:
                try:
                    result = ("ok", fn())
                except EventError as exc:
                    result = ("error", exc)
                with self._lock:
                    self._results[key] = (self._clock(), result)
            else:
                result = saved[1]

        # result: ("ok", dati) oppure ("error", l'errore da rilanciare)
        kind = result[0]
        value = result[1]
        if kind == "error":
            raise value
        return value


# recent: le risposte già date dalle rotte degli amici
recent = RecentRequests()


# Dati in ingresso


def check_request_id(value):
    """Controlla request_id e lo restituisce; altrimenti EventError("invalid_data").

    In parole semplici:
        check_request_id(value)
        Per esempio check_request_id("3f2a-…") -> "3f2a-…"; check_request_id("") e
        check_request_id(12) -> errore. Va bene un testo da 1 a REQUEST_ID_MAX caratteri.
        value: il campo request_id del JSON della pagina (lo crea la pagina, uno per tentativo)
    """
    if not isinstance(value, str) or len(value) < 1 or len(value) > REQUEST_ID_MAX:
        raise EventError("invalid_data", "Manca request_id, oppure non è valido.")
    return value


def check_user_id(value):
    """Controlla un numero di utente e lo restituisce; altrimenti EventError("invalid_data").

    In parole semplici:
        check_user_id(value)
        Per esempio check_user_id(7) -> 7; check_user_id("7"), check_user_id(0) e
        check_user_id(True) -> errore.
        value: il numero di un utente, dal JSON della pagina o dall'indirizzo
    """
    # bool è un int per Python: True non è un numero di utente
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise EventError("invalid_data", "user_id deve essere il numero di un utente.")
    return value


def check_username(value):
    """Lo username scritto per cercare un utente, senza spazi all'inizio e alla fine (P63:
    dal telefono capita di aggiungerne uno). Non è una correzione silenziosa di un dato
    valido: uno username non contiene mai spazi (D7). Uno spazio in mezzo resta, e
    l'utente non si trova.

    In parole semplici:
        check_username(value)
        Per esempio check_username(" Nina ") -> "Nina"; check_username("") -> errore.
        value: il campo username del JSON (la casella "Aggiungi un amico" del pannello)
    """
    maximum = current_app.config["USERNAME_MAX"]
    if isinstance(value, str):
        value = value.strip()
    if not isinstance(value, str) or len(value) < 1 or len(value) > maximum:
        raise EventError("invalid_data", f"Scrivi uno username (al massimo {maximum} caratteri).")
    return value


# Lettura


def overview(user_id):
    """Lista del contratto (GET /api/friends/): amici, richieste, bloccati e contatori.

    In parole semplici:
        overview(7)
        Restituisce per esempio {"friends": [{"user_id": 8, "username": "Nina",
        "avatar": "coppe", "presence": "online", "unread": 2}], "requests_in": [...],
        "requests_out": [...], "blocked": [...], "counters": {"requests_in": 1,
        "unread_messages": 2}}.
        user_id: il numero dell'utente collegato (da friends/routes.py)
    """
    # unread: i messaggi non letti per mittente, per esempio {8: 2}
    unread = friend_repo.unread_by_sender(user_id)

    # Gli amici, ognuno con la presenza e i messaggi non letti
    friends = []
    for friend_user in friend_repo.friends_of(user_id):
        friend = _user(friend_user)
        friend["presence"] = presence(friend_user.id)
        friend["unread"] = unread.get(friend_user.id, 0)
        friends.append(friend)
    # sort è "stabile": dentro ogni gruppo resta l'ordine per nome dato da friends_of
    friends.sort(key=_presence_rank)

    # Le richieste ricevute e mandate: ogni riga è una coppia (utente, data della richiesta)
    requests_in = []
    for other, sent_at in friend_repo.requests_in(user_id):
        request = _user(other)
        request["sent_at"] = iso_utc(sent_at)
        requests_in.append(request)
    requests_out = []
    for other, sent_at in friend_repo.requests_out(user_id):
        request = _user(other)
        request["sent_at"] = iso_utc(sent_at)
        requests_out.append(request)

    blocked = []
    for other in friend_repo.blocked_by(user_id):
        blocked.append(_user(other))

    return {
        "friends": friends,
        "requests_in": requests_in,
        "requests_out": requests_out,
        "blocked": blocked,
        "counters": {"requests_in": len(requests_in), "unread_messages": sum(unread.values())},
    }


def _presence_rank(friend):
    """La posizione del gruppo di un amico nella lista: 0 online, 1 in partita, 2 offline.

    In parole semplici:
        _presence_rank({"presence": "in_game", ...}) = 1
        La usa friends.sort in overview come "chiave": la lista si ordina per questo numero.
    """
    return PRESENCE_ORDER[friend["presence"]]


def presence(user_id):
    """Dove si trova un utente: "in_game", "online" o "offline".

    In parole semplici:
        presence(8)
        "in_game" se ha una partita in corso (room_manager), "online" se ha una scheda
        collegata in tempo reale (presence.py), altrimenti "offline".
        user_id: il numero di un amico (da overview e da friends_events.py)
    """
    if find_room_of_user(user_id) is not None:
        return "in_game"
    if online_users.is_online(user_id):
        return "online"
    return "offline"


def _changed(user_id, reason):
    """friends:changed (contratto 5.2) a tutte le schede di quell'utente (P47).

    In parole semplici:
        _changed(8, "request_received")
        Manda l'evento al "canale" dell'utente (user_channel, una stanza di
        Socket.IO con tutte le sue schede): la pagina rilegge la lista degli amici.
    """
    socketio.emit("friends:changed", {"reason": reason}, to=user_channel(user_id))


def _user(user):
    """I dati pubblici di un utente nella forma del contratto.

    In parole semplici:
        _user(nina) = {"user_id": 8, "username": "Nina", "avatar": "coppe"}
        Un dizionario nuovo ogni volta: chi lo riceve può aggiungere altri campi.
    """
    return {"user_id": user.id, "username": user.username, "avatar": user.avatar}


def iso_utc(moment):
    """Data e ora del database (UTC) nel formato del contratto: 2026-09-28T14:03:12.000Z.

    In parole semplici:
        iso_utc(moment)
        moment: un datetime letto dal database (già in UTC, senza fuso orario).
        I microsecondi diventano millesimi a tre cifre ("// 1000" è la divisione
        intera; ":03d" scrive il numero con tre cifre, per esempio 7 -> "007").
    """
    return moment.strftime("%Y-%m-%dT%H:%M:%S.") + f"{moment.microsecond // 1000:03d}Z"


# Scritture


def send_request(user_id, request_id, username):
    """POST /api/friends/requests: manda una richiesta di amicizia e restituisce l'utente.

    In parole semplici:
        send_request(7, "a1b2", "Nina")
        Restituisce per esempio {"user_id": 8, "username": "Nina", "avatar": "coppe",
        "sent_at": "2026-09-28T14:03:12.000Z"}; Nina riceve friends:changed.
        Lo stesso request_id ripetuto riceve la stessa risposta (recent.run).
    """
    check_request_id(request_id)
    username = check_username(username)

    # attempt: il lavoro vero, che recent.run esegue solo la prima volta
    def attempt():
        return _sent(_write(_send_request, user_id, username))

    return recent.run(user_id, "request", request_id, attempt)


def _sent(result):
    """Dopo una richiesta salvata, avvisa chi la riceve; restituisce result così com'è.

    In parole semplici:
        _sent({"user_id": 8, ...}): friends:changed "request_received" alle schede di 8.
    """
    _changed(result["user_id"], "request_received")
    return result


# P65: gli avvisi arrivano a tutti e due, anche alle schede di chi ha fatto l'azione:
# la home (lista degli amici da invitare) e le altre schede rileggono la lista. Prima
# chi accettava una richiesta non vedeva il nuovo amico nella carta "Gioca con un amico"
# finché non ricaricava la pagina.


def accept_request(user_id, other_id):
    """POST /api/friends/requests/<id>/accept: accetta la richiesta di other_id.

    In parole semplici:
        accept_request(7, 8): 7 e 8 diventano amici. La seconda volta non fa niente.
    """
    if _write(_accept_request, user_id, check_user_id(other_id)):
        _changed(other_id, "request_accepted")
        _changed(user_id, "request_accepted")


def decline_request(user_id, other_id):
    """POST /api/friends/requests/<id>/decline: rifiuta la richiesta di other_id.

    In parole semplici:
        decline_request(7, 8): cancella la richiesta che 8 ha mandato a 7.
    """
    if _write(_delete_pending, user_id, other_id, user_id):
        _changed(other_id, "request_declined")
        _changed(user_id, "request_declined")


def cancel_request(user_id, other_id):
    """DELETE /api/friends/requests/<id>: annulla la richiesta mandata a other_id.

    In parole semplici:
        cancel_request(7, 8): cancella la richiesta che 7 ha mandato a 8.
    """
    if _write(_delete_pending, user_id, user_id, other_id):
        _changed(other_id, "request_declined")  # la richiesta che aveva ricevuto non c'è più
        _changed(user_id, "request_declined")


def remove_friend(user_id, other_id):
    """DELETE /api/friends/<id>: toglie l'amicizia e annulla l'invito a partita tra i due.

    In parole semplici:
        remove_friend(7, 8): 7 e 8 non sono più amici.
    """
    if _write(_remove_friend, user_id, other_id):
        invites.cancel_all_of(user_id, only_with=other_id)
        _changed(other_id, "friend_removed")
        _changed(user_id, "friend_removed")


def block(user_id, request_id, other_id):
    """POST /api/friends/blocks: blocca other_id (D23).

    In parole semplici:
        block(7, "c3d4", 8): 7 blocca 8. Lo stesso request_id ripetuto riceve la
        stessa risposta (recent.run).
    """
    check_request_id(request_id)
    check_user_id(other_id)

    # attempt: il lavoro vero, che recent.run esegue solo la prima volta
    def attempt():
        return _blocked(user_id, other_id)

    return recent.run(user_id, "block", request_id, attempt)


def _blocked(user_id, other_id):
    """Salva il blocco, annulla l'invito tra i due e manda gli avvisi.

    In parole semplici:
        _blocked(7, 8)
        Chi è bloccato riceve "friend_removed" (solo se aveva l'amicizia o una
        richiesta), mai "blocked": non deve sapere del blocco.
    """
    removed = _write(_block, user_id, other_id)
    invites.cancel_all_of(user_id, only_with=other_id)
    if removed:
        _changed(other_id, "friend_removed")  # sparisce dalla sua lista, senza sapere del blocco
    _changed(user_id, "blocked")  # le altre schede di chi blocca


def unblock(user_id, other_id):
    """DELETE /api/friends/blocks/<id>: sblocca other_id.

    In parole semplici:
        unblock(7, 8): 7 sblocca 8; la seconda volta non fa niente.
    """
    if _write(_unblock, user_id, other_id):
        _changed(user_id, "blocked")  # solo chi sblocca: l'elenco dei bloccati è cambiato; l'altro non lo sa


def _write(action, *args):
    """Esegue `action` in una transazione: commit se va bene, altrimenti rollback.

    Prima chiude la transazione aperta dalle letture precedenti (per esempio il
    caricamento dell'utente del login) e apre la nuova in READ COMMITTED: con il
    livello predefinito di MySQL (REPEATABLE READ) le letture vedrebbero i dati
    com'erano alla prima lettura, e dopo aver aspettato il lock degli utenti non
    vedrebbero la richiesta appena salvata da un'altra scheda.

    In parole semplici:
        _write(action, *args)
        Per esempio _write(_accept_request, 7, 8) chiama _accept_request(7, 8) dentro
        la transazione e restituisce quello che restituisce.
        action: una delle funzioni _send_request, _accept_request, ... qui sotto
                (in C, un puntatore a funzione)
        *args:  i parametri da passarle, che sono 2 o 3 a seconda della funzione:
                l'asterisco raccoglie tutti quelli dati in una tupla, e action(*args)
                li ripassa uno per uno. Serve davvero: le funzioni hanno parametri diversi.
        try / except: con un errore qualsiasi si annulla la transazione (rollback) e
        lo si rilancia (raise) a chi ha chiamato.
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
    """La richiesta di amicizia, dentro la transazione: controlli e scrittura.

    In parole semplici:
        _send_request(7, "Nina")
        Restituisce i dati di Nina con "sent_at", oppure lancia EventError con il
        motivo (utente che non c'è, te stesso, bloccato, già amici, limite).
    """
    target = user_repo.get_by_username(username)
    if target is None:
        raise EventError("not_found", NO_SUCH_USER)
    if target.id == user_id:
        raise EventError("invalid_data", SELF_REQUEST)

    # Si bloccano le righe dei due utenti; se l'altro è stato cancellato nel frattempo non c'è
    if target.id not in friend_repo.lock_users(user_id, target.id):
        raise EventError("not_found", NO_SUCH_USER)
    if friend_repo.get_block(target.id, user_id) is not None:
        raise EventError("not_found", NO_SUCH_USER)  # chi ti ha bloccato risulta inesistente (P8)
    if friend_repo.get_block(user_id, target.id) is not None:
        raise EventError("blocked", YOU_BLOCKED)

    # C'è già una riga tra i due: amicizia, richiesta tua o richiesta sua
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
    data = _user(target)
    data["sent_at"] = iso_utc(row.requested_at)
    return data


def _accept_request(user_id, other_id):
    """Accetta, dentro la transazione; True se è cambiato qualcosa.

    In parole semplici:
        _accept_request(7, 8): False se sono già amici (seconda volta), EventError se
        8 non ha mandato una richiesta a 7 o se si supera il limite.
    """
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
    """Cancella la richiesta in attesa da requester_id ad addressee_id; True se c'era.

    In parole semplici:
        _delete_pending(7, 8, 7): rifiuto (8 l'aveva mandata a 7);
        _delete_pending(7, 7, 8): annullamento (7 l'aveva mandata a 8).
        user_id non serve al conto, ma tiene la stessa forma delle altre funzioni di _write.
    """
    friend_repo.lock_users(requester_id, addressee_id)
    row = friend_repo.get_pair(requester_id, addressee_id)
    if row is not None and row.status == friend_repo.PENDING and row.requester_id == requester_id:
        friend_repo.delete(row)
        return True
    return False


def _remove_friend(user_id, other_id):
    """Cancella l'amicizia, dentro la transazione; True se c'era.

    In parole semplici:
        _remove_friend(7, 8): False se non erano amici (seconda volta).
    """
    friend_repo.lock_users(user_id, other_id)
    row = friend_repo.get_pair(user_id, other_id)
    if row is not None and row.status == friend_repo.ACCEPTED:
        friend_repo.delete(row)
        log.info("Amicizia tolta tra %s e %s", user_id, other_id)
        return True
    return False


def _block(user_id, other_id):
    """Salva il blocco e toglie amicizia o richieste; True se l'altro aveva una riga con te.

    In parole semplici:
        _block(7, 8)
        Restituisce True se tra 7 e 8 c'era un'amicizia o una richiesta (la lista di 8
        cambia), False altrimenti; EventError se 8 è 7 stesso o non esiste.
    """
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
    """Cancella il blocco, dentro la transazione; True se c'era.

    In parole semplici:
        _unblock(7, 8): False se 7 non aveva bloccato 8 (seconda volta).
    """
    friend_repo.lock_users(user_id, other_id)
    row = friend_repo.get_block(user_id, other_id)
    if row is not None:
        friend_repo.delete(row)
        return True
    return False


def _check_limits(user_id, other_id):
    """EventError("limit_reached") se uno dei due ha già FRIENDS_MAX amici (D26).

    In parole semplici:
        _check_limits(7, 8)
        Per esempio con FRIENDS_MAX = 100 e 7 con 100 amici: "Hai già 100 amici: è il
        massimo." (format mette il numero al posto di {n}).
    """
    maximum = current_app.config["FRIENDS_MAX"]
    if friend_repo.count_friends(user_id) >= maximum:
        raise EventError("limit_reached", MY_LIMIT.format(n=maximum))
    if friend_repo.count_friends(other_id) >= maximum:
        raise EventError("limit_reached", THEIR_LIMIT.format(n=maximum))
