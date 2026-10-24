"""Tabella rating: Glicko-2, una riga per utente e modalità (P5).

I valori iniziali (1500, 350, 0,06) stanno in config.py, non qui.

Cosa contiene:
    MODES    le modalità ammesse
    Rating   una riga della tabella rating

Un "modello" è una classe Python che descrive una tabella (vedi il commento in
app/models/match.py). Attenzione: le colonne DOUBLE arrivano da SQLAlchemy come
Decimal, non come float (P27): chi le usa nei calcoli le converte.

DA DOVE ARRIVANO I DATI: le righe le scrive e le legge rating_repo.py (a fine partita
e per la coda) e le legge stats_repo.py (pannello statistiche).
"""

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DOUBLE, INTEGER, VARCHAR

# Mapped e mapped_column: vedi il commento in app/models/match.py
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db

MODES = ("1v1", "2v2")  # valori ammessi (CHECK nella tabella)


class Rating(db.Model):
    """Il rating di un utente in una modalità (chiave: utente e modalità insieme)."""

    __tablename__ = "rating"

    # ondelete="CASCADE": cancellando l'account si cancellano anche i suoi rating
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
