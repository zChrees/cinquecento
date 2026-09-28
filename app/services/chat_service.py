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
NOT_FRIENDS = "Non siete più amici: puoi leggere la conversazione, ma non scrivere."
BLOCKED = "Bloccato: non potete più scrivervi."

recent = RecentRequests()


class RateLimit:
    """Un messaggio ogni `seconds` secondi per utente, in memoria."""

    def __init__(self, clock=time.monotonic):
        self._clock = clock
        self._lock = threading.Lock()
        self._last = {}  # user_id -> ora dell'ultimo messaggio

    def take(self, user_id, seconds):
        with self._lock:
            now = self._clock()
            last = self._last.get(user_id)
            if last is not None and now - last < seconds:
                raise EventError("too_fast", "Un messaggio al secondo: aspetta un momento.",
                                 retry_after=math.ceil(seconds - (now - last)))
            self._last[user_id] = now

    def give_back(self, user_id):
        """Il messaggio non è stato salvato: non conta per il limite."""
        with self._lock:
            self._last.pop(user_id, None)


rate_limit = RateLimit()


def message_data(row):
    return {
        "id": row.id,
        "from_user_id": row.sender_id,
        "to_user_id": row.recipient_id,
        "text": row.text,
        "sent_at": iso_utc(row.sent_at),
    }


def check_text(text):
    maximum = current_app.config["CHAT_MAX_LENGTH"]
    if not isinstance(text, str) or not text.strip():
        raise EventError("invalid_data", "Scrivi un messaggio.")
    if len(text) > maximum:
        raise EventError("invalid_data", f"Al massimo {maximum} caratteri.")
    return text


def check_before_id(value):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise EventError("invalid_data", "before_id deve essere il numero di un messaggio, oppure null.")
    return value


def _other(user_id, other_id):
    check_user_id(other_id)
    if other_id == user_id:
        raise EventError("invalid_data", "Non puoi scrivere a te stesso.")
    if user_repo.get_by_id(other_id) is None:
        raise EventError("not_found", "Questo utente non esiste.")
    return other_id


def cannot_write(user_id, other_id):
    """None se i due possono scriversi, altrimenti "blocked" o "not_friends"."""
    if friend_repo.get_block(user_id, other_id) is not None or friend_repo.get_block(other_id, user_id) is not None:
        return "blocked"
    row = friend_repo.get_pair(user_id, other_id)
    if row is None or row.status != friend_repo.ACCEPTED:
        return "not_friends"
    return None


# --- Lettura ---


def history(user_id, other_id, before_id):
    """chat:history: messaggi, has_more, can_write e cannot_write. Aprire la chat
    (before_id None) segna come letti i messaggi ricevuti."""
    other_id = _other(user_id, other_id)
    before_id = check_before_id(before_id)
    rows, has_more = chat_repo.conversation(user_id, other_id, before_id, HISTORY_LIMIT)
    reason = cannot_write(user_id, other_id)
    if before_id is None:
        chat_repo.mark_read(user_id, other_id, chat_repo.utc_now())
        db.session.commit()
    return {
        "messages": [message_data(r) for r in rows],
        "has_more": has_more,
        "can_write": reason is None,
        "cannot_write": reason,
    }


def read(user_id, other_id):
    """chat:read: con la chat aperta, segna come letti i messaggi appena arrivati."""
    other_id = _other(user_id, other_id)
    chat_repo.mark_read(user_id, other_id, chat_repo.utc_now())
    db.session.commit()


# --- Scrittura ---


def send(user_id, request_id, other_id, text, deliver=None):
    """chat:send: {"message": messaggio salvato}. `deliver(messaggio)` lo recapita (una
    volta sola: lo stesso request_id ripetuto riceve la risposta senza recapitarlo di nuovo)."""
    check_request_id(request_id)

    def attempt():
        message = _send(user_id, other_id, text)
        if deliver is not None:
            deliver(message)
        return {"message": message}

    return recent.run(user_id, "chat:send", request_id, attempt)


def _send(user_id, other_id, text):
    other_id = _other(user_id, other_id)
    text = check_text(text)
    rate_limit.take(user_id, current_app.config["CHAT_MIN_INTERVAL_SECONDS"])
    try:
        return _write(user_id, other_id, text)
    except Exception:
        rate_limit.give_back(user_id)
        raise


def _write(user_id, other_id, text):
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
