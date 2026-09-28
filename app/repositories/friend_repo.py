"""Accesso alle tabelle amicizie, blocchi e (in lettura) messaggi (P45).

Qui non si fa commit: la transazione la chiude il servizio (friend_service).
Una riga di amicizie per coppia, in qualunque direzione (vincolo uq_amicizie_coppia):
stato 'in_attesa' = richiesta, 'accettata' = amicizia.
Date e ore si scrivono da Python in UTC, non con CURRENT_TIMESTAMP di MySQL, che
userebbe il fuso orario del server (001_init.sql: "date e ore sempre in UTC").
"""

from datetime import UTC, datetime

import sqlalchemy as sa

from app.extensions import db
from app.models.chat_message import ChatMessage
from app.models.friendship import Block, Friendship
from app.models.user import User

PENDING = "in_attesa"
ACCEPTED = "accettata"


def utc_now():
    return datetime.now(UTC).replace(tzinfo=None)


def lock_users(*user_ids):
    """Blocca in scrittura le righe dei due utenti fino alla fine della transazione.

    Tutte le scritture sulle amicizie di una coppia passano da qui, sempre nello stesso
    ordine (id crescente): due richieste contemporanee si mettono in fila e i controlli
    che seguono vedono i dati già aggiornati. Restituisce gli id che esistono.
    """
    ids = sorted(set(user_ids))
    rows = db.session.execute(
        sa.select(User.id).where(User.id.in_(ids)).order_by(User.id).with_for_update()
    )
    return set(rows.scalars())


def get_user(user_id):
    return db.session.get(User, user_id)


def get_pair(a, b):
    """La riga di amicizie tra a e b, in qualunque direzione, o None."""
    return db.session.scalar(sa.select(Friendship).where(sa.or_(
        sa.and_(Friendship.requester_id == a, Friendship.addressee_id == b),
        sa.and_(Friendship.requester_id == b, Friendship.addressee_id == a),
    )))


def add_request(requester_id, addressee_id):
    row = Friendship(
        requester_id=requester_id, addressee_id=addressee_id, status=PENDING, requested_at=utc_now()
    )
    db.session.add(row)
    return row


def accept(row):
    row.status = ACCEPTED
    row.answered_at = utc_now()


def delete(row):
    db.session.delete(row)


def count_friends(user_id):
    return db.session.scalar(sa.select(sa.func.count()).select_from(Friendship).where(
        Friendship.status == ACCEPTED,
        sa.or_(Friendship.requester_id == user_id, Friendship.addressee_id == user_id),
    ))


def get_block(blocker_id, blocked_id):
    return db.session.get(Block, (blocker_id, blocked_id))


def add_block(blocker_id, blocked_id):
    row = Block(blocker_id=blocker_id, blocked_id=blocked_id, blocked_at=utc_now())
    db.session.add(row)
    return row


def friends_of(user_id):
    """Amici (amicizie accettate): utenti ordinati per username."""
    other = sa.case((Friendship.requester_id == user_id, Friendship.addressee_id), else_=Friendship.requester_id)
    return db.session.scalars(
        sa.select(User)
        .join(Friendship, User.id == other)
        .where(
            Friendship.status == ACCEPTED,
            sa.or_(Friendship.requester_id == user_id, Friendship.addressee_id == user_id),
        )
        .order_by(User.username)
    ).all()


def requests_in(user_id):
    """Richieste ricevute: coppie (utente che l'ha mandata, data), la più recente prima."""
    return db.session.execute(
        sa.select(User, Friendship.requested_at)
        .join(Friendship, User.id == Friendship.requester_id)
        .where(Friendship.addressee_id == user_id, Friendship.status == PENDING)
        .order_by(Friendship.requested_at.desc(), User.id)
    ).all()


def requests_out(user_id):
    """Richieste mandate: coppie (utente a cui è andata, data), la più recente prima."""
    return db.session.execute(
        sa.select(User, Friendship.requested_at)
        .join(Friendship, User.id == Friendship.addressee_id)
        .where(Friendship.requester_id == user_id, Friendship.status == PENDING)
        .order_by(Friendship.requested_at.desc(), User.id)
    ).all()


def blocked_by(user_id):
    """Utenti bloccati da user_id, ordinati per username."""
    return db.session.scalars(
        sa.select(User).join(Block, User.id == Block.blocked_id)
        .where(Block.blocker_id == user_id)
        .order_by(User.username)
    ).all()


def unread_by_sender(user_id):
    """Messaggi non letti ricevuti da user_id: {mittente: quanti}."""
    rows = db.session.execute(
        sa.select(ChatMessage.sender_id, sa.func.count())
        .where(ChatMessage.recipient_id == user_id, ChatMessage.read_at.is_(None))
        .group_by(ChatMessage.sender_id)
    )
    return dict(rows.all())
