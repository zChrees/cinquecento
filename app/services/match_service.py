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
- cala_carte        {"mani", "canti"}    P84: le carte che restavano a ogni posto ({"posto", "carte"})
                                         e i 20 aggiunti per il compagno ({"posto", "seme", "punti"})
Date e ore in UTC. Nei log solo numeri, mai nomi degli utenti.
P27: nella stessa transazione si aggiorna il rating (rating_service.apply_match).

Cosa contiene:
    PlayerRecord, MoveRecord, MatchRecord   i dati della partita da salvare
    result_of(team, winner_team)            il risultato di una squadra, per esempio "vittoria"
    check(record)                           controlla il MatchRecord prima di scrivere
    save_match(record)                      salva la partita, per esempio save_match(record) = 42
    TEMPORARY_ERRORS                        gli errori per cui riprovare (MySQL non risponde, O3)

DA DOVE ARRIVANO I DATI: _try_save di room.py chiama save_match con il MatchRecord
costruito da _match_record, dentro l'applicazione Flask, e con TEMPORARY_ERRORS
decide se riprovare.
"""

import logging
from dataclasses import dataclass

from sqlalchemy.exc import InterfaceError, OperationalError

from app.extensions import db
from app.models.match import END_REASONS, MODES
from app.repositories import match_repo
from app.services import rating_service

log = logging.getLogger(__name__)

MOVE_KINDS = ("gioca_carta", "canta", "mossa_automatica", "abbandono", "cala_carte")
TEAMS = (0, 1)

# O3 (R6): gli errori di save_match per cui riprovare più tardi può servire. SQLAlchemy li
# lancia quando la connessione con MySQL manca o cade (MySQL spento o in riavvio, rete) o
# quando MySQL ferma la transazione per un blocco (deadlock). Gli altri (un dato non valido,
# un utente che non c'è) darebbero lo stesso errore anche la volta dopo.
# È una tupla di classi: `except TEMPORARY_ERRORS:` prende un errore di una qualsiasi delle due
TEMPORARY_ERRORS = (OperationalError, InterfaceError)


# @dataclass(frozen=True): costruttore automatico e campi che non si cambiano più
# (vedi il commento in app/game/engine/cards.py)
@dataclass(frozen=True)
class PlayerRecord:
    """Un giocatore della partita da salvare.

    In parole semplici:
        PlayerRecord(seat=0, user_id=7, abandoned=False)
        abandoned: facoltativo (se manca False), True per chi ha abbandonato.
    """

    seat: int
    user_id: int
    abandoned: bool = False

    # @property: si legge come un campo (record.team, senza parentesi)
    @property
    def team(self):
        """La squadra del giocatore: 0 o 1."""
        return self.seat % 2  # la squadra di un posto è posto % 2 (contratto 3.1)


@dataclass(frozen=True)
class MoveRecord:
    """Una mossa della partita da salvare.

    In parole semplici:
        MoveRecord(hand=1, seat=0, kind="gioca_carta", details={"seme": "coppe", "valore": 1}, at=ora)
        seat: None per gli eventi del server senza un giocatore.
    """

    hand: int
    seat: int | None
    kind: str
    details: dict
    at: object  # datetime in UTC, senza fuso


@dataclass(frozen=True)
class MatchRecord:
    """La partita finita, con tutto quello che si salva."""

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
    """Il risultato di una squadra come si salva in giocatori_partita.risultato.

    In parole semplici:
        result_of(team, winner_team)
        Restituisce "vittoria", "sconfitta" o, con winner_team None, "pareggio".
    """
    if winner_team is None:
        return "pareggio"
    if team == winner_team:
        return "vittoria"
    return "sconfitta"


def check(record):
    """Controlla il MatchRecord prima di scrivere: un dato sbagliato non si salva a metà.

    In parole semplici:
        check(record)
        Modalità, motivo, squadra vincente, punteggi, posti in ordine (0, 1 nel 1v1;
        0, 1, 2, 3 nel 2v2) e tipi di mossa. Un dato sbagliato lancia ValueError.
        "!r" dentro la f-string scrive il valore con le virgolette, per esempio '3v3'.
    """
    if record.mode not in MODES:
        raise ValueError(f"Modalità non valida: {record.mode!r}")
    if record.reason not in END_REASONS:
        raise ValueError(f"Motivo di fine non valido: {record.reason!r}")
    # una squadra vincente valida: 0, 1 oppure None (pareggio)
    if record.winner_team not in TEAMS + (None,):
        raise ValueError(f"Squadra vincente non valida: {record.winner_team!r}")
    if len(record.scores) != len(TEAMS):
        raise ValueError("Servono i punti delle due squadre.")
    # seats: i posti dei giocatori in ordine; devono essere 0, 1, ... fino al numero di
    # giocatori (int(record.mode[0]) è il primo carattere della modalità: 1 o 2)
    seats = []
    for player in record.players:
        seats.append(player.seat)
    if seats != list(range(int(record.mode[0]) * 2)):
        raise ValueError("I giocatori devono essere uno per posto, in ordine.")
    for move in record.moves:
        if move.kind not in MOVE_KINDS:
            raise ValueError(f"Tipo di mossa non valido: {move.kind!r}")


def save_match(record):
    """Salva la partita finita in una sola transazione e restituisce il suo numero (partite.id).

    In parole semplici:
        save_match(record)
        1. check(record);
        2. la riga in partite, i giocatori, le mosse (numerate da 1) e il rating;
        3. commit: tutto insieme. Se qualcosa va storto, rollback (non resta niente) e
           l'errore va avanti a chi l'ha chiamata (raise), che lo scrive nel log.
        Restituisce il numero della partita, per esempio 42.
    """
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

        players = []
        for player in record.players:
            players.append({
                "seat": player.seat,
                "team": player.team,
                "user_id": player.user_id,
                "result": result_of(player.team, record.winner_team),
                "abandoned": player.abandoned,
            })
        match_repo.add_players(match_id, players)

        # le mosse numerate da 1, nell'ordine della partita
        moves = []
        for index in range(len(record.moves)):
            move = record.moves[index]
            moves.append({
                "number": index + 1,
                "hand": move.hand,
                "seat": move.seat,
                "kind": move.kind,
                "details": move.details,
                "created_at": move.at,
            })
        match_repo.add_moves(match_id, moves)

        rating_service.apply_match(record)  # P27: nella stessa transazione della partita
        db.session.commit()
    except Exception:
        db.session.rollback()
        # raise da solo: rilancia lo stesso errore, dopo aver annullato le scritture
        raise
    log.info("Partita salvata (numero %s, %s mosse)", match_id, len(record.moves))
    return match_id