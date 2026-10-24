"""Rotte: richieste di amicizia, lista amici e blocchi (P45; contratto 2.2).

Richieste HTTP in JSON, tutte con il login; quelle che modificano qualcosa (POST,
DELETE) mandano il codice CSRF nell'intestazione X-CSRFToken (contratto 1.5).
Rispondono nella forma del contratto (1.2): {"ok": true, "data": ...} oppure
{"ok": false, "error": {"code", "message"}} con il codice HTTP della tabella.
La logica sta in app/services/friend_service.py. Gli indirizzi sono sotto
/api/friends/ (prefisso in __init__.py), come tutte le rotte di dati.

Cosa contiene:
    HTTP_STATUS               il codice HTTP di ogni errore, per esempio "not_found" → 404
    json_endpoint             il decoratore che mettono tutte le rotte (login e risposta)
    body()                    il corpo JSON della richiesta, per esempio {"username": "Lucia"}
    GET    /                              overview: la lista (amici, richieste, bloccati)
    POST   /requests                      send_request: manda una richiesta
    POST   /requests/<user_id>/accept     accept_request: accetta
    POST   /requests/<user_id>/decline    decline_request: rifiuta
    DELETE /requests/<user_id>            cancel_request: annulla una richiesta mandata
    DELETE /<user_id>                     remove_friend: toglie un amico
    POST   /blocks                        block: blocca un utente
    DELETE /blocks/<user_id>              unblock: lo sblocca

DA DOVE ARRIVANO I DATI: dal pannello amici della SPA (frontend/src/api/friends.ts,
usato da FriendsPanel.tsx e dalla home per gli amici da invitare): il numero
dell'utente nell'indirizzo, gli altri campi nel corpo JSON; chi è collegato lo dice
Flask-Login (current_user, dal cookie della sessione).
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
    e risposta del contratto; un errore imprevisto passa a app/errors.py (server_error, 500).

    In parole semplici:
        @json_endpoint sopra una rotta (un "decoratore": json_endpoint(fn) riceve la
        funzione della rotta e restituisce una funzione nuova, wrapper, che Flask
        chiama al suo posto). wrapper:
          1. senza login risponde subito not_logged_in (401) e la rotta non parte;
          2. chiama la rotta; quello che restituisce diventa {"ok": true, "data": ...},
             oppure solo {"ok": true} se la rotta non ha dati (restituisce None);
          3. se la rotta lancia EventError (per esempio "not_found"), risponde
             {"ok": false, "error": ...} con il codice di HTTP_STATUS (400 se il
             codice non è nella tabella).

        fn: la funzione della rotta, per esempio overview. In C sarebbe un puntatore
            a funzione.

        Restituisce: wrapper.
    """

    # @functools.wraps(fn): wrapper prende il nome di fn (per esempio "overview"):
    # Flask usa il nome per distinguere le rotte, e senza tutte si chiamerebbero
    # "wrapper".
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        # *args, **kwargs: i parametri che Flask passa alla rotta (per esempio
        # user_id=31 dall'indirizzo), tutti, qualunque siano; servono perché le
        # rotte hanno parametri diversi, e si passano così come sono a fn.
        if not current_user.is_authenticated:
            return error("not_logged_in"), 401
        try:
            return ok(fn(*args, **kwargs))
        except EventError as exc:
            status = HTTP_STATUS.get(exc.code, 400)
            # **exc.extra: i campi in più dell'errore (per esempio retry_after=3)
            # passati a error con il loro nome
            return error(exc.code, exc.message, **exc.extra), status

    return wrapper


def body():
    """Il corpo JSON della richiesta, che deve essere un oggetto.

    In parole semplici:
        data = body()
        Per esempio {"request_id": "…", "username": "Lucia"}. Se il corpo non è un
        oggetto JSON (manca, è un elenco, un numero, ...) lancia EventError
        "invalid_data", che json_endpoint trasforma nella risposta 400.
    """
    # silent=True: con un corpo che non è JSON restituisce None invece di un errore
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise EventError("invalid_data", "Il corpo della richiesta deve essere un oggetto JSON.")
    return data


# I decoratori di ogni rotta, dal basso verso l'alto: json_endpoint avvolge la
# funzione (login e risposta), poi @bp.get / @bp.post / @bp.delete dice a Flask
# a quale metodo e indirizzo risponde. <int:user_id> nell'indirizzo prende un numero
# e lo passa alla funzione come user_id (un testo al suo posto dà 404).
@bp.get("/")
@json_endpoint
def overview():
    """GET /api/friends/: la lista del pannello amici.

    In parole semplici:
        Amici (con chi è online e i messaggi non letti), richieste ricevute e
        mandate, bloccati e contatori, da friend_service.overview.
    """
    return friend_service.overview(current_user.id)


@bp.post("/requests")
@json_endpoint
def send_request():
    """POST /api/friends/requests: manda una richiesta di amicizia.

    In parole semplici:
        Corpo {"request_id", "username"}: request_id è la chiave anti-doppione
        (contratto 1.3), username chi si vuole come amico. Controlli e risposta li
        fa friend_service.send_request.
    """
    data = body()
    return friend_service.send_request(current_user.id, data.get("request_id"), data.get("username"))


@bp.post("/requests/<int:user_id>/accept")
@json_endpoint
def accept_request(user_id):
    """POST /api/friends/requests/<user_id>/accept: accetta la richiesta di user_id.

    In parole semplici:
        Per esempio /api/friends/requests/31/accept accetta la richiesta dell'utente
        31. Risponde {"ok": true}.
    """
    friend_service.accept_request(current_user.id, user_id)


@bp.post("/requests/<int:user_id>/decline")
@json_endpoint
def decline_request(user_id):
    """POST /api/friends/requests/<user_id>/decline: rifiuta la richiesta di user_id.

    In parole semplici:
        Come accept_request, ma la richiesta si rifiuta.
    """
    friend_service.decline_request(current_user.id, user_id)


@bp.delete("/requests/<int:user_id>")
@json_endpoint
def cancel_request(user_id):
    """DELETE /api/friends/requests/<user_id>: annulla la richiesta mandata a user_id.

    In parole semplici:
        Per chi ha mandato una richiesta e ci ripensa prima della risposta.
    """
    friend_service.cancel_request(current_user.id, user_id)


@bp.delete("/<int:user_id>")
@json_endpoint
def remove_friend(user_id):
    """DELETE /api/friends/<user_id>: toglie user_id dagli amici.

    In parole semplici:
        Per esempio DELETE /api/friends/31. I suoi inviti aperti si annullano
        (lo fa friend_service.remove_friend).
    """
    friend_service.remove_friend(current_user.id, user_id)


@bp.post("/blocks")
@json_endpoint
def block():
    """POST /api/friends/blocks: blocca un utente.

    In parole semplici:
        Corpo {"request_id", "user_id"}: la chiave anti-doppione e il numero
        dell'utente da bloccare.
    """
    data = body()
    friend_service.block(current_user.id, data.get("request_id"), data.get("user_id"))


@bp.delete("/blocks/<int:user_id>")
@json_endpoint
def unblock(user_id):
    """DELETE /api/friends/blocks/<user_id>: sblocca user_id.

    In parole semplici:
        Per esempio DELETE /api/friends/blocks/31.
    """
    friend_service.unblock(current_user.id, user_id)
