"""Inviti a partita (P47; decisioni D27, D36; contratto 5.3), in memoria.

- Nel 1v1 si invita **un amico alla volta**: chi ha già un invito aperto ("pending" o
  "accepted"), mandato o ricevuto, non può mandarne né riceverne un altro (busy).
- Nel 2v2 (P59) chi invita può avere aperti fino a GROUP_MAX inviti, tutti 2v2 e agli
  stessi punti: sono il suo **gruppo** (group_of). Chi riceve ha sempre al massimo un
  invito aperto, e chi ha un invito ricevuto aperto non ne manda.
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

Cosa contiene:
    INVITE_SECONDS   i secondi per rispondere a un invito (da config.py)
    OPEN             gli stati di un invito aperto: ("pending", "accepted")
    GROUP_MAX        quanti amici si invitano al massimo nel 2v2 (3)
    Invite           un invito: chi lo manda, chi lo riceve, modalità, punti, stato
    Invites          l'elenco degli inviti, con il suo lucchetto
    invites          l'unico elenco del programma

DA DOVE ARRIVANO I DATI: friends_events.py (invite:send, invite:accept, invite:decline,
invite:cancel, invite:start) chiama i metodi di invites con i giocatori e il codice
dell'invito mandato dalla pagina; connection_events.py, friend_service.py e
auth_service.py annullano gli inviti (cancel_all_of) quando un utente chiude l'ultima
scheda, toglie un'amicizia o cancella l'account.
"""

import logging
import secrets
import threading
import time
from dataclasses import dataclass

from app.realtime.events import EventError
from app.realtime.room import MODES
from config import BaseConfig

log = logging.getLogger(__name__)

INVITE_SECONDS = BaseConfig.INVITE_SECONDS  # letto a ogni invito: i test lo riducono
OPEN = ("pending", "accepted")
GROUP_MAX = MODES["2v2"] - 1  # nel 2v2 al massimo 3 amici: con chi invita il tavolo è pieno


# @dataclass: scrive da solo il costruttore dai campi qui sotto (vedi il commento in
# app/game/engine/cards.py). Qui senza frozen: lo stato e il timer di un invito cambiano.
@dataclass
class Invite:
    """Un invito a partita.

    In parole semplici:
        Invite("inv_abc", mario, lucia, "1v1", 300, scadenza)
        invite_id:    il codice dell'invito, per esempio "inv_q3Zr_8kLmP1x"
        sender:       chi invita (un Player di room.py)
        recipient:    chi è invitato (un Player)
        mode:         "1v1" o "2v2"
        target_score: i punti per vincere, 150, 300 o 500
        deadline:     l'ora (time.monotonic) in cui scade se resta "pending"
        status:       lo stato, all'inizio "pending"
        timer:        il timer che lo fa scadere, None quando non serve più
    """

    invite_id: str
    sender: object  # Player
    recipient: object  # Player
    mode: str
    target_score: int
    deadline: float
    status: str = "pending"
    timer: object = None

    def involves(self, user_id):
        """True se l'utente è chi invita o chi è invitato.

        In parole semplici:
            invite.involves(7)
            Lo usano open_of, cancel_all_of e _forget per trovare gli inviti di un utente.
        """
        return user_id == self.sender.user_id or user_id == self.recipient.user_id

    def data(self, now):
        """L'invito nella forma del contratto (5.3).

        In parole semplici:
            invite.data(now)
            now: l'ora adesso (time.monotonic), per calcolare i secondi che restano.
            Restituisce per esempio {"invite_id": "inv_...", "from": {...}, "to": {...},
            "mode": "1v1", "target_score": 300, "status": "pending", "seconds_left": 41.5}.
        """
        # seconds_left: per un invito "pending" i secondi che restano (mai meno di 0),
        # arrotondati a un decimale; per gli altri stati 0
        if self.status == "pending":
            seconds_left = round(max(0.0, self.deadline - now), 1)
        else:
            seconds_left = 0.0
        return {
            "invite_id": self.invite_id,
            "from": _user(self.sender),
            "to": _user(self.recipient),
            "mode": self.mode,
            "target_score": self.target_score,
            "status": self.status,
            "seconds_left": seconds_left,
        }


