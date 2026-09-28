"""Salvataggio delle partite finite (P26).

A fine partita la stanza (app/realtime/room.py) prepara un MatchRecord con tutto
quello che serve e chiama save_match: la riga in partite, i giocatori e le mosse
si scrivono in UNA sola transazione. Se qualcosa va storto a metà non resta niente
(rollback): nel database non esistono partite "a metà" (DECISIONI.md, P26).
Prima della fine nel database non si scrive niente: la partita in corso sta solo
in memoria.

Mosse salvate (mosse_partita.tipo, nomi in italiano come le altre colonne, D38):
- gioca_carta       {"seme", "valore"}   la carta giocata dal giocatore
- canta             {"seme", "punti"}    40 o 20
- mossa_automatica  {"seme", "valore"}   la carta giocata dal server a tempo scaduto (D12)
- abbandono         {"motivo"}           "esci" (game:leave) o "tempo_scaduto" (non rientrato)
Date e ore in UTC. Nei log solo numeri, mai nomi degli utenti.
"""

import logging
from dataclasses import dataclass

from app.extensions import db
from app.models.match import END_REASONS, MODES
from app.repositories import match_repo

log = logging.getLogger(__name__)

MOVE_KINDS = ("gioca_carta", "canta", "mossa_automatica", "abbandono")
TEAMS = (0, 1)


@dataclass(frozen=True)
class PlayerRecord:
    seat: int
    user_id: int
    abandoned: bool = False

    @property
    def team(self):
        return self.seat % 2  # la squadra di un posto è posto % 2 (contratto 3.1)


@dataclass(frozen=True)
class MoveRecord:
    hand: int
    seat: int | None
    kind: str
    details: dict
    at: object  # datetime in UTC, senza fuso


@dataclass(frozen=True)
class MatchRecord:
    mode: str
    target_score: int
    rated: bool
    started_at: object
    ended_at: object
    reason: str  # "punteggio" o "abbandono"
    winner_team: int | None  # None = pareggio
    scores: tuple  # punti finali per squadra: (squadra 0, squadra 1)
    players: tuple  # PlayerRecord, uno per posto
    moves: tuple  # MoveRecord, nell'ordine della partita


def result_of(team, winner_team):
    if winner_team is None:
        return "pareggio"
    return "vittoria" if team == winner_team else "sconfitta"


def check(record):
    """Controlla il MatchRecord prima di scrivere: un dato sbagliato non si salva a metà."""
    if record.mode not in MODES:
        raise ValueError(f"Modalità non valida: {record.mode!r}")
    if record.reason not in END_REASONS:
        raise ValueError(f"Motivo di fine non valido: {record.reason!r}")
    if record.winner_team not in (*TEAMS, None):
        raise ValueError(f"Squadra vincente non valida: {record.winner_team!r}")
    if len(record.scores) != len(TEAMS):
        raise ValueError("Servono i punti delle due squadre.")
    if [p.seat for p in record.players] != list(range(int(record.mode[0]) * 2)):
        raise ValueError("I giocatori devono essere uno per posto, in ordine.")
    for move in record.moves:
        if move.kind not in MOVE_KINDS:
            raise ValueError(f"Tipo di mossa non valido: {move.kind!r}")


def save_match(record):
    """Salva la partita finita in una sola transazione e restituisce il suo numero (partite.id)."""
    check(record)
    try:
        match = match_repo.add_match(
            mode=record.mode,
            target_score=record.target_score,
            counts_for_rating=record.rated,
            started_at=record.started_at,
            ended_at=record.ended_at,
            end_reason=record.reason,
            winning_team=record.winner_team,
            team0_score=record.scores[0],
            team1_score=record.scores[1],
        )
        match_id = match.id
        match_repo.add_players(match_id, [
            {
                "seat": p.seat,
                "team": p.team,
                "user_id": p.user_id,
                "result": result_of(p.team, record.winner_team),
                "abandoned": p.abandoned,
            }
            for p in record.players
        ])
        match_repo.add_moves(match_id, [
            {
                "number": number,
                "hand": move.hand,
                "seat": move.seat,
                "kind": move.kind,
                "details": move.details,
                "created_at": move.at,
            }
            for number, move in enumerate(record.moves, start=1)
        ])
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    log.info("Partita salvata (numero %s, %s mosse)", match_id, len(record.moves))
    return match_id
