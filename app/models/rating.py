"""Tabella rating: Glicko-2, una riga per utente e modalità (P5).

I valori iniziali (1500, 350, 0,06) stanno in config.py, non qui.
"""

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DOUBLE, INTEGER, VARCHAR
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db

MODES = ("1v1", "2v2")  # valori ammessi (CHECK nella tabella)


class Rating(db.Model):
    __tablename__ = "rating"

    user_id: Mapped[int] = mapped_column(
        "utente_id",
        INTEGER(unsigned=True),
        sa.ForeignKey("utenti.id", ondelete="CASCADE"),
        primary_key=True,
    )
    mode: Mapped[str] = mapped_column(
        "modalita", VARCHAR(3, charset="utf8mb4", collation="utf8mb4_0900_bin"), primary_key=True
    )
    value: Mapped[float] = mapped_column("valore", DOUBLE)
    deviation: Mapped[float] = mapped_column("deviazione", DOUBLE)
    volatility: Mapped[float] = mapped_column("volatilita", DOUBLE)
    updated_at: Mapped[datetime] = mapped_column("aggiornato_il", sa.DateTime)
