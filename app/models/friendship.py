"""Tabelle amicizie e blocchi (P5, D23).

"Non si chiede l'amicizia a se stessi" e "non si blocca se stessi" li controlla
il servizio (P45): MySQL non ammette un CHECK su colonne con ON DELETE CASCADE.

Cosa contiene:
    STATUSES     i due stati di una riga di amicizie
    Friendship   una riga di amicizie: una richiesta in attesa o un'amicizia
    Block        una riga di blocchi: chi ha bloccato chi

Un "modello" è una classe Python che descrive una tabella (vedi il commento in
app/models/match.py): ogni attributo è una colonna, e il primo parametro di
mapped_column è il nome della colonna nel database.

DA DOVE ARRIVANO I DATI: le righe le scrive e le legge friend_repo.py; le tabelle le
crea migrations/001_init.sql.
"""

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.mysql import INTEGER

# Mapped e mapped_column: vedi il commento in app/models/match.py
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db

# Gli stati di una riga di amicizie. La colonna stato è un ENUM con DEFAULT: è
# l'eccezione alla regola "niente ENUM" di P5, scritta in migrations/001_init.sql
STATUSES = ("in_attesa", "accettata")


# db.Model: la classe di base dei modelli di Flask-SQLAlchemy (app/extensions.py)
class Friendship(db.Model):
    """Una riga per coppia, in qualunque direzione: richiesta in attesa o amicizia accettata."""

    # __tablename__: il nome della tabella nel database
    __tablename__ = "amicizie"

    # ForeignKey: la colonna punta a utenti.id; ondelete="CASCADE": cancellando
    # l'account si cancellano anche le sue amicizie e richieste.
    # La chiave primaria è la coppia (richiedente, destinatario)
    requester_id: Mapped[int] = mapped_column(
        "richiedente_id",
        INTEGER(unsigned=True),
        sa.ForeignKey("utenti.id", ondelete="CASCADE"),
        primary_key=True,
    )
    addressee_id: Mapped[int] = mapped_column(
        "destinatario_id",
        INTEGER(unsigned=True),
        sa.ForeignKey("utenti.id", ondelete="CASCADE"),
        primary_key=True,
    )
    # sa.Enum(*STATUSES): l'asterisco passa i valori della tupla uno per uno, cioè
    # sa.Enum("in_attesa", "accettata"); così l'elenco sta scritto una volta sola
    status: Mapped[str] = mapped_column(
        "stato", sa.Enum(*STATUSES), server_default="in_attesa"
    )
    requested_at: Mapped[datetime] = mapped_column(
        "richiesta_il", sa.DateTime, server_default=sa.text("CURRENT_TIMESTAMP")
    )
    # Vuota finché la richiesta è in attesa (datetime | None: un'ora oppure None)
    answered_at: Mapped[datetime | None] = mapped_column("risposta_il", sa.DateTime)
    # La coppia in ordine: le calcola MySQL e servono solo a "una riga per coppia"
    # (sa.Computed: colonna calcolata; persisted=False: MySQL non la salva, la ricalcola)
    user_low: Mapped[int | None] = mapped_column(
        "utente_minore",
        INTEGER(unsigned=True),
        sa.Computed("LEAST(richiedente_id, destinatario_id)", persisted=False),
    )
    user_high: Mapped[int | None] = mapped_column(
        "utente_maggiore",
        INTEGER(unsigned=True),
        sa.Computed("GREATEST(richiedente_id, destinatario_id)", persisted=False),
    )


class Block(db.Model):
    """Un blocco: blocker_id ha bloccato blocked_id (D23); la chiave è la coppia."""

    __tablename__ = "blocchi"

    blocker_id: Mapped[int] = mapped_column(
        "bloccante_id",
        INTEGER(unsigned=True),
        sa.ForeignKey("utenti.id", ondelete="CASCADE"),
        primary_key=True,
    )
    blocked_id: Mapped[int] = mapped_column(
        "bloccato_id",
        INTEGER(unsigned=True),
        sa.ForeignKey("utenti.id", ondelete="CASCADE"),
        primary_key=True,
    )
    blocked_at: Mapped[datetime] = mapped_column(
        "bloccato_il", sa.DateTime, server_default=sa.text("CURRENT_TIMESTAMP")
    )
