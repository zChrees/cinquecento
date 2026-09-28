"""Inviti a partita (P47; decisioni D27, D36; contratto 5.3), in memoria.

- Si invita **un amico alla volta**: chi ha già un invito aperto ("pending" o
  "accepted"), da mandato o da ricevuto, non può mandarne né riceverne un altro (busy).
- L'invito "pending" scade dopo INVITE_SECONDS senza risposta ("expired"). Dopo
  "accepted" non scade più (scelta di Giuseppe): resta aperto finché chi ha invitato
  preme "Gioca" ("started"), lo annulla ("cancelled"), l'invitato rifiuta ("declined")
  o uno dei due chiude tutte le schede ("cancelled").
- Stati: pending → accepted | declined | expired | cancelled; accepted → started |
  declined | cancelled. "started", "declined", "expired" e "cancelled" sono finali.
- Ogni cambio di stato chiama `on_change(invito)` (friends_events.py manda
  invite:update a tutti e due), fuori dal lock.
- Qui ci sono solo gli inviti: amicizia, chi è online, partite e coda li controlla
  friends_events.py. Nei log solo numeri di utente.
"""

import logging
import secrets
import threading
import time
from dataclasses import dataclass

from app.realtime.events import EventError
from config import BaseConfig

log = logging.getLogger(__name__)

INVITE_SECONDS = BaseConfig.INVITE_SECONDS  # letto a ogni invito: i test lo riducono
OPEN = ("pending", "accepted")


@dataclass
class Invite:
    invite_id: str
    sender: object  # Player
    recipient: object  # Player
    mode: str
    target_score: int
    deadline: float
    status: str = "pending"
    timer: object = None

    def involves(self, user_id):
        return user_id in (self.sender.user_id, self.recipient.user_id)

    def data(self, now):
        """L'invito nella forma del contratto (5.3)."""
        return {
            "invite_id": self.invite_id,
            "from": _user(self.sender),
            "to": _user(self.recipient),
            "mode": self.mode,
            "target_score": self.target_score,
            "status": self.status,
            "seconds_left": round(max(0.0, self.deadline - now), 1) if self.status == "pending" else 0.0,
        }


def _user(player):
    return {"user_id": player.user_id, "username": player.username, "avatar": player.avatar}


