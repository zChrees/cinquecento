"""Tabelle delle partite finite: partite, giocatori_partita, mosse_partita (P5).

Una partita si salva tutta insieme a fine partita (P26), in una sola
transazione: nel database non esiste mai una partita "a metà".

Cosa contiene:
    MODES, END_REASONS, RESULTS   i valori ammessi nelle colonne a elenco
    Match                         una riga di partite
    MatchPlayer                   una riga di giocatori_partita (un giocatore di una partita)
    MatchMove                     una riga di mosse_partita (una mossa di una partita)

Un "modello" è una classe Python che descrive una tabella: ogni attributo è una
colonna. SQLAlchemy lo usa per trasformare le righe in oggetti e viceversa
(match.mode al posto della colonna modalita). I nomi in Python sono in inglese, quelli
delle colonne in italiano (D38): il primo parametro di mapped_column è il nome della
colonna nel database.

DA DOVE ARRIVANO I DATI: le righe le scrive match_repo.py e le legge stats_repo.py;
le tabelle le crea migrations/001_init.sql.
"""

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DATETIME, INTEGER, SMALLINT, TINYINT, VARCHAR

# Mapped[int]: "questa colonna contiene un int" (serve a SQLAlchemy e all'editor);
# mapped_column(...): il nome e il tipo della colonna nel database
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db

# Valori ammessi (CHECK nelle tabelle). Sono testo esatto, non ENUM: vedi migrations/001_init.sql.
MODES = ("1v1", "2v2")
END_REASONS = ("punteggio", "abbandono")
RESULTS = ("vittoria", "sconfitta", "pareggio")


def _code(length):
    """Il tipo delle colonne a elenco: testo confrontato in modo esatto.

    In parole semplici:
        _code(10)
        Un VARCHAR(10) con la collation utf8mb4_0900_bin: "Vittoria" e "vittoria" sono
        diversi (P5: niente ENUM, che senza DEFAULT prende in silenzio il primo valore).
    """
    return VARCHAR(length, charset="utf8mb4", collation="utf8mb4_0900_bin")


# db.Model: la classe di base dei modelli di Flask-SQLAlchemy (app/extensions.py)
class Match(db.Model):
    """Una partita finita (tabella partite)."""

    # __tablename__: il nome della tabella nel database
    __tablename__ = "partite"

    id: Mapped[int] = mapped_column(INTEGER(unsigned=True), primary_key=True)
    mode: Mapped[str] = mapped_column("modalita", _code(3))
    target_score: Mapped[int] = mapped_column("punti_per_vincere", SMALLINT(unsigned=True))
    # No per il 1v1 contro un amico (D36)
    counts_for_rating: Mapped[bool] = mapped_column("conta_per_rating", sa.Boolean)
    started_at: Mapped[datetime] = mapped_column("iniziata_il", sa.DateTime)
    ended_at: Mapped[datetime] = mapped_column("finita_il", sa.DateTime)
    end_reason: Mapped[str] = mapped_column("motivo_fine", _code(10))
    # 0 o 1; vuota = pareggio
    winning_team: Mapped[int | None] = mapped_column("squadra_vincente", TINYINT(unsigned=True))
    team0_score: Mapped[int] = mapped_column("punti_squadra_0", SMALLINT(unsigned=True))
    team1_score: Mapped[int] = mapped_column("punti_squadra_1", SMALLINT(unsigned=True))


class MatchPlayer(db.Model):
    """Un giocatore di una partita finita (tabella giocatori_partita): uno per posto."""

    __tablename__ = "giocatori_partita"

    # ForeignKey: la colonna punta a partite.id; ondelete="CASCADE": se si cancella la
    # partita, si cancellano anche i suoi giocatori
    match_id: Mapped[int] = mapped_column(
        "partita_id",
        INTEGER(unsigned=True),
        sa.ForeignKey("partite.id", ondelete="CASCADE"),
        primary_key=True,
    )
    seat: Mapped[int] = mapped_column("posto", TINYINT(unsigned=True), primary_key=True)
    team: Mapped[int] = mapped_column("squadra", TINYINT(unsigned=True))
    # Vuoto = "utente eliminato" (D6): ondelete="SET NULL", cancellando l'account la
    # colonna si svuota e la partita resta
    user_id: Mapped[int | None] = mapped_column(
        "utente_id", INTEGER(unsigned=True), sa.ForeignKey("utenti.id", ondelete="SET NULL")
    )
    result: Mapped[str] = mapped_column("risultato", _code(10))
    abandoned: Mapped[bool] = mapped_column(
        "ha_abbandonato", sa.Boolean, server_default=sa.false()
    )


class MatchMove(db.Model):
    """Una mossa di una partita finita (tabella mosse_partita), numerata da 1."""

    __tablename__ = "mosse_partita"

    match_id: Mapped[int] = mapped_column(
        "partita_id",
        INTEGER(unsigned=True),
        sa.ForeignKey("partite.id", ondelete="CASCADE"),
        primary_key=True,
    )
    number: Mapped[int] = mapped_column("numero", INTEGER(unsigned=True), primary_key=True)
    hand: Mapped[int] = mapped_column("mano", SMALLINT(unsigned=True))
    # Vuoto per gli eventi del server
    seat: Mapped[int | None] = mapped_column("posto", TINYINT(unsigned=True))
    kind: Mapped[str] = mapped_column("tipo", sa.String(20))
    # JSON: i dettagli della mossa (match_service.py), salvati come testo JSON
    details: Mapped[dict] = mapped_column("dettagli", sa.JSON)
    # DATETIME(fsp=3): data e ora con i millesimi di secondo
    created_at: Mapped[datetime] = mapped_column("creata_il", DATETIME(fsp=3))
