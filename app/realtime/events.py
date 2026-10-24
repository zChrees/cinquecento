"""Nomi degli eventi e forma delle risposte in tempo reale (contratto, 1.1 e 1.2).

Ogni evento che la pagina manda riceve una risposta (ack):
    {"ok": true, "data": {...}}  oppure  {"ok": false, "error": {"code", "message"}}
I gestori lanciano EventError con un codice del contratto; `handler` la trasforma
nella risposta, e un errore imprevisto diventa `server_error` (dettaglio solo nel log).
Gli errori vanno solo a chi ha mandato la richiesta: sono la risposta, mai un evento.

Cosa contiene:
    NOT_LOGGED_IN              il motivo del rifiuto della connessione senza login
    user_channel(user_id)      il canale di tutte le schede di un utente, per esempio "user:7"
    room_channel(room_id)      il canale dei giocatori di una stanza, per esempio "room:abc"
    ERRORS                     i codici di errore del contratto e il loro messaggio
    EventError(code, ...)      l'errore che un gestore lancia per rifiutare una richiesta
    ok(data)                   la risposta "tutto bene", per esempio {"ok": True, "data": {...}}
    error(code, ...)           la risposta di errore, per esempio {"ok": False, "error": {...}}
    EventLimiter, limiter      il limite di frequenza per scheda (P32)
    handler                    il decoratore che mettono tutti i gestori degli eventi

Un "ack" (acknowledgement, "ricevuta") è la risposta che Socket.IO rimanda alla pagina
per un evento: la pagina manda game:play_card e riceve indietro {"ok": ...}. Un
"canale" (in Socket.IO si chiama "room", da non confondere con la stanza di gioco) è un
gruppo di schede a cui si manda un evento tutto insieme.

DA DOVE ARRIVANO I DATI: i gestori degli eventi di app/sockets/ (con @handler) e le
rotte JSON di app/blueprints/ (ok ed error) usano questo file; la configurazione del
limite (EVENT_BURST, EVENT_RATE_PER_SECOND) arriva da config.py.
"""

import functools
import logging
import math
import threading
import time

from flask import current_app, request
from flask_login import current_user

log = logging.getLogger(__name__)

# Motivo del rifiuto della connessione senza login (contratto 1.4)
NOT_LOGGED_IN = "not_logged_in"


# Stanze Socket.IO (canali): tutte le schede di un utente, e i giocatori di una stanza di gioco
def user_channel(user_id):
    """Il nome del canale di tutte le schede di un utente.

    In parole semplici:
        user_channel(user_id)
        Per esempio user_channel(7) = "user:7". Ogni scheda ci entra al collegamento
        (connection_events.py); mandando un evento a questo canale lo ricevono tutte
        le schede aperte di quell'utente.
    """
    return f"user:{user_id}"


def room_channel(room_id):
    """Il nome del canale dei giocatori di una stanza di gioco.

    In parole semplici:
        room_channel(room_id)
        Per esempio room_channel("abc") = "room:abc". Ci entrano le schede al tavolo
        (game:join); la stanza ci manda game:state e le frasi.
    """
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
    """Richiesta rifiutata con un codice del contratto; `extra` finisce in error (es. retry_after).

    In parole semplici:
        raise EventError("busy")
        raise EventError("too_fast", "Aspetta un momento.", retry_after=3)
        Un gestore la lancia per rifiutare una richiesta; handler (qui sotto) la prende
        e la trasforma nella risposta di errore.

        code:    uno dei codici di ERRORS, per esempio "busy"; un codice che non c'è
                 è un errore di chi ha scritto il programma (ValueError).
        message: facoltativo, il messaggio per l'utente; se manca (o è vuoto) si usa
                 quello di ERRORS.
        extra:   altri campi da mettere nella risposta, per esempio retry_after=3.
                 **extra raccoglie in un dizionario tutti i parametri passati con il
                 nome che la funzione non conosce: qui {"retry_after": 3}.
    """

    def __init__(self, code, message=None, **extra):
        if code not in ERRORS:
            raise ValueError(f"codice di errore sconosciuto: {code}")
        # super().__init__: chiama il costruttore di Exception, la classe "madre"
        super().__init__(code)
        self.code = code
        if not message:
            message = ERRORS[code]
        self.message = message
        self.extra = extra


def ok(data=None):
    """La risposta "tutto bene" del contratto (1.2).

    In parole semplici:
        ok()          restituisce {"ok": True}
        ok({"x": 1})  restituisce {"ok": True, "data": {"x": 1}}
        data: facoltativo, i dati della risposta. Arriva da handler (quello che
        restituisce il gestore) o da una rotta JSON.
    """
    if data is None:
        return {"ok": True}
    return {"ok": True, "data": data}


def error(code, message=None, **extra):
    """La risposta di errore del contratto (1.2).

    In parole semplici:
        error("too_fast", retry_after=2)
        Restituisce {"ok": False, "error": {"code": "too_fast", "message": "Troppo
        veloce: aspetta un momento.", "retry_after": 2}}.

        code:    uno dei codici di ERRORS.
        message: facoltativo; se manca (o è vuoto) si usa quello di ERRORS.
        extra:   altri campi, aggiunti dopo code e message (vedi EventError).
    """
    if not message:
        message = ERRORS[code]
    details = {"code": code, "message": message}
    # items(): le coppie (nome, valore) del dizionario, una alla volta
    for name, value in extra.items():
        details[name] = value
    return {"ok": False, "error": details}


