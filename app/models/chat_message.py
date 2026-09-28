"""Tabella messaggi: la chat tra amici, a testo libero (P5, D24).

Il testo si mostra sempre come testo, mai come HTML, e non va mai nei log.
"""

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.mysql import BIGINT, DATETIME, INTEGER
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class ChatMessage(db.Model):
    __tablename__ = "messaggi"

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True)
    sender_id: Mapped[int] = mapped_column(
        "mittente_id", INTEGER(unsigned=True), sa.ForeignKey("utenti.id", ondelete="CASCADE")
    )
    recipient_id: Mapped[int] = mapped_column(
        "destinatario_id", INTEGER(unsigned=True), sa.ForeignKey("utenti.id", ondelete="CASCADE")
    )
    # Al massimo 1000 caratteri (D26, CHAT_MAX_LENGTH in config.py)
    text: Mapped[str] = mapped_column("testo", sa.String(1000))
    sent_at: Mapped[datetime] = mapped_column("inviato_il", DATETIME(fsp=3))
    # Vuota finché il destinatario non lo apre
    read_at: Mapped[datetime | None] = mapped_column("letto_il", sa.DateTime)
