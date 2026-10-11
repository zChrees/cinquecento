"""Accesso alla tabella rating (P27): una riga per utente e modalità.

Qui non si fa commit: la transazione è quella del salvataggio della partita
(match_service.save_match), che la chiude.
"""

import sqlalchemy as sa

from app.extensions import db
from app.models.rating import Rating


def get_for_update(user_ids, mode):
    """Le righe di quegli utenti in quella modalità, bloccate in scrittura fino alla fine
    della transazione: {user_id: Rating}. Una lettura bloccante vede sempre i dati già
    confermati, anche con il livello REPEATABLE READ di MySQL (vedi P45)."""
    rows = db.session.scalars(
        sa.select(Rating)
        .where(Rating.user_id.in_(sorted(set(user_ids))), Rating.mode == mode)
        .order_by(Rating.user_id)
        .with_for_update()
    )
    return {row.user_id: row for row in rows}


def get_value(user_id, mode):
    """Il rating di un utente in una modalità, come float, oppure None se non ha ancora la
    riga (P28, per la coda). Sola lettura, senza blocchi: la colonna DOUBLE arriva come
    Decimal e qui si converte."""
    value = db.session.scalar(
        sa.select(Rating.value).where(Rating.user_id == user_id, Rating.mode == mode)
    )
    return None if value is None else float(value)


def add(user_id, mode, value, deviation, volatility, updated_at):
    """La prima riga di un utente in una modalità (alla sua prima partita che conta)."""
    row = Rating(user_id=user_id, mode=mode, value=value, deviation=deviation,
                 volatility=volatility, updated_at=updated_at)
    db.session.add(row)
    return row


def update(row, value, deviation, volatility, updated_at):
    row.value = value
    row.deviation = deviation
    row.volatility = volatility
    row.updated_at = updated_at