class EventLimiter:
    """Limite di frequenza per scheda (P32): un secchio da `burst` gettoni che si riempie
    di `rate` gettoni al secondo; ogni evento ne usa uno. Un solo processo: in memoria.

    In parole semplici:
        limiter.hit(sid, burst, rate)
        Ogni scheda ha un "secchio" di gettoni: ogni evento ne toglie uno, e col tempo
        il secchio si riempie di nuovo, fino a burst. Se è vuoto l'evento si rifiuta.
        Così una scheda può mandare qualche evento di fila, ma non centinaia al secondo.
    """

    PRUNE_EVERY = 256  # ogni tanto si dimenticano le schede ferme da più di un minuto
    IDLE_SECONDS = 60

    def __init__(self, clock=time.monotonic):
        """Crea il limite, con i secchi vuoti.

        In parole semplici:
            EventLimiter()
            clock: facoltativo, la funzione che dà l'ora in secondi (time.monotonic,
                   un orologio che va sempre avanti anche se si cambia l'ora del PC);
                   i test ne passano una finta per far passare il tempo a comando.
        """
        self._clock = clock
        # _lock: un "lucchetto" (come un mutex in C): con "with self._lock:" un solo
        # thread alla volta può leggere o cambiare i secchi
        self._lock = threading.Lock()
        self._buckets = {}  # sid -> (gettoni, ultimo aggiornamento)
        self._hits = 0

    def hit(self, sid, burst, rate):
        """None se l'evento può passare, altrimenti i secondi interi da aspettare.

        In parole semplici:
            hit(sid, burst, rate)
            sid:   il codice della scheda, dato da Socket.IO (request.sid).
            burst: quanti gettoni tiene al massimo il secchio (EVENT_BURST di config.py).
            rate:  quanti gettoni tornano ogni secondo (EVENT_RATE_PER_SECOND).
            Arrivano da handler, qui sotto.

            Restituisce None (passa) oppure i secondi da aspettare, per esempio 2.
        """
        # "with": prende il lucchetto e lo lascia da solo alla fine del blocco, anche
        # se dentro c'è un return o un errore
        with self._lock:
            now = self._clock()
            self._hits += 1

            # Ogni PRUNE_EVERY eventi si tengono solo le schede usate nell'ultimo minuto
            if self._hits % self.PRUNE_EVERY == 0:
                kept = {}
                for key in self._buckets:
                    value = self._buckets[key]
                    if now - value[1] < self.IDLE_SECONDS:
                        kept[key] = value
                self._buckets = kept

            # tokens e last: i gettoni della scheda e l'ora dell'ultimo conto; una
            # scheda nuova parte con il secchio pieno
            bucket = self._buckets.get(sid, (burst, now))
            tokens = bucket[0]
            last = bucket[1]
            # i gettoni tornati dall'ultimo conto, senza superare burst
            tokens = min(burst, tokens + (now - last) * rate)

            if tokens < 1:
                self._buckets[sid] = (tokens, now)
                # quanto manca ad avere un gettone intero, arrotondato in su (almeno 1 s)
                return max(1, math.ceil((1 - tokens) / rate))
            self._buckets[sid] = (tokens - 1, now)
            return None


# limiter: il limite unico per tutte le schede (un solo processo)
limiter = EventLimiter()


def handler(fn):
    """Decoratore per i gestori degli eventi: restituisce sempre una risposta del contratto.

    Prima del gestore (P32): l'utente deve avere ancora il login (un account cancellato
    risulta anonimo) e la scheda non deve superare il limite di frequenza.

    In parole semplici:
        @handler
        def on_play_card(data): ...

        Un decoratore è una funzione che riceve una funzione (fn, il gestore) e ne
        restituisce un'altra (wrapper) che la "avvolge": scrivere @handler sopra il
        gestore vuol dire on_play_card = handler(on_play_card). Quando arriva
        l'evento, Socket.IO chiama wrapper, che:
          1. senza login risponde not_logged_in;
          2. se la scheda va troppo veloce risponde too_fast con retry_after;
          3. altrimenti chiama il gestore e mette quello che restituisce in ok(...);
             un EventError diventa error(...), ogni altro errore server_error.

        fn: il gestore dell'evento, una funzione di app/sockets/.
    """

    # functools.wraps: un decoratore che copia su wrapper il nome e il commento di fn
    # (così nei log e nei test wrapper si chiama come il gestore)
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        """Il gestore "avvolto": controlli, poi il gestore vero, poi la risposta.

        In parole semplici:
            *args e **kwargs raccolgono tutti i parametri che Socket.IO passa (in
            ordine e con il nome) e li ripassano uguali a fn. Servono perché
            handler avvolge gestori con parametri diversi (con o senza data).
        """
        if not current_user.is_authenticated:
            return error("not_logged_in")
        config = current_app.config
        wait = limiter.hit(request.sid, config["EVENT_BURST"], config["EVENT_RATE_PER_SECOND"])
        if wait is not None:
            return error("too_fast", retry_after=wait)
        try:
            return ok(fn(*args, **kwargs))
        except EventError as exc:
            return error(exc.code, exc.message, **exc.extra)
        except Exception:
            # log.exception scrive nel log anche dove è successo l'errore (non lo vede l'utente)
            log.exception("Errore imprevisto nell'evento %s", fn.__name__)
            return error("server_error")

    return wrapper