class Invites:
    def __init__(self, clock=time.monotonic):
        self._clock = clock
        self.lock = threading.RLock()  # friends_events.py lo tiene anche mentre avvia la partita
        self._invites = {}  # invite_id -> Invite (anche quelli finiti, finché non se ne apre un altro)
        self.on_change = None

    # --- Lettura ---

    def get(self, invite_id):
        with self.lock:
            return self._invites.get(invite_id) if isinstance(invite_id, str) else None

    def open_of(self, user_id):
        """L'invito aperto ("pending" o "accepted") di quell'utente, mandato o ricevuto, o None."""
        with self.lock:
            return next((i for i in self._invites.values() if i.status in OPEN and i.involves(user_id)), None)

    def data(self, invite):
        return invite.data(self._clock())

    # --- Scritture ---

    def send(self, sender, recipient, mode, target_score):
        """Nuovo invito "pending"; busy se uno dei due ha già un invito aperto."""
        with self.lock:
            if self.open_of(sender.user_id) is not None:
                raise EventError("busy", "Hai già un invito aperto: aspetta la risposta o annullalo.")
            if self.open_of(recipient.user_id) is not None:
                raise EventError("busy", f"{recipient.username} ha già un invito in sospeso.")
            self._forget(sender.user_id, recipient.user_id)
            seconds = INVITE_SECONDS
            invite = Invite(self._new_id(), sender, recipient, mode, target_score, self._clock() + seconds)
            invite.timer = threading.Timer(seconds, self._expire, args=(invite.invite_id,))
            invite.timer.daemon = True
            self._invites[invite.invite_id] = invite
            invite.timer.start()
            log.info("Invito %s da %s a %s (%s a %s)", invite.invite_id, sender.user_id,
                     recipient.user_id, mode, target_score)
            return invite

    def accept(self, invite_id, user_id):
        with self.lock:
            invite = self._of_recipient(invite_id, user_id)
            if invite.status == "accepted":
                return invite  # seconda volta: niente da fare
            if invite.status == "expired":
                raise EventError("expired", "L'invito è scaduto.")
            if invite.status != "pending":
                raise EventError("not_found", "Questo invito non c'è più.")
            self._set(invite, "accepted")
        self._changed(invite)
        return invite

    def decline(self, invite_id, user_id):
        """L'invitato rifiuta (anche dopo aver accettato); a invito già finito non fa niente."""
        with self.lock:
            invite = self._of_recipient(invite_id, user_id)
            if invite.status not in OPEN:
                return invite
            self._set(invite, "declined")
        self._changed(invite)
        return invite

    def cancel(self, invite_id, user_id):
        """Chi ha invitato annulla; a invito già finito non fa niente."""
        with self.lock:
            invite = self.get(invite_id)
            if invite is None or invite.sender.user_id != user_id:
                raise EventError("not_found", "Questo invito non esiste.")
            if invite.status not in OPEN:
                return invite
            self._set(invite, "cancelled")
        self._changed(invite)
        return invite

    def accepted_of_sender(self, invite_id, user_id):
        """Per invite:start (sotto self.lock): l'invito accettato mandato da `user_id`."""
        invite = self.get(invite_id)
        if invite is None or invite.sender.user_id != user_id:
            raise EventError("not_found", "Questo invito non esiste.")
        if invite.status == "expired":
            raise EventError("expired", "L'invito è scaduto.")
        if invite.status != "accepted":
            raise EventError("not_allowed", "Puoi giocare solo dopo che l'amico ha accettato.")
        return invite

    def mark_started(self, invite):
        with self.lock:
            self._set(invite, "started")
        self._changed(invite)

    def cancel_all_of(self, user_id, *, only_with=None):
        """Annulla gli inviti aperti di quell'utente (ultima scheda chiusa, amicizia tolta,
        blocco); con `only_with` solo quelli con quell'altro utente."""
        with self.lock:
            invites = [i for i in self._invites.values()
                       if i.status in OPEN and i.involves(user_id)
                       and (only_with is None or i.involves(only_with))]
            for invite in invites:
                self._set(invite, "cancelled")
        for invite in invites:
            self._changed(invite)
        return invites

    # --- Interni ---

    def _of_recipient(self, invite_id, user_id):
        invite = self.get(invite_id)
        if invite is None or invite.recipient.user_id != user_id:
            raise EventError("not_found", "Questo invito non esiste.")
        return invite

    def _set(self, invite, status):
        invite.status = status
        if status != "pending" and invite.timer is not None:
            invite.timer.cancel()
            invite.timer = None
        log.info("Invito %s: %s", invite.invite_id, status)

    def _expire(self, invite_id):
        with self.lock:
            invite = self._invites.get(invite_id)
            if invite is None or invite.status != "pending":
                return
            self._set(invite, "expired")
        self._changed(invite)

    def _changed(self, invite):
        if self.on_change is not None:
            try:
                self.on_change(invite)
            except Exception:
                log.exception("Avviso del cambio di stato dell'invito %s non riuscito", invite.invite_id)

    def _forget(self, *user_ids):
        """Dimentica gli inviti finiti di quegli utenti (restano solo finché serve rispondere)."""
        for invite_id, invite in list(self._invites.items()):
            if invite.status not in OPEN and any(invite.involves(u) for u in user_ids):
                del self._invites[invite_id]

    def _new_id(self):
        invite_id = f"inv_{secrets.token_urlsafe(9)}"
        while invite_id in self._invites:
            invite_id = f"inv_{secrets.token_urlsafe(9)}"
        return invite_id


invites = Invites()
