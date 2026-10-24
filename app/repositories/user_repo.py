"""Accesso alla tabella utenti (P16): letture e creazione; avatar e cancellazione (P17).

Qui non si fa commit: la transazione la chiude il servizio (auth_service).

Cosa contiene:
    get_by_id(7)                     l'utente numero 7, o None
    get_by_username("Mario")         l'utente con quello username esatto, o None
    get_by_email("mario@x.it")       l'utente con quell'email, o None
    add(username, email, hash)       prepara un utente nuovo
    set_avatar(user, "re_coppe")     cambia l'avatar
    delete(user)                     cancella l'utente

DA DOVE ARRIVANO I DATI: le chiamano auth_service.py (registrazione, login,
impostazioni, Flask-Login), friend_service.py (cercare un utente per username),
chat_service.py (controllare che l'amico esista) e app/sockets/friends_events.py
(l'amico da invitare a una partita).
"""

import sqlalchemy as sa

from app.extensions import db
from app.models.user import User


def get_by_id(user_id):
    """L'utente con quel numero, o None.

    In parole semplici:
        get_by_id(7)
        db.session.get(Modello, chiave): legge la riga con quella chiave primaria.
    """
    return db.session.get(User, user_id)


def get_by_username(username):
    """Confronto esatto: la colonna distingue le maiuscole (D7).

    In parole semplici:
        get_by_username("Mario")
        SELECT ... FROM utenti WHERE nome_utente = 'Mario'; scalar restituisce la
        prima riga, o None se non c'è. "mario" non trova Mario.
    """
    return db.session.scalar(sa.select(User).where(User.username == username))


def get_by_email(email):
    """P96: la colonna non distingue le maiuscole, come alla registrazione ("Mario@x.it" = "mario@x.it").

    In parole semplici:
        get_by_email("mario@x.it") -> l'utente, o None.
    """
    return db.session.scalar(sa.select(User).where(User.email == email))


def add(username, email, password_hash):
    """Prepara un utente nuovo; un username o un'email già usati li rifiuta MySQL al commit.

    In parole semplici:
        add("Mario", "mario@x.it", hash)
        db.session.add: l'utente si scriverà nel database al commit (di
        auth_service.register). password_hash: la password già trasformata in hash.
    """
    user = User(username=username, email=email, password_hash=password_hash)
    db.session.add(user)
    return user


def set_avatar(user, avatar):
    """Codice dell'avatar già controllato dal servizio; None = iniziale del nome.

    In parole semplici:
        set_avatar(user, "re_coppe")
        Cambia l'attributo: SQLAlchemy se ne accorge e scrive la colonna al commit.
    """
    user.avatar = avatar


def delete(user):
    """Cancella l'utente. Il resto lo fa MySQL con le chiavi esterne (001_init.sql, D6):
    rating, amicizie, blocchi e messaggi si cancellano, nelle partite resta "utente eliminato".

    In parole semplici:
        delete(user): la riga sparisce al commit (di auth_service.delete_account).
    """
    db.session.delete(user)
