"""Chat tra amici (P48; decisioni D24, D25, D26; contratto 5.4).

- Si scrive solo a un amico, uno a uno. Se l'amicizia finisce o c'è un blocco la
  conversazione resta leggibile ma non si scrive più: `can_write` falso e
  `cannot_write` = "not_friends" oppure "blocked". Chi è stato bloccato lo vede
  scritto nella chat e non può scrivere (scelta di Giuseppe); `chat:send` risponde
  `not_friends` o `blocked`.
- Testo: non vuoto né fatto solo di spazi, al massimo CHAT_MAX_LENGTH caratteri (1000),
  salvato così com'è; al massimo un messaggio ogni CHAT_MIN_INTERVAL_SECONDS per
  utente (`too_fast` con `retry_after` in secondi interi).
- I controlli su amicizia e blocchi stanno nella stessa transazione della scrittura,
  dopo aver bloccato le righe dei due utenti (come friend_service, P45), in READ
  COMMITTED: un blocco appena salvato da un'altra scheda si vede.
- `chat:send` porta request_id: lo stesso tentativo riceve la stessa risposta.
- La cronologia: al massimo HISTORY_LIMIT messaggi, dal più vecchio al più nuovo;
  aprire la chat (before_id null) segna come letti i messaggi ricevuti.
- I messaggi non si cancellano mai (D24): spariscono solo con l'account (P5).
Il testo dei messaggi non va mai nei log; nei log solo numeri di utente.

Cosa contiene:
    RateLimit / rate_limit           un messaggio al secondo per utente, in memoria
    message_data(row)                un messaggio nella forma del contratto
    check_text(text)                 controlla il testo: check_text("ciao") -> "ciao"
    check_before_id(v)               controlla before_id: check_before_id(None) -> None
    cannot_write(me, other)          None, "blocked" o "not_friends"
    history(me, other, before_id)    chat:history, la cronologia
    read(me, other)                  chat:read, segna come letti
    send(me, rid, other, text, deliver)   chat:send, salva e recapita un messaggio

DA DOVE ARRIVANO I DATI: la finestra della chat della SPA (ChatWindow.tsx, attraverso
frontend/src/socket/) manda gli eventi chat:history, chat:send e chat:read;
app/sockets/chat_events.py li riceve e chiama history, send e read con il numero
dell'utente collegato e i campi dell'evento (user_id dell'amico, before_id, text,
request_id).
"""

import logging
import math
import threading
import time

from flask import current_app

from app.extensions import db
from app.realtime.events import EventError
from app.repositories import chat_repo, friend_repo, user_repo
from app.services.friend_service import (
    RecentRequests,
    check_request_id,
    check_user_id,
    iso_utc,
)

log = logging.getLogger(__name__)

HISTORY_LIMIT = 50
# I messaggi che vede l'utente
NOT_FRIENDS = "Non siete più amici: puoi leggere la conversazione, ma non scrivere."
BLOCKED = "Bloccato: non potete più scrivervi."

# recent: le risposte già date a chat:send, per request_id (RecentRequests di friend_service.py)
recent = RecentRequests()


class RateLimit:
    """Un messaggio ogni `seconds` secondi per utente, in memoria.

    In parole semplici:
        RateLimit(clock)
        Una "classe": tiene insieme l'ora dell'ultimo messaggio di ogni utente e le
        funzioni che la usano (take, give_back), come una struct del C con le sue funzioni.
        clock: facoltativo; la funzione che dà l'ora in secondi (time.monotonic, un
               orologio che non torna mai indietro); i test ne passano una finta.
    """

    def __init__(self, clock=time.monotonic):
        self._clock = clock
        # _lock: il "lucchetto" del dizionario: i messaggi arrivano in thread diversi,
        # e con "with self._lock:" uno solo alla volta lo legge o lo cambia
        self._lock = threading.Lock()
        self._last = {}  # user_id -> ora dell'ultimo messaggio, per esempio {7: 5031.2}

    def take(self, user_id, seconds):
        """Conta un messaggio; troppo presto dopo il precedente → EventError("too_fast").

        In parole semplici:
            take(user_id, seconds)
            Per esempio take(7, 1): se 7 ha scritto 0,3 secondi fa, errore con
            retry_after = 1 (math.ceil arrotonda per eccesso: 0,7 -> 1); altrimenti
            si ricorda l'ora di adesso.
            seconds: CHAT_MIN_INTERVAL_SECONDS di config.py (da _send)
        """
        with self._lock:
            now = self._clock()
            last = self._last.get(user_id)
            if last is not None and now - last < seconds:
                raise EventError("too_fast", "Un messaggio al secondo: aspetta un momento.",
                                 retry_after=math.ceil(seconds - (now - last)))
            self._last[user_id] = now

    def give_back(self, user_id):
        """Il messaggio non è stato salvato: non conta per il limite.

        In parole semplici:
            give_back(7): dimentica l'ultimo messaggio di 7 (lo usa _send dopo un
            errore, e i test per azzerare il limite).
        """
        with self._lock:
            self._last.pop(user_id, None)  # pop con None: niente errore se non c'è


