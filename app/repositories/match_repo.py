"""Accesso alle tabelle partite, giocatori_partita e mosse_partita (P26).

Qui non si fa commit: la transazione la chiude il servizio (match_service), che
scrive la partita tutta insieme a fine partita.
"""

from app.extensions import db
from app.models.match import Match, MatchMove, MatchPlayer


def add_match(**columns):
    """Prepara la riga di partite e la manda a MySQL (flush) per avere il suo numero."""
    match = Match(**columns)
    db.session.add(match)
    db.session.flush()
    return match


def add_players(match_id, players):
    """players: dizionari con seat, team, user_id, result, abandoned."""
    db.session.add_all(MatchPlayer(match_id=match_id, **player) for player in players)
    db.session.flush()


def add_moves(match_id, moves):
    """moves: dizionari con number, hand, seat, kind, details, created_at, nell'ordine della partita."""
    db.session.add_all(MatchMove(match_id=match_id, **move) for move in moves)
    db.session.flush()
