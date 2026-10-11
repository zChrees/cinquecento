"""Tabelle amicizie e blocchi (P5, D23).

"Non si chiede l'amicizia a se stessi" e "non si blocca se stessi" li controlla
il servizio (P45): MySQL non ammette un CHECK su colonne con ON DELETE CASCADE.
"""

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.mysql import INTEGER
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db

STATUSES = ("in_attesa", "accettata")


class Friendship(db.Model):
    """Una riga per coppia, in qualunque direzione: richiesta in attesa o amicizia accettata."""

    __tablename__ = "amicizie"

    requester_id: Mapped[int] = mapped_column(
        "richiedente_id",
        INTEGER(unsigned=True),
        sa.ForeignKey("utenti.id", ondelete="CASCADE"),
        primary_key=True,
    )
    addressee_id: Mapped[int] = mapped_column(
        "destinatario_id",
        INTEGER(unsigned=True),
        sa.ForeignKey("utenti.id", ondelete="CASCADE"),
        primary_key=True,
    )
    status: Mapped[str] = mapped_column(
        "stato", sa.Enum(*STATUSES), server_default="in_attesa"
    )
    requested_at: Mapped[datetime] = mapped_column(
        "richiesta_il", sa.DateTime, server_default=sa.text("CURRENT_TIMESTAMP")
    )
    # Vuota finché la richiesta è in attesa
    answered_at: Mapped[datetime | None] = mapped_column("risposta_il", sa.DateTime)
    # La coppia in ordine: le calcola MySQL e servono solo a "una riga per coppia"
    user_low: Mapped[int | None] = mapped_column(
        "utente_minore",
        INTEGER(unsigned=True),
        sa.Computed("LEAST(richiedente_id, destinatario_id)", persisted=False),
    )
    user_high: Mapped[int | None] = mapped_column(
        "utente_maggiore",
        INTEGER(unsigned=True),
        sa.Computed("GREATEST(richiedente_id, destinatario_id)", persisted=False),
    )


class Block(db.Model):
    __tablename__ = "blocchi"

    blocker_id: Mapped[int] = mapped_column(
        "bloccante_id",
        INTEGER(unsigned=True),
        sa.ForeignKey("utenti.id", ondelete="CASCADE"),
        primary_key=True,
    )
    blocked_id: Mapped[int] = mapped_column(
        "bloccato_id",
        INTEGER(unsigned=True),
        sa.ForeignKey("utenti.id", ondelete="CASCADE"),
        primary_key=True,
    )
    blocked_at: Mapped[datetime] = mapped_column(
        "bloccato_il", sa.DateTime, server_default=sa.text("CURRENT_TIMESTAMP")
    )