# rate_limit: l'unico limite dei messaggi del server
rate_limit = RateLimit()


def message_data(row):
    """Un messaggio salvato nella forma del contratto (5.4).

    In parole semplici:
        message_data(row)
        Per esempio {"id": 31, "from_user_id": 7, "to_user_id": 8, "text": "ciao",
        "sent_at": "2026-09-28T14:03:12.345Z"}.
        row: una riga della tabella messaggi (un ChatMessage, da chat_repo)
    """
    return {
        "id": row.id,
        "from_user_id": row.sender_id,
        "to_user_id": row.recipient_id,
        "text": row.text,
        "sent_at": iso_utc(row.sent_at),
    }


def check_text(text):
    """Controlla il testo di un messaggio e lo restituisce così com'è; altrimenti EventError.

    In parole semplici:
        check_text(text)
        Per esempio check_text(" ciao ") -> " ciao " (gli spazi restano);
        check_text("   ") -> errore "Scrivi un messaggio."
        text: il campo text dell'evento chat:send
    """
    maximum = current_app.config["CHAT_MAX_LENGTH"]
    if not isinstance(text, str) or not text.strip():
        raise EventError("invalid_data", "Scrivi un messaggio.")
    if len(text) > maximum:
        raise EventError("invalid_data", f"Al massimo {maximum} caratteri.")
    return text


def check_before_id(value):
    """Controlla before_id e lo restituisce; altrimenti EventError("invalid_data").

    In parole semplici:
        check_before_id(value)
        Per esempio check_before_id(None) -> None (gli ultimi messaggi);
        check_before_id(31) -> 31 (i messaggi prima del 31, per scorrere indietro).
        value: il campo before_id dell'evento chat:history
    """
    if value is None:
        return None
    # bool è un int per Python: True non è il numero di un messaggio
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise EventError("invalid_data", "before_id deve essere il numero di un messaggio, oppure null.")
    return value


def _other(user_id, other_id):
    """Controlla il numero dell'amico della chat e lo restituisce; altrimenti EventError.

    In parole semplici:
        _other(7, 8) -> 8; _other(7, 7) -> errore (te stesso); errore anche se 8 non esiste.
        other_id: il campo user_id dell'evento
    """
    check_user_id(other_id)
    if other_id == user_id:
        raise EventError("invalid_data", "Non puoi scrivere a te stesso.")
    if user_repo.get_by_id(other_id) is None:
        raise EventError("not_found", "Questo utente non esiste.")
    return other_id


def cannot_write(user_id, other_id):
    """None se i due possono scriversi, altrimenti "blocked" o "not_friends".

    In parole semplici:
        cannot_write(7, 8)
        "blocked" se uno dei due ha bloccato l'altro, "not_friends" se non sono amici,
        None se sono amici.
    """
    if friend_repo.get_block(user_id, other_id) is not None or friend_repo.get_block(other_id, user_id) is not None:
        return "blocked"
    row = friend_repo.get_pair(user_id, other_id)
    if row is None or row.status != friend_repo.ACCEPTED:
        return "not_friends"
    return None


# --- Lettura ---


