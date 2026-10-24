"""Tabella utenti: gli account (P5).

Gli attributi sono in inglese, le colonne in italiano (D38): GET /api/auth/session
(app/blueprints/auth/api.py) legge current_user.username e current_user.avatar, e
FakeUser di tests/browser.py ha gli stessi nomi (CLAUDE.md, Punti delicati, P19).
Le tabelle le crea solo migrations/001_init.sql, mai questi modelli.

Cosa contiene:
    User   una riga della tabella utenti (un account)

Un "modello" è una classe Python che descrive una tabella (vedi il commento in
app/models/match.py): ogni attributo è una colonna, e il primo parametro di
mapped_column, quando c'è, è il nome della colonna nel database.

DA DOVE ARRIVANO I DATI: le righe le scrive e le legge user_repo.py; le leggono anche
friend_repo.py (amici, richieste, bloccati) e Flask-Login, attraverso
auth_service.load_user, per sapere chi è collegato.
"""

from datetime import datetime

import sqlalchemy as sa
from flask_login import UserMixin
from sqlalchemy.dialects.mysql import INTEGER, VARCHAR

# Mapped e mapped_column: vedi il commento in app/models/match.py
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


# class User(UserMixin, db.Model): la classe eredita da due classi insieme. db.Model la
# rende un modello di SQLAlchemy (una tabella); UserMixin di Flask-Login aggiunge quello
# che serve al login (get_id, is_authenticated, ...), così Flask-Login sa usarla.
class User(UserMixin, db.Model):
    """Un account (tabella utenti)."""

    # __tablename__: il nome della tabella nel database
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
    # Codice di un avatar predefinito (D29); vuoto = iniziale del nome.
    # str | None: un testo oppure None (la colonna può essere vuota, NULL)
    avatar: Mapped[str | None] = mapped_column(sa.String(30))
    # server_default: il valore lo mette MySQL quando crea la riga (l'ora di adesso)
    created_at: Mapped[datetime] = mapped_column(
        "creato_il", sa.DateTime, server_default=sa.text("CURRENT_TIMESTAMP")
    )
