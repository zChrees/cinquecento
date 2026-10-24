"""Tabella messaggi: la chat tra amici, a testo libero (P5, D24).

Il testo si mostra sempre come testo, mai come HTML, e non va mai nei log.

Cosa contiene:
    ChatMessage   una riga della tabella messaggi (un messaggio)

Un "modello" è una classe Python che descrive una tabella (vedi il commento in
app/models/match.py): ogni attributo è una colonna, e il primo parametro di
mapped_column, quando c'è, è il nome della colonna nel database.

DA DOVE ARRIVANO I DATI: le righe le scrive e le legge chat_repo.py (la chat);
friend_repo.unread_by_sender conta quelle non lette (il pannello amici).
"""

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.mysql import BIGINT, DATETIME, INTEGER

# Mapped e mapped_column: vedi il commento in app/models/match.py
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


# db.Model: la classe di base dei modelli di Flask-SQLAlchemy (app/extensions.py)
class ChatMessage(db.Model):
    """Un messaggio della chat (tabella messaggi)."""

    # __tablename__: il nome della tabella nel database
    __tablename__ = "messaggi"

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True)
    # ForeignKey: la colonna punta a utenti.id; ondelete="CASCADE": cancellando
    # l'account si cancellano anche i suoi messaggi
    sender_id: Mapped[int] = mapped_column(
        "mittente_id", INTEGER(unsigned=True), sa.ForeignKey("utenti.id", ondelete="CASCADE")
    )
    recipient_id: Mapped[int] = mapped_column(
        "destinatario_id", INTEGER(unsigned=True), sa.ForeignKey("utenti.id", ondelete="CASCADE")
    )
    # Al massimo 1000 caratteri (D26, CHAT_MAX_LENGTH in config.py)
    text: Mapped[str] = mapped_column("testo", sa.String(1000))
    # DATETIME(fsp=3): con i millesimi di secondo (chat_repo.utc_now)
    sent_at: Mapped[datetime] = mapped_column("inviato_il", DATETIME(fsp=3))
    # Vuota finché il destinatario non lo apre (datetime | None: un'ora oppure None)
    read_at: Mapped[datetime | None] = mapped_column("letto_il", sa.DateTime)