def history(user_id, other_id, before_id):
    """chat:history: messaggi, has_more, can_write e cannot_write. Aprire la chat
    (before_id None) segna come letti i messaggi ricevuti.

    In parole semplici:
        history(7, 8, None)
        Restituisce per esempio {"messages": [{"id": 30, ...}, {"id": 31, ...}],
        "has_more": False, "can_write": True, "cannot_write": None}.
        before_id: None per gli ultimi messaggi, oppure il numero del messaggio più
                   vecchio già mostrato, per caricare quelli prima
    """
    other_id = _other(user_id, other_id)
    before_id = check_before_id(before_id)

    # conversation restituisce una coppia: (i messaggi, se ce ne sono di più vecchi)
    page = chat_repo.conversation(user_id, other_id, before_id, HISTORY_LIMIT)
    rows = page[0]
    has_more = page[1]
    reason = cannot_write(user_id, other_id)
    if before_id is None:
        chat_repo.mark_read(user_id, other_id, chat_repo.utc_now())
        db.session.commit()

    messages = []
    for row in rows:
        messages.append(message_data(row))
    return {
        "messages": messages,
        "has_more": has_more,
        "can_write": reason is None,
        "cannot_write": reason,
    }


def read(user_id, other_id):
    """chat:read: con la chat aperta, segna come letti i messaggi appena arrivati.

    In parole semplici:
        read(7, 8): i messaggi di 8 a 7 non ancora letti diventano letti adesso.
    """
    other_id = _other(user_id, other_id)
    chat_repo.mark_read(user_id, other_id, chat_repo.utc_now())
    db.session.commit()


# --- Scrittura ---


def send(user_id, request_id, other_id, text, deliver=None):
    """chat:send: {"message": messaggio salvato}. `deliver(messaggio)` lo recapita (una
    volta sola: lo stesso request_id ripetuto riceve la risposta senza recapitarlo di nuovo).

    In parole semplici:
        send(7, "e5f6", 8, "ciao", deliver)
        Restituisce per esempio {"message": {"id": 31, "from_user_id": 7, ...}}.
        deliver: facoltativo; la funzione di chat_events.py che manda il messaggio al
                 destinatario e alle altre schede di chi scrive (in C, un puntatore a
                 funzione); se manca (None) non si recapita niente
    """
    check_request_id(request_id)

    # attempt: il lavoro vero, che recent.run esegue solo la prima volta
    def attempt():
        message = _send(user_id, other_id, text)
        if deliver is not None:
            deliver(message)
        return {"message": message}

    return recent.run(user_id, "chat:send", request_id, attempt)


def _send(user_id, other_id, text):
    """Controlli, limite di frequenza e scrittura; restituisce il messaggio del contratto.

    In parole semplici:
        _send(7, 8, "ciao")
        Se la scrittura fallisce, il messaggio non conta per il limite (give_back);
        try / except: con un errore qualsiasi si restituisce il "posto" e lo si
        rilancia (raise) a chi ha chiamato.
    """
    other_id = _other(user_id, other_id)
    text = check_text(text)
    rate_limit.take(user_id, current_app.config["CHAT_MIN_INTERVAL_SECONDS"])
    try:
        return _write(user_id, other_id, text)
    except Exception:
        rate_limit.give_back(user_id)
        raise


def _write(user_id, other_id, text):
    """Salva il messaggio in una transazione, dopo aver ricontrollato amicizia e blocchi.

    In parole semplici:
        _write(7, 8, "ciao")
        Come _write di friend_service.py: prima chiude la transazione delle letture
        precedenti e ne apre una in READ COMMITTED, così vede un blocco appena salvato
        da un'altra scheda; poi blocca le righe dei due utenti, controlla e scrive.
        Restituisce i dati del messaggio (message_data), preparati prima del commit.
    """
    db.session.rollback()
    db.session.connection(execution_options={"isolation_level": "READ COMMITTED"})
    try:
        friend_repo.lock_users(user_id, other_id)
        reason = cannot_write(user_id, other_id)
        if reason == "blocked":
            raise EventError("blocked", BLOCKED)
        if reason == "not_friends":
            raise EventError("not_friends", NOT_FRIENDS)
        row = chat_repo.add(user_id, other_id, text, chat_repo.utc_now())
        data = message_data(row)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    log.info("Messaggio %s da %s a %s", data["id"], user_id, other_id)
    return data
