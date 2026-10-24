"""Accesso alla tabella rating (P27): una riga per utente e modalità.

Qui non si fa commit: la transazione è quella del salvataggio della partita
(match_service.save_match), che la chiude.

Cosa contiene:
    get_for_update(user_ids, mode)   le righe di quegli utenti, bloccate fino al commit
    get_value(user_id, mode)         il rating di un utente come numero, o None
    add(...)                         la prima riga di un utente in una modalità
    update(row, ...)                 cambia i valori di una riga

Le query si scrivono con SQLAlchemy: sa.select(Rating).where(...) costruisce una
SELECT (come la si scriverebbe in SQL) e db.session la manda a MySQL.

DA DOVE ARRIVANO I DATI: rating_service.apply_match (a fine partita) e la coda
(matchmaking.py, get_value) chiamano queste funzioni.
"""

import sqlalchemy as sa

from app.extensions import db
from app.models.rating import Rating


def get_for_update(user_ids, mode):
    """Le righe di quegli utenti in quella modalità, bloccate in scrittura fino alla fine
    della transazione: {user_id: Rating}. Una lettura bloccante vede sempre i dati già
    confermati, anche con il livello REPEATABLE READ di MySQL (vedi P45).

    In parole semplici:
        get_for_update([7, 12], "1v1")
        È una SELECT ... FOR UPDATE (with_for_update): finché la transazione non
        finisce, nessun altro può cambiare quelle righe. Gli utenti si ordinano
        (sorted) così due salvataggi insieme bloccano le righe nello stesso ordine e
        non si aspettano a vicenda all'infinito. Chi non ha la riga non c'è nel risultato.
        Restituisce per esempio {7: <Rating 7 1v1>}.
    """
    rows = db.session.scalars(
        sa.select(Rating)
        .where(Rating.user_id.in_(sorted(set(user_ids))), Rating.mode == mode)
        .order_by(Rating.user_id)
        .with_for_update()
    )
    found = {}
    for row in rows:
        found[row.user_id] = row
    return found


def get_value(user_id, mode):
    """Il rating di un utente in una modalità, come float, oppure None se non ha ancora la
    riga (P28, per la coda). Sola lettura, senza blocchi: la colonna DOUBLE arriva come
    Decimal e qui si converte.

    In parole semplici:
        get_value(7, "1v1")
        Per esempio 1523.4, oppure None.
    """
    value = db.session.scalar(
        sa.select(Rating.value).where(Rating.user_id == user_id, Rating.mode == mode)
    )
    if value is None:
        return None
    return float(value)


def add(user_id, mode, value, deviation, volatility, updated_at):
    """La prima riga di un utente in una modalità (alla sua prima partita che conta).

    In parole semplici:
        add(user_id, mode, value, deviation, volatility, updated_at)
        Aggiunge la riga alla transazione (db.session.add); MySQL la scrive al commit.
    """
    row = Rating(user_id=user_id, mode=mode, value=value, deviation=deviation,
                 volatility=volatility, updated_at=updated_at)
    db.session.add(row)
    return row


def update(row, value, deviation, volatility, updated_at):
    """Cambia i valori di una riga già letta (con get_for_update).

    In parole semplici:
        update(row, value, deviation, volatility, updated_at)
        Basta cambiare i campi: SQLAlchemy se ne accorge e al commit manda l'UPDATE.
    """
    row.value = value
    row.deviation = deviation
    row.volatility = volatility
    row.updated_at = updated_at
