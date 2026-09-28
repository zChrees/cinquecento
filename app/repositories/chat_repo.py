"""Accesso alla tabella messaggi: la chat tra amici (P48, D24).

Qui non si fa commit: la transazione la chiude il servizio (chat_service).
Il testo dei messaggi non va mai nei log. Date e ore si scrivono da Python in UTC,
con i millesimi (colonna DATETIME(3)).
"""

from datetime import UTC, datetime

import sqlalchemy as sa

from app.extensions import db
from app.models.chat_message import ChatMessage


def utc_now():
    """Già ai millesimi, come `inviato_il` (DATETIME(3)): MySQL arrotonderebbe il resto,
    e la risposta di chat:send avrebbe un'ora diversa da chat:history (P31)."""
    now = datetime.now(UTC).replace(tzinfo=None)
    return now.replace(microsecond=now.microsecond // 1000 * 1000)


def add(sender_id, recipient_id, text, sent_at):
    row = ChatMessage(sender_id=sender_id, recipient_id=recipient_id, text=text, sent_at=sent_at)
    db.session.add(row)
    db.session.flush()  # per avere l'id
    return row


def conversation(user_id, other_id, before_id, limit):
    """Al massimo `limit` messaggi tra i due, prima di `before_id` (None = gli ultimi),
    dal più vecchio al più nuovo; più `has_more` (ce ne sono di più vecchi)."""
    between = sa.or_(
        sa.and_(ChatMessage.sender_id == user_id, ChatMessage.recipient_id == other_id),
        sa.and_(ChatMessage.sender_id == other_id, ChatMessage.recipient_id == user_id),
    )
    query = sa.select(ChatMessage).where(between)
    if before_id is not None:
        query = query.where(ChatMessage.id < before_id)
    rows = db.session.scalars(query.order_by(ChatMessage.id.desc()).limit(limit + 1)).all()
    return list(reversed(rows[:limit])), len(rows) > limit


def mark_read(recipient_id, sender_id, read_at):
    """Segna come letti i messaggi ricevuti da `recipient_id` da parte di `sender_id`."""
    db.session.execute(
        sa.update(ChatMessage)
        .where(ChatMessage.recipient_id == recipient_id, ChatMessage.sender_id == sender_id,
               ChatMessage.read_at.is_(None))
        .values(read_at=read_at)
    )
