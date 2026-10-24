"""Accesso alle tabelle partite, giocatori_partita e mosse_partita (P26).

Qui non si fa commit: la transazione la chiude il servizio (match_service), che
scrive la partita tutta insieme a fine partita.

Cosa contiene:
    add_match(**columns)            la riga della partita, con il suo numero
    add_players(match_id, players)  i giocatori della partita
    add_moves(match_id, moves)      le mosse della partita

"flush" manda a MySQL le scritture preparate, senza confermarle (il commit lo fa il
servizio): serve per avere subito il numero della partita (partite.id), che MySQL
assegna da solo, e per scoprire subito un errore.

DA DOVE ARRIVANO I DATI: match_service.save_match, con i dati del MatchRecord.
"""

from app.extensions import db
from app.models.match import Match, MatchMove, MatchPlayer


def add_match(**columns):
    """Prepara la riga di partite e la manda a MySQL (flush) per avere il suo numero.

    In parole semplici:
        add_match(mode="1v1", target_score=300, ...)
        **columns raccoglie in un dizionario tutti i parametri passati con il nome
        (i campi del modello Match) e Match(**columns) li ripassa uguali al costruttore.
        Restituisce la riga, con match.id già assegnato.
    """
    match = Match(**columns)
    db.session.add(match)
    db.session.flush()
    return match


def add_players(match_id, players):
    """players: dizionari con seat, team, user_id, result, abandoned.

    In parole semplici:
        add_players(42, [{"seat": 0, "team": 0, "user_id": 7, "result": "vittoria",
                          "abandoned": False}, ...])
        Una riga di giocatori_partita per ogni dizionario.
    """
    for player in players:
        db.session.add(MatchPlayer(
            match_id=match_id,
            seat=player["seat"],
            team=player["team"],
            user_id=player["user_id"],
            result=player["result"],
            abandoned=player["abandoned"],
        ))
    db.session.flush()


def add_moves(match_id, moves):
    """moves: dizionari con number, hand, seat, kind, details, created_at, nell'ordine della partita.

    In parole semplici:
        add_moves(42, [{"number": 1, "hand": 1, "seat": 0, "kind": "gioca_carta",
                        "details": {"seme": "coppe", "valore": 1}, "created_at": ora}, ...])
        Una riga di mosse_partita per ogni dizionario.
    """
    for move in moves:
        db.session.add(MatchMove(
            match_id=match_id,
            number=move["number"],
            hand=move["hand"],
            seat=move["seat"],
            kind=move["kind"],
            details=move["details"],
            created_at=move["created_at"],
        ))
    db.session.flush()
