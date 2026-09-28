"""Tabella utenti: gli account (P5).

Gli attributi sono in inglese, le colonne in italiano (D38): base.html legge
current_user.username e current_user.avatar (CLAUDE.md, Punti delicati).
Le tabelle le crea solo migrations/001_init.sql, mai questi modelli.
"""

from datetime import datetime

import sqlalchemy as sa
from flask_login import UserMixin
from sqlalchemy.dialects.mysql import INTEGER, VARCHAR
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "utenti"

    id: Mapped[int] = mapped_column(INTEGER(unsigned=True), primary_key=True)
    # "Mario" e "mario" sono due utenti diversi (D7): collation che distingue le maiuscole
    username: Mapped[str] = mapped_column(
        "nome_utente",
        VARCHAR(20, charset="utf8mb4", collation="utf8mb4_0900_as_cs"),
        unique=True,
    )
    # Unica senza distinguere le maiuscole; mai mostrata agli altri utenti
    email: Mapped[str] = mapped_column(sa.String(254), unique=True)
    password_hash: Mapped[str] = mapped_column("hash_password", sa.String(255))
    # Codice di un avatar predefinito (D29); vuoto = iniziale del nome
    avatar: Mapped[str | None] = mapped_column(sa.String(30))
    created_at: Mapped[datetime] = mapped_column(
        "creato_il", sa.DateTime, server_default=sa.text("CURRENT_TIMESTAMP")
    )