def _user(player):
    """Un giocatore nella forma del contratto.

    In parole semplici:
        _user(player)
        Restituisce per esempio {"user_id": 7, "username": "Mario", "avatar": "gatto"}.
    """
    return {"user_id": player.user_id, "username": player.username, "avatar": player.avatar}


class Invites:
    """L'elenco degli inviti, aperti e appena finiti.

    In parole semplici:
        invites.send(mario, lucia, "1v1", 300)   un invito nuovo
        invites.accept(invite_id, lucia_id)      Lucia accetta
        invites.open_of(7)                       l'invito aperto dell'utente 7, o None
    """

    def __init__(self, clock=time.monotonic):
        """Crea l'elenco vuoto.

        In parole semplici:
            Invites()
            clock: facoltativo, la funzione che dà l'ora in secondi (time.monotonic);
                   i test ne passano una finta.
        """
        self._clock = clock
        # RLock: un lucchetto "rientrante", che lo stesso thread può prendere più volte
        # (per esempio send prende il lucchetto e chiama group_of, che lo prende di nuovo)
        self.lock = threading.RLock()  # friends_events.py lo tiene anche mentre avvia la partita
        self._invites = {}  # invite_id -> Invite (anche quelli finiti, finché non se ne apre un altro)
        # on_change: la funzione da chiamare a ogni cambio di stato; la mette friends_events.py
        self.on_change = None

    # --- Lettura ---

    def get(self, invite_id):
        """L'invito con quel codice, o None (anche se il codice non è un testo).

        In parole semplici:
            get("inv_abc")
            invite_id: il codice mandato dalla pagina.
        """
        with self.lock:
            if not isinstance(invite_id, str):
                return None
            return self._invites.get(invite_id)

    def open_of(self, user_id):
        """L'invito aperto ("pending" o "accepted") di quell'utente, mandato o ricevuto, o None.

        In parole semplici:
            open_of(7)
            Il primo invito aperto che riguarda l'utente (ricerca lineare), oppure None.
        """
        with self.lock:
            for invite in self._invites.values():
                if invite.status in OPEN and invite.involves(user_id):
                    return invite
            return None

    def group_of(self, sender_id):
        """Gli inviti aperti mandati da `sender_id`, nell'ordine in cui sono partiti
        (nel 1v1 al massimo uno, nel 2v2 fino a GROUP_MAX).

        In parole semplici:
            group_of(7)
            Restituisce una lista, per esempio [invito_a_lucia, invito_a_paolo]; vuota
            se l'utente non ha inviti aperti mandati da lui.
        """
        with self.lock:
            group = []
            for invite in self._invites.values():
                if invite.status in OPEN and invite.sender.user_id == sender_id:
                    group.append(invite)
            return group

    def data(self, invite):
        """L'invito nella forma del contratto, con i secondi che restano adesso.

        In parole semplici:
            data(invite)
            Chiama invite.data con l'ora dell'orologio di Invites.
        """
        return invite.data(self._clock())

    # --- Scritture ---

    def send(self, sender, recipient, mode, target_score):
        """Nuovo invito "pending". busy se chi riceve ha già un invito aperto, se chi
        manda ne ha uno ricevuto, o se ne ha già mandati e non si può aggiungerne al
        gruppo (1v1, punti o modalità diversi, gruppo pieno).

        In parole semplici:
            send(sender, recipient, mode, target_score)
            sender, recipient: chi invita e chi è invitato (Player). Arrivano da
                               friends_events.py (invite:send), che ha già controllato
                               amicizia e presenza.
            mode, target_score: modalità e punti scelti nella home.
            Restituisce l'invito nuovo; parte anche il timer che lo fa scadere.
        """
        with self.lock:
            group = self.group_of(sender.user_id)
            # received: chi manda ha un invito aperto ricevuto da un altro (non mandato da lui)
            received = self.open_of(sender.user_id) is not None and len(group) == 0

            # busy: True se non può mandare un altro invito adesso
            busy = False
            if received:
                busy = True
            elif len(group) > 0:
                # ha già mandato inviti: se ne aggiunge un altro solo nel 2v2, agli stessi punti
                if mode != "2v2":
                    busy = True
                else:
                    for other in group:
                        if other.mode != mode or other.target_score != target_score:
                            busy = True
                            break
            if busy:
                raise EventError("busy", "Hai già un invito aperto: aspetta la risposta o annullalo.")
            if len(group) >= GROUP_MAX:
                raise EventError("busy", f"Hai già invitato {GROUP_MAX} amici: il tavolo è pieno.")
            if self.open_of(recipient.user_id) is not None:
                raise EventError("busy", f"{recipient.username} ha già un invito in sospeso.")

            self._forget(sender.user_id, recipient.user_id)
            seconds = INVITE_SECONDS
            invite = Invite(self._new_id(), sender, recipient, mode, target_score, self._clock() + seconds)
            # Timer: un thread che, dopo `seconds` secondi, chiama self._expire(invite_id);
            # daemon = True: non impedisce al programma di chiudersi
            invite.timer = threading.Timer(seconds, self._expire, args=(invite.invite_id,))
            invite.timer.daemon = True
            self._invites[invite.invite_id] = invite
            invite.timer.start()
            log.info("Invito %s da %s a %s (%s a %s)", invite.invite_id, sender.user_id,
                     recipient.user_id, mode, target_score)
            return invite

    def accept(self, invite_id, user_id):
        """L'invitato accetta.

        In parole semplici:
            accept(invite_id, user_id)
            user_id: chi accetta; deve essere l'invitato. Arriva da invite:accept.
            Accettare due volte non è un errore; un invito scaduto risponde expired,
            uno finito in altro modo not_found. Restituisce l'invito.
        """
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
        """L'invitato rifiuta (anche dopo aver accettato); a invito già finito non fa niente.

        In parole semplici:
            decline(invite_id, user_id)
            user_id: chi rifiuta; deve essere l'invitato. Arriva da invite:decline.
        """
        with self.lock:
            invite = self._of_recipient(invite_id, user_id)
            if invite.status not in OPEN:
                return invite
            self._set(invite, "declined")
        self._changed(invite)
        return invite

    def cancel(self, invite_id, user_id):
        """Chi ha invitato annulla; a invito già finito non fa niente.

        In parole semplici:
            cancel(invite_id, user_id)
            user_id: chi annulla; deve essere chi ha invitato. Arriva da invite:cancel e
            da invite:start (gli inviti del gruppo che non entrano in partita).
        """
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
        """Per invite:start (sotto self.lock): l'invito accettato mandato da `user_id`.

        In parole semplici:
            accepted_of_sender(invite_id, user_id)
            Controlla che l'invito esista, che l'abbia mandato quell'utente e che sia
            stato accettato; altrimenti lancia EventError con il motivo.
            friends_events.py la chiama con il lucchetto già preso.
        """
        invite = self.get(invite_id)
        if invite is None or invite.sender.user_id != user_id:
            raise EventError("not_found", "Questo invito non esiste.")
        if invite.status == "expired":
            raise EventError("expired", "L'invito è scaduto.")
        if invite.status != "accepted":
            raise EventError("not_allowed", "Puoi giocare solo dopo che l'amico ha accettato.")
        return invite

    def mark_started(self, invite):
        """L'invito è diventato una partita ("started").

        In parole semplici:
            mark_started(invite)
            La chiama friends_events.py quando invite:start crea la partita.
        """
        with self.lock:
            self._set(invite, "started")
        self._changed(invite)

    # L'asterisco * da solo vuol dire: only_with si deve passare con il nome
    # (cancel_all_of(7, only_with=12)), mai in ordine
    def cancel_all_of(self, user_id, *, only_with=None):
        """Annulla gli inviti aperti di quell'utente (ultima scheda chiusa, amicizia tolta,
        blocco); con `only_with` solo quelli con quell'altro utente.

        In parole semplici:
            cancel_all_of(user_id)
            cancel_all_of(user_id, only_with=other_id)
            user_id:   l'utente di cui si annullano gli inviti.
            only_with: facoltativo; se c'è, solo gli inviti tra i due utenti.
            Restituisce la lista degli inviti annullati.
        """
        with self.lock:
            found = []
            for invite in self._invites.values():
                if invite.status not in OPEN or not invite.involves(user_id):
                    continue
                if only_with is None or invite.involves(only_with):
                    found.append(invite)
            for invite in found:
                self._set(invite, "cancelled")
        # Gli avvisi fuori dal lucchetto, come per gli altri cambi di stato
        for invite in found:
            self._changed(invite)
        return found

    # --- Interni ---

    def _of_recipient(self, invite_id, user_id):
        """L'invito, se `user_id` è chi lo ha ricevuto; altrimenti not_found.

        In parole semplici:
            _of_recipient(invite_id, user_id)
            La usano accept e decline: solo l'invitato può rispondere.
        """
        invite = self.get(invite_id)
        if invite is None or invite.recipient.user_id != user_id:
            raise EventError("not_found", "Questo invito non esiste.")
        return invite

    def _set(self, invite, status):
        """Cambia lo stato dell'invito (con il lucchetto già preso).

        In parole semplici:
            _set(invite, "accepted")
            Se l'invito non è più "pending", il timer della scadenza non serve più e si
            ferma. Nel log solo il codice dell'invito e lo stato.
        """
        invite.status = status
        if status != "pending" and invite.timer is not None:
            invite.timer.cancel()
            invite.timer = None
        log.info("Invito %s: %s", invite.invite_id, status)

    def _expire(self, invite_id):
        """L'invito è scaduto: la chiama il timer di send, in un thread a parte.

        In parole semplici:
            _expire(invite_id)
            Se nel frattempo l'invito non è più "pending" (accettato, annullato, ...)
            non fa niente.
        """
        with self.lock:
            invite = self._invites.get(invite_id)
            if invite is None or invite.status != "pending":
                return
            self._set(invite, "expired")
        self._changed(invite)

    def _changed(self, invite):
        """Avvisa on_change del cambio di stato (fuori dal lucchetto).

        In parole semplici:
            _changed(invite)
            Chiama on_change (friends_events.py manda invite:update ai due utenti). Se
            l'avviso non riesce lo scrive nel log, senza far fallire chi l'ha chiamata.
        """
        if self.on_change is not None:
            try:
                self.on_change(invite)
            except Exception:
                log.exception("Avviso del cambio di stato dell'invito %s non riuscito", invite.invite_id)

    def _forget(self, *user_ids):
        """Dimentica gli inviti finiti di quegli utenti (restano solo finché serve rispondere).

        In parole semplici:
            _forget(sender_id, recipient_id)
            *user_ids raccoglie in una tupla tutti i numeri passati, per esempio (7, 12).
            Toglie dall'elenco gli inviti non più aperti che riguardano uno di loro.
        """
        # list(...): una copia delle coppie (codice, invito), perché non si può togliere
        # una chiave da un dizionario mentre lo si scorre
        for invite_id, invite in list(self._invites.items()):
            if invite.status in OPEN:
                continue
            for user_id in user_ids:
                if invite.involves(user_id):
                    del self._invites[invite_id]
                    break

    def _new_id(self):
        """Un codice nuovo per un invito, che non c'è già nell'elenco.

        In parole semplici:
            _new_id()
            Per esempio "inv_q3Zr_8kLmP1x": "inv_" e 9 byte a caso scritti come testo.
        """
        invite_id = f"inv_{secrets.token_urlsafe(9)}"
        while invite_id in self._invites:
            invite_id = f"inv_{secrets.token_urlsafe(9)}"
        return invite_id


# invites: l'unico elenco del programma (un solo processo)
invites = Invites()
