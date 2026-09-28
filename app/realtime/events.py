"""Nomi degli eventi e forma delle risposte in tempo reale (contratto, 1.1 e 1.2).

Ogni evento che la pagina manda riceve una risposta (ack):
    {"ok": true, "data": {...}}  oppure  {"ok": false, "error": {"code", "message"}}
I gestori lanciano EventError con un codice del contratto; `handler` la trasforma
nella risposta, e un errore imprevisto diventa `server_error` (dettaglio solo nel log).
Gli errori vanno solo a chi ha mandato la richiesta: sono la risposta, mai un evento.
"""

import functools
import logging

log = logging.getLogger(__name__)

# Motivo del rifiuto della connessione senza login (contratto 1.4)
NOT_LOGGED_IN = "not_logged_in"

# Stanze Socket.IO (canali): tutte le schede di un utente, e i giocatori di una stanza di gioco
def user_channel(user_id):
    return f"user:{user_id}"


def room_channel(room_id):
    return f"room:{room_id}"


# Codici di errore del contratto (1.2) e messaggio predefinito
ERRORS = {
    "invalid_data": "Dati non validi.",
    "not_logged_in": "Accedi per continuare.",
    "not_allowed": "Non puoi fare questa azione.",
    "blocked": "Non puoi interagire con questo utente.",
    "not_found": "Non esiste o non esiste più.",
    "not_friends": "Dovete essere amici.",
    "not_your_turn": "Non è il tuo turno.",
    "illegal_move": "Mossa non ammessa.",
    "stale_state": "La partita è cambiata: riprova.",
    "busy": "Già in partita, in coda o con un invito in sospeso.",
    "already_exists": "Esiste già.",
    "request_from_them": "Ti ha già mandato una richiesta: accettala.",
    "limit_reached": "Hai raggiunto il limite.",
    "too_fast": "Troppo veloce: aspetta un momento.",
    "expired": "È scaduto.",
    "offline": "Non è collegato.",
    "server_error": "Errore del server: riprova.",
}


class EventError(Exception):
    """Richiesta rifiutata con un codice del contratto; `extra` finisce in error (es. retry_after)."""

    def __init__(self, code, message=None, **extra):
        if code not in ERRORS:
            raise ValueError(f"codice di errore sconosciuto: {code}")
        super().__init__(code)
        self.code = code
        self.message = message or ERRORS[code]
        self.extra = extra


def ok(data=None):
    return {"ok": True} if data is None else {"ok": True, "data": data}


def error(code, message=None, **extra):
    return {"ok": False, "error": {"code": code, "message": message or ERRORS[code], **extra}}


def handler(fn):
    """Decoratore per i gestori degli eventi: restituisce sempre una risposta del contratto."""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return ok(fn(*args, **kwargs))
        except EventError as exc:
            return error(exc.code, exc.message, **exc.extra)
        except Exception:
            log.exception("Errore imprevisto nell'evento %s", fn.__name__)
            return error("server_error")

    return wrapper
