"""Tabelle delle partite finite: partite, giocatori_partita, mosse_partita (P5).

Una partita si salva tutta insieme a fine partita (P26), in una sola
transazione: nel database non esiste mai una partita "a metà".
"""

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DATETIME, INTEGER, SMALLINT, TINYINT, VARCHAR
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db

# Valori ammessi (CHECK nelle tabelle). Sono testo esatto, non ENUM: vedi migrations/001_init.sql.
MODES = ("1v1", "2v2")
END_REASONS = ("punteggio", "abbandono")
RESULTS = ("vittoria", "sconfitta", "pareggio")


def _code(length):
    return VARCHAR(length, charset="utf8mb4", collation="utf8mb4_0900_bin")


class Match(db.Model):
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
    __tablename__ = "giocatori_partita"

    match_id: Mapped[int] = mapped_column(
        "partita_id",
        INTEGER(unsigned=True),
        sa.ForeignKey("partite.id", ondelete="CASCADE"),
        primary_key=True,
    )
    seat: Mapped[int] = mapped_column("posto", TINYINT(unsigned=True), primary_key=True)
    team: Mapped[int] = mapped_column("squadra", TINYINT(unsigned=True))
    # Vuoto = "utente eliminato" (D6)
    user_id: Mapped[int | None] = mapped_column(
        "utente_id", INTEGER(unsigned=True), sa.ForeignKey("utenti.id", ondelete="SET NULL")
    )
    result: Mapped[str] = mapped_column("risultato", _code(10))
    abandoned: Mapped[bool] = mapped_column(
        "ha_abbandonato", sa.Boolean, server_default=sa.false()
    )


class MatchMove(db.Model):
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
    details: Mapped[dict] = mapped_column("dettagli", sa.JSON)
    created_at: Mapped[datetime] = mapped_column("creata_il", DATETIME(fsp=3))
