"""Letture per il pannello statistiche (P30): partite, giocatori_partita, rating.

Solo letture, senza blocchi né commit. I risultati di un giocatore stanno in
giocatori_partita.risultato ("vittoria", "sconfitta", "pareggio"): una partita
abbandonata è già salvata come persa (P26), per chi ha abbandonato e per il suo
compagno (D13).
"""

import sqlalchemy as sa
from sqlalchemy.orm import aliased

from app.extensions import db
from app.models.match import Match, MatchPlayer
from app.models.rating import Rating


def results(user_id):
    """Quante partite l'utente ha finito con ciascun risultato: {"vittoria": n, ...}."""
    rows = db.session.execute(
        sa.select(MatchPlayer.result, sa.func.count())
        .where(MatchPlayer.user_id == user_id)
        .group_by(MatchPlayer.result)
    )
    return {result: count for result, count in rows}


def rated_games(user_id):
    """Partite che contano per il rating dell'utente, per modalità: {"1v1": n, ...}.

    Sono le partite con conta_per_rating, tranne quelle in cui il suo compagno ha
    abbandonato e lui no: lì il suo rating non cambia (D13), quindi non contano
    nemmeno per "provvisorio" (scelta di P30).
    """
    partner = aliased(MatchPlayer)
    partner_abandoned = (
        sa.select(partner.seat)
        .where(
            partner.match_id == MatchPlayer.match_id,
            partner.team == MatchPlayer.team,
            partner.seat != MatchPlayer.seat,
            partner.abandoned.is_(True),
        )
        .exists()
    )
    rows = db.session.execute(
        sa.select(Match.mode, sa.func.count())
        .join(MatchPlayer, MatchPlayer.match_id == Match.id)
        .where(
            MatchPlayer.user_id == user_id,
            Match.counts_for_rating.is_(True),
            sa.or_(MatchPlayer.abandoned.is_(True), ~partner_abandoned),
        )
        .group_by(Match.mode)
    )
    return {mode: count for mode, count in rows}


def rating_values(user_id):
    """Il rating dell'utente per modalità, come float: {"1v1": 1523.4, ...}; manca chi non ha la riga.
    La colonna DOUBLE arriva come Decimal (P27): qui si converte."""
    rows = db.session.execute(sa.select(Rating.mode, Rating.value).where(Rating.user_id == user_id))
    return {mode: float(value) for mode, value in rows}
