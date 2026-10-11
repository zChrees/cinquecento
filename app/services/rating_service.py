"""Aggiornamento del rating a fine partita (P27; decisioni D9, D13, D35, D36).

Lo chiama match_service.save_match prima del commit: rating e partita si salvano
nella stessa transazione (o tutti e due o niente).
- Solo le partite che contano (record.rated): il 1v1 contro un amico no, il 2v2
  con un amico come compagno sì (D36).
- Rating separati per 1v1 e 2v2; uguali per 150, 300 e 500 punti (D35).
- Vittoria 1, pareggio 0.5, sconfitta 0.
- La riga si crea alla prima partita che conta, con i valori iniziali di config.py (D9).
- 2v2: ogni giocatore affronta la squadra avversaria come un solo avversario
  (glicko2.team_opponent, scelta (a) di P27). Si calcola tutto dai rating di prima
  della partita, poi si scrive.
- Abbandono nel 2v2 (D13): perde tutta la squadra, ma il rating scende solo a chi
  ha abbandonato; il compagno resta com'era. Gli avversari guadagnano normalmente.
"""

import logging

from flask import current_app

from app.repositories import rating_repo
from app.services import glicko2

log = logging.getLogger(__name__)


def score_of(team, winner_team):
    if winner_team is None:
        return 0.5
    return 1.0 if team == winner_team else 0.0


def _stored(row):
    # Le colonne DOUBLE arrivano da SQLAlchemy come Decimal (DOUBLE di MySQL, asdecimal):
    # il calcolo di Glicko-2 lavora con i float.
    return glicko2.Rating(float(row.value), float(row.deviation), float(row.volatility))


def apply_match(record):
    """Aggiorna il rating dei giocatori di una partita finita; restituisce {user_id: nuovo Rating}."""
    if not record.rated:
        return {}
    config = current_app.config
    initial = glicko2.Rating(config["RATING_INITIAL"], config["RATING_RD_INITIAL"],
                             config["RATING_VOLATILITY_INITIAL"])
    rows = rating_repo.get_for_update([p.user_id for p in record.players], record.mode)
    before = {p.user_id: _stored(rows[p.user_id]) if p.user_id in rows else initial for p in record.players}
    abandoned_teams = {p.team for p in record.players if p.abandoned}

    after = {}
    for player in record.players:
        if player.team in abandoned_teams and not player.abandoned:
            continue  # compagno di chi ha abbandonato: il rating non cambia (D13)
        opponents = [before[p.user_id] for p in record.players if p.team != player.team]
        opponent = opponents[0] if len(opponents) == 1 else glicko2.team_opponent(opponents)
        result = glicko2.Result(opponent, score_of(player.team, record.winner_team))
        after[player.user_id] = glicko2.update(before[player.user_id], [result], config["GLICKO_TAU"])

    for user_id, rating in after.items():
        if user_id in rows:
            rating_repo.update(rows[user_id], rating.value, rating.deviation, rating.volatility, record.ended_at)
        else:
            rating_repo.add(user_id, record.mode, rating.value, rating.deviation, rating.volatility,
                            record.ended_at)
    log.info("Rating %s aggiornato per %s giocatori", record.mode, len(after))
    return after
