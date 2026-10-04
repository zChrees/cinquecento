"""Accesso alla tabella utenti (P16): letture e creazione; avatar e cancellazione (P17).

Qui non si fa commit: la transazione la chiude il servizio (auth_service).
"""

import sqlalchemy as sa

from app.extensions import db
from app.models.user import User


def get_by_id(user_id):
    return db.session.get(User, user_id)


def get_by_username(username):
    """Confronto esatto: la colonna distingue le maiuscole (D7)."""
    return db.session.scalar(sa.select(User).where(User.username == username))


def get_by_email(email):
    """P96: la colonna non distingue le maiuscole, come alla registrazione ("Mario@x.it" = "mario@x.it")."""
    return db.session.scalar(sa.select(User).where(User.email == email))


def add(username, email, password_hash):
    """Prepara un utente nuovo; un username o un'email già usati li rifiuta MySQL al commit."""
    user = User(username=username, email=email, password_hash=password_hash)
    db.session.add(user)
    return user


def set_avatar(user, avatar):
    """Codice dell'avatar già controllato dal servizio; None = iniziale del nome."""
    user.avatar = avatar


def delete(user):
    """Cancella l'utente. Il resto lo fa MySQL con le chiavi esterne (001_init.sql, D6):
    rating, amicizie, blocchi e messaggi si cancellano, nelle partite resta "utente eliminato"."""
    db.session.delete(user)
