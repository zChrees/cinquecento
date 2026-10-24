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

Cosa contiene:
    score_of(team, winner_team)   il risultato per Glicko-2, per esempio 1.0 per chi ha vinto
    apply_match(record)           aggiorna il rating dei giocatori di una partita finita

Una "transazione" è un gruppo di scritture sul database che vale tutto insieme: o
vanno a buon fine tutte (commit) o non ne resta nessuna (rollback).

DA DOVE ARRIVANO I DATI: match_service.save_match passa il MatchRecord preparato dalla
stanza (app/realtime/room.py); i rating di prima si leggono con rating_repo.
"""

import logging

from flask import current_app

from app.repositories import rating_repo
from app.services import glicko2

log = logging.getLogger(__name__)


def score_of(team, winner_team):
    """Il risultato di una squadra per Glicko-2.

    In parole semplici:
        score_of(team, winner_team)
        team: la squadra (0 o 1). winner_team: la squadra che ha vinto, o None per un
        pareggio. Restituisce 1.0 (vittoria), 0.5 (pareggio) o 0.0 (sconfitta).
    """
    if winner_team is None:
        return 0.5
    if team == winner_team:
        return 1.0
    return 0.0


def _stored(row):
    """Una riga della tabella rating come Rating di glicko2.

    In parole semplici:
        _stored(row)
        Le colonne DOUBLE arrivano da SQLAlchemy come Decimal (DOUBLE di MySQL,
        asdecimal): il calcolo di Glicko-2 lavora con i float, quindi si convertono.
    """
    return glicko2.Rating(float(row.value), float(row.deviation), float(row.volatility))


def apply_match(record):
    """Aggiorna il rating dei giocatori di una partita finita; restituisce {user_id: nuovo Rating}.

    In parole semplici:
        apply_match(record)
        record: il MatchRecord della partita (match_service.py). Arriva da save_match.
        1. una partita che non conta non cambia niente ({});
        2. si leggono (e si bloccano fino al commit) le righe dei giocatori;
        3. per ognuno si calcola il rating nuovo dai rating di PRIMA della partita;
        4. si scrivono: la riga esistente si aggiorna, quella che manca si crea.
        Qui non si fa commit: lo fa save_match.
    """
    if not record.rated:
        return {}
    config = current_app.config
    initial = glicko2.Rating(config["RATING_INITIAL"], config["RATING_RD_INITIAL"],
                             config["RATING_VOLATILITY_INITIAL"])

    user_ids = []
    for player in record.players:
        user_ids.append(player.user_id)
    rows = rating_repo.get_for_update(user_ids, record.mode)

    # before: il rating di ognuno prima della partita (initial per chi non ha ancora la riga)
    before = {}
    for player in record.players:
        if player.user_id in rows:
            before[player.user_id] = _stored(rows[player.user_id])
        else:
            before[player.user_id] = initial

    # abandoned_teams: le squadre in cui qualcuno ha abbandonato
    abandoned_teams = set()
    for player in record.players:
        if player.abandoned:
            abandoned_teams.add(player.team)

    after = {}
    for player in record.players:
        if player.team in abandoned_teams and not player.abandoned:
            continue  # compagno di chi ha abbandonato: il rating non cambia (D13)
        # opponents: i rating di prima dei giocatori dell'altra squadra
        opponents = []
        for other in record.players:
            if other.team != player.team:
                opponents.append(before[other.user_id])
        # nel 1v1 l'avversario è uno; nel 2v2 la squadra diventa un solo avversario
        if len(opponents) == 1:
            opponent = opponents[0]
        else:
            opponent = glicko2.team_opponent(opponents)
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
