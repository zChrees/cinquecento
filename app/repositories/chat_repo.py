"""Accesso alla tabella messaggi: la chat tra amici (P48, D24).

Qui non si fa commit: la transazione la chiude il servizio (chat_service).
Il testo dei messaggi non va mai nei log. Date e ore si scrivono da Python in UTC,
con i millesimi (colonna DATETIME(3)).

Cosa contiene:
    utc_now()                                 l'ora di adesso in UTC, ai millesimi
    add(7, 8, "ciao", ora)                    prepara un messaggio e gli dà il numero
    conversation(7, 8, before_id, limit)      una pagina della conversazione tra 7 e 8
    mark_read(7, 8, ora)                      i messaggi di 8 a 7 diventano letti

DA DOVE ARRIVANO I DATI: le chiama chat_service.py, con i numeri dell'utente collegato
e dell'amico (dagli eventi chat:history, chat:send e chat:read).
"""

from datetime import UTC, datetime

import sqlalchemy as sa

from app.extensions import db
from app.models.chat_message import ChatMessage


def utc_now():
    """Già ai millesimi, come `inviato_il` (DATETIME(3)): MySQL arrotonderebbe il resto,
    e la risposta di chat:send avrebbe un'ora diversa da chat:history (P31).

    In parole semplici:
        utc_now()
        Per esempio datetime(2026, 9, 28, 14, 3, 12, 345000): i microsecondi 345678
        diventano 345000 ("// 1000 * 1000" toglie le ultime tre cifre).
    """
    now = datetime.now(UTC).replace(tzinfo=None)
    return now.replace(microsecond=now.microsecond // 1000 * 1000)


def add(sender_id, recipient_id, text, sent_at):
    """Prepara il messaggio e lo restituisce, già con il suo numero.

    In parole semplici:
        add(7, 8, "ciao", utc_now())
        flush manda la riga a MySQL senza chiudere la transazione: così MySQL le dà
        l'id (AUTO_INCREMENT), che serve alla risposta prima del commit.
    """
    row = ChatMessage(sender_id=sender_id, recipient_id=recipient_id, text=text, sent_at=sent_at)
    db.session.add(row)
    db.session.flush()  # per avere l'id
    return row


def conversation(user_id, other_id, before_id, limit):
    """Al massimo `limit` messaggi tra i due, prima di `before_id` (None = gli ultimi),
    dal più vecchio al più nuovo; più `has_more` (ce ne sono di più vecchi).

    In parole semplici:
        conversation(7, 8, None, 50)
        Restituisce una coppia (messaggi, has_more), per esempio ([m30, m31], False).
        Si leggono limit + 1 messaggi, dal più nuovo: se ne arriva uno in più vuol dire
        che ce ne sono di più vecchi (has_more), e quello in più non si restituisce.
    """
    between = sa.or_(
        sa.and_(ChatMessage.sender_id == user_id, ChatMessage.recipient_id == other_id),
        sa.and_(ChatMessage.sender_id == other_id, ChatMessage.recipient_id == user_id),
    )
    query = sa.select(ChatMessage).where(between)
    if before_id is not None:
        query = query.where(ChatMessage.id < before_id)
    rows = db.session.scalars(query.order_by(ChatMessage.id.desc()).limit(limit + 1)).all()

    # newest_first: i primi limit messaggi, dal più nuovo; poi si girano (reversed)
    newest_first = rows[:limit]
    oldest_first = list(reversed(newest_first))
    has_more = len(rows) > limit
    return (oldest_first, has_more)


def mark_read(recipient_id, sender_id, read_at):
    """Segna come letti i messaggi ricevuti da `recipient_id` da parte di `sender_id`.

    In parole semplici:
        mark_read(7, 8, utc_now())
        UPDATE messaggi SET letto_il = ora WHERE destinatario_id = 7 AND
        mittente_id = 8 AND letto_il IS NULL: solo quelli non ancora letti.
    """
    db.session.execute(
        sa.update(ChatMessage)
        .where(ChatMessage.recipient_id == recipient_id, ChatMessage.sender_id == sender_id,
               ChatMessage.read_at.is_(None))
        .values(read_at=read_at)
    )
