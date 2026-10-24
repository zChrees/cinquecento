"""Accesso alle tabelle amicizie, blocchi e (in lettura) messaggi (P45).

Qui non si fa commit: la transazione la chiude il servizio (friend_service).
Una riga di amicizie per coppia, in qualunque direzione (vincolo uq_amicizie_coppia):
stato 'in_attesa' = richiesta, 'accettata' = amicizia.
Date e ore si scrivono da Python in UTC, non con CURRENT_TIMESTAMP di MySQL, che
userebbe il fuso orario del server (001_init.sql: "date e ore sempre in UTC").

Cosa contiene:
    PENDING, ACCEPTED              i due stati di una riga di amicizie
    utc_now()                      l'ora di adesso in UTC, al secondo
    lock_users(7, 8)               blocca le righe dei due utenti fino alla fine della transazione
    get_pair(7, 8)                 la riga di amicizie tra 7 e 8, o None
    add_request(7, 8)              la richiesta di 7 a 8
    accept(row)                    la richiesta diventa amicizia
    delete(row)                    cancella una riga di amicizie o di blocchi
    count_friends(7)               quanti amici ha 7
    get_block(7, 8)                il blocco di 7 su 8, o None
    add_block(7, 8)                7 blocca 8
    friends_of(7)                  gli amici di 7, per username
    requests_in(7), requests_out(7)   le richieste ricevute e mandate
    blocked_by(7)                  gli utenti bloccati da 7
    unread_by_sender(7)            i messaggi non letti di 7 per mittente: {8: 2}

DA DOVE ARRIVANO I DATI: le chiamano friend_service.py (rotte /api/friends/...),
chat_service.py (amicizia, blocchi e lock_users prima di un messaggio) e
app/sockets/friends_events.py (gli amici da avvisare, l'amicizia prima di un invito).
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
    """Già al secondo, come le colonne DATETIME delle amicizie e dei blocchi: MySQL
    arrotonderebbe i decimali, e la risposta di POST /api/friends/requests avrebbe un'ora
    diversa da quella della lista (P31).

    In parole semplici:
        utc_now()
        Per esempio datetime(2026, 9, 28, 14, 3, 12): senza fuso orario (tzinfo=None,
        come le colonne DATETIME) e con i microsecondi a zero.
    """
    return datetime.now(UTC).replace(tzinfo=None, microsecond=0)


def lock_users(*user_ids):
    """Blocca in scrittura le righe dei due utenti fino alla fine della transazione.

    Tutte le scritture sulle amicizie di una coppia passano da qui, sempre nello stesso
    ordine (id crescente): due richieste contemporanee si mettono in fila e i controlli
    che seguono vedono i dati già aggiornati. Restituisce gli id che esistono.

    In parole semplici:
        lock_users(8, 7)
        *user_ids: l'asterisco raccoglie tutti i numeri dati in una tupla, qui (8, 7).
        SELECT id FROM utenti WHERE id IN (7, 8) ORDER BY id FOR UPDATE: "FOR UPDATE"
        (with_for_update) blocca le righe lette; un'altra transazione che vuole le
        stesse righe aspetta il commit o il rollback di questa.
        Restituisce un insieme (set) con gli id trovati, per esempio {7, 8}, oppure {7}
        se l'utente 8 non esiste più.
    """
    # ids: i numeri senza doppioni (set) e in ordine crescente (sorted), per esempio [7, 8]
    ids = sorted(set(user_ids))
    rows = db.session.execute(
        sa.select(User.id).where(User.id.in_(ids)).order_by(User.id).with_for_update()
    )
    return set(rows.scalars())


def get_pair(a, b):
    """La riga di amicizie tra a e b, in qualunque direzione, o None.

    In parole semplici:
        get_pair(7, 8)
        WHERE (richiedente_id = 7 AND destinatario_id = 8) OR (richiedente_id = 8 AND
        destinatario_id = 7): trova sia la richiesta di 7 a 8 sia quella di 8 a 7.
    """
    return db.session.scalar(sa.select(Friendship).where(sa.or_(
        sa.and_(Friendship.requester_id == a, Friendship.addressee_id == b),
        sa.and_(Friendship.requester_id == b, Friendship.addressee_id == a),
    )))


def add_request(requester_id, addressee_id):
    """Prepara la richiesta di amicizia (stato in_attesa) e la restituisce.

    In parole semplici:
        add_request(7, 8): 7 chiede l'amicizia a 8, con l'ora di adesso.
    """
    row = Friendship(
        requester_id=requester_id, addressee_id=addressee_id, status=PENDING, requested_at=utc_now()
    )
    db.session.add(row)
    return row


def accept(row):
    """La richiesta diventa amicizia, con l'ora della risposta.

    In parole semplici:
        accept(row)
        row: la riga di amicizie in attesa (da get_pair)
    """
    row.status = ACCEPTED
    row.answered_at = utc_now()


def delete(row):
    """Cancella una riga di amicizie o di blocchi al commit.

    In parole semplici:
        delete(row)
        row: una riga di get_pair o di get_block
    """
    db.session.delete(row)


def count_friends(user_id):
    """Quante amicizie accettate ha un utente.

    In parole semplici:
        count_friends(7)
        SELECT COUNT(*) FROM amicizie WHERE stato = 'accettata' AND
        (richiedente_id = 7 OR destinatario_id = 7), per esempio 12.
    """
    return db.session.scalar(sa.select(sa.func.count()).select_from(Friendship).where(
        Friendship.status == ACCEPTED,
        sa.or_(Friendship.requester_id == user_id, Friendship.addressee_id == user_id),
    ))


def get_block(blocker_id, blocked_id):
    """Il blocco di blocker_id su blocked_id, o None.

    In parole semplici:
        get_block(7, 8)
        La chiave primaria di blocchi è la coppia (bloccante, bloccato): si passa come tupla.
    """
    return db.session.get(Block, (blocker_id, blocked_id))


def add_block(blocker_id, blocked_id):
    """Prepara il blocco e lo restituisce.

    In parole semplici:
        add_block(7, 8): 7 blocca 8, con l'ora di adesso.
    """
    row = Block(blocker_id=blocker_id, blocked_id=blocked_id, blocked_at=utc_now())
    db.session.add(row)
    return row


def friends_of(user_id):
    """Amici (amicizie accettate): utenti ordinati per username.

    In parole semplici:
        friends_of(7)
        other: "l'altro della coppia". sa.case è il CASE WHEN di SQL: se 7 è il
        richiedente l'altro è il destinatario, altrimenti il richiedente. La query
        unisce (join) utenti e amicizie su quell'altro.
        Restituisce un elenco di utenti, per esempio [Luca, Nina].
    """
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
    """Richieste ricevute: coppie (utente che l'ha mandata, data), la più recente prima.

    In parole semplici:
        requests_in(7)
        Per esempio [(nina, datetime(2026, 9, 28, 14, 3, 12))]: ogni riga ha due
        valori, l'utente e la colonna richiesta_il.
    """
    return db.session.execute(
        sa.select(User, Friendship.requested_at)
        .join(Friendship, User.id == Friendship.requester_id)
        .where(Friendship.addressee_id == user_id, Friendship.status == PENDING)
        .order_by(Friendship.requested_at.desc(), User.id)
    ).all()


def requests_out(user_id):
    """Richieste mandate: coppie (utente a cui è andata, data), la più recente prima.

    In parole semplici:
        requests_out(7): come requests_in, ma con le richieste che ha mandato 7.
    """
    return db.session.execute(
        sa.select(User, Friendship.requested_at)
        .join(Friendship, User.id == Friendship.addressee_id)
        .where(Friendship.requester_id == user_id, Friendship.status == PENDING)
        .order_by(Friendship.requested_at.desc(), User.id)
    ).all()


def blocked_by(user_id):
    """Utenti bloccati da user_id, ordinati per username.

    In parole semplici:
        blocked_by(7) -> per esempio [Luca].
    """
    return db.session.scalars(
        sa.select(User).join(Block, User.id == Block.blocked_id)
        .where(Block.blocker_id == user_id)
        .order_by(User.username)
    ).all()


def unread_by_sender(user_id):
    """Messaggi non letti ricevuti da user_id: {mittente: quanti}.

    In parole semplici:
        unread_by_sender(7)
        SELECT mittente_id, COUNT(*) ... GROUP BY mittente_id: una riga per mittente,
        ognuna una coppia (mittente, quanti). Per esempio {8: 2}; un mittente senza
        messaggi da leggere manca dal dizionario.
    """
    rows = db.session.execute(
        sa.select(ChatMessage.sender_id, sa.func.count())
        .where(ChatMessage.recipient_id == user_id, ChatMessage.read_at.is_(None))
        .group_by(ChatMessage.sender_id)
    )
    counts = {}
    for sender_id, count in rows:
        counts[sender_id] = count
    return counts
