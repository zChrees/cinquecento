"""Code di matchmaking (P28; decisione D16; contratto 4).

- Una coda per modalità e punteggio (code separate). Ogni utente sta in coda una volta
  sola: un secondo queue:join (un'altra scheda, un request_id nuovo) riceve `busy`.
- Intervallo di rating accettato (D16): ±MATCH_RANGE_START, che si allarga di
  MATCH_RANGE_STEP ogni MATCH_RANGE_STEP_SECONDS fino a ±MATCH_RANGE_MAX; dopo
  MATCH_ANY_AFTER_SECONDS va bene qualunque avversario (`rating_range` null).
- Due giocatori si abbinano solo se **si accettano a vicenda**: la differenza di rating
  sta nell'intervallo di tutti e due (scelta di Giuseppe, P28). Si serve prima chi
  aspetta da più tempo, con l'avversario di rating più vicino.
- Il controllo delle code gira in un thread, avviato al primo queue:join con
  l'applicazione Flask: prova gli abbinamenti ogni CHECK_SECONDS e subito dopo ogni
  ingresso, e rimanda queue:status quando l'intervallo si allarga. La partita si crea
  con create_room dentro app.app_context(), così a fine partita si salva (P26).
- Chi chiude tutte le schede esce dalla coda (connection_events.py, scelta di Giuseppe).
- Tutto in memoria (un solo processo), sotto il lock della coda; create_room e gli
  invii ai client stanno fuori da quel lock.
Nei log solo numeri di utente.
"""

import logging
import math
import secrets
import threading
import time
from dataclasses import dataclass

from app.extensions import socketio
from app.realtime.events import EventError, user_channel
from app.realtime.room import Player
from app.realtime.room_manager import RoomError, create_room, find_room_of_user
from app.repositories import rating_repo
from config import BaseConfig

log = logging.getLogger(__name__)

# Letti al momento dell'uso: i test li riducono con monkeypatch
RANGE_START = BaseConfig.MATCH_RANGE_START
RANGE_STEP = BaseConfig.MATCH_RANGE_STEP
RANGE_STEP_SECONDS = BaseConfig.MATCH_RANGE_STEP_SECONDS
RANGE_MAX = BaseConfig.MATCH_RANGE_MAX
ANY_AFTER_SECONDS = BaseConfig.MATCH_ANY_AFTER_SECONDS
RATING_INITIAL = BaseConfig.RATING_INITIAL
CHECK_SECONDS = 1.0

ANY = "any"  # stadio in cui va bene qualunque avversario


def stage_of(waited):
    """Stadio dell'intervallo dopo `waited` secondi: 0, 1, 2… fino al massimo, poi ANY."""
    if waited >= ANY_AFTER_SECONDS:
        return ANY
    max_stage = math.ceil((RANGE_MAX - RANGE_START) / RANGE_STEP)
    return min(int(waited // RANGE_STEP_SECONDS), max_stage)


def half_width(stage):
    """Metà dell'intervallo di rating accettato in quello stadio; None = qualunque."""
    if stage == ANY:
        return None
    return min(RANGE_START + stage * RANGE_STEP, RANGE_MAX)


@dataclass
class Entry:
    player: Player
    mode: str
    target_score: int
    rating: float
    joined_at: float
    stage: object = 0  # ultimo stadio mandato con queue:status

    @property
    def user_id(self):
        return self.player.user_id


class MatchQueue:
    """Le code, senza Flask né socket: si prova con un orologio finto."""

    def __init__(self, clock=time.monotonic):
        self._clock = clock
        self._lock = threading.Lock()
        self._entries = {}  # user_id -> Entry

    def join(self, player, mode, target_score, rating):
        """Mette in coda e restituisce lo stato (queue:status). Già in coda → busy."""
        with self._lock:
            if player.user_id in self._entries:
                raise EventError("busy", "Sei già in coda.")
            now = self._clock()
            entry = Entry(player, mode, target_score, rating, now, stage_of(0))
            self._entries[player.user_id] = entry
            return self._status(entry, now)

    def leave(self, user_id):
        """Toglie dalla coda; restituisce l'Entry, o None se non c'era."""
        with self._lock:
            return self._entries.pop(user_id, None)

    def requeue(self, entry):
        """Rimette in coda un giocatore abbinato a una partita che non è partita, con la sua attesa."""
        with self._lock:
            self._entries.setdefault(entry.user_id, entry)

    def status(self, user_id):
        """Lo stato della coda di quell'utente, o None se non è in coda."""
        with self._lock:
            entry = self._entries.get(user_id)
            return None if entry is None else self._status(entry, self._clock())

    def __contains__(self, user_id):
        with self._lock:
            return user_id in self._entries

    def __len__(self):
        with self._lock:
            return len(self._entries)

    def _status(self, entry, now):
        waited = now - entry.joined_at
        half = half_width(stage_of(waited))
        rating_range = None if half is None else {
            "min": max(0, round(entry.rating - half)),
            "max": round(entry.rating + half),
        }
        return {
            "mode": entry.mode,
            "target_score": entry.target_score,
            "seconds_waiting": int(waited),
            "rating_range": rating_range,
            "partner": None,
        }

    def _accepts(self, entry, other, now):
        half = half_width(stage_of(now - entry.joined_at))
        return half is None or abs(entry.rating - other.rating) <= half

    def take_matches(self):
        """Gli abbinamenti possibili adesso, tolti dalla coda: lista di coppie di Entry."""
        with self._lock:
            now = self._clock()
            waiting = sorted(self._entries.values(), key=lambda e: e.joined_at)
            used, pairs = set(), []
            for entry in waiting:
                if entry.user_id in used:
                    continue
                candidates = [
                    other for other in waiting
                    if other is not entry and other.user_id not in used
                    and (other.mode, other.target_score) == (entry.mode, entry.target_score)
                    and self._accepts(entry, other, now) and self._accepts(other, entry, now)
                ]
                if not candidates:
                    continue
                best = min(candidates, key=lambda o: (abs(o.rating - entry.rating), o.joined_at))
                used.update((entry.user_id, best.user_id))
                pairs.append((entry, best))
            for user_id in used:
                del self._entries[user_id]
            return pairs

    def take_updates(self):
        """Chi deve ricevere un queue:status perché il suo intervallo si è allargato: [(user_id, stato)]."""
        with self._lock:
            now = self._clock()
            updates = []
            for entry in self._entries.values():
                stage = stage_of(now - entry.joined_at)
                if stage != entry.stage:
                    entry.stage = stage
                    updates.append((entry.user_id, self._status(entry, now)))
            return updates


class Matchmaker:
    """La coda con i socket: ingresso, uscita e il thread che crea le partite."""

    def __init__(self):
        self.queue = MatchQueue()
        self._wake = threading.Event()
        self._thread_lock = threading.Lock()
        self._app = None

    def join(self, app, user, mode, target_score, sid):
        """queue:join di `user` dalla scheda `sid`; restituisce lo stato della coda."""
        if find_room_of_user(user.id) is not None:
            raise EventError("busy", "Hai già una partita in corso.")
        rating = rating_repo.get_value(user.id, mode)
        status = self.queue.join(Player.of(user), mode, target_score,
                                 RATING_INITIAL if rating is None else rating)
        log.info("Utente %s in coda %s a %s", user.id, mode, target_score)
        socketio.emit("queue:status", status, to=user_channel(user.id), skip_sid=sid)  # le altre schede
        self._start(app)
        self._wake.set()
        return status

    def leave(self, user_id, reason="cancelled"):
        """Esce dalla coda (anche da un'altra scheda); True se era in coda."""
        entry = self.queue.leave(user_id)
        if entry is None:
            return False
        log.info("Utente %s uscito dalla coda (%s)", user_id, reason)
        socketio.emit("queue:left", {"reason": reason}, to=user_channel(user_id))
        return True

    def _start(self, app):
        with self._thread_lock:
            if self._app is None:
                self._app = app
                socketio.start_background_task(self._loop, app)

    def _loop(self, app):
        while True:
            self._wake.wait(CHECK_SECONDS)
            self._wake.clear()
            try:
                with app.app_context():
                    self.check()
            except Exception:
                log.exception("Errore nel controllo delle code")

    def check(self):
        """Un giro di controllo: crea le partite possibili e aggiorna gli intervalli."""
        for pair in self.queue.take_matches():
            self._start_game(pair)
        for user_id, status in self.queue.take_updates():
            socketio.emit("queue:status", status, to=user_channel(user_id))

    def _start_game(self, entries):
        entries = list(entries)
        secrets.SystemRandom().shuffle(entries)  # chi siede al posto 0 lo decide il caso
        first = entries[0]
        try:
            room = create_room([e.player for e in entries], first.mode, first.target_score, rated=True)
        except RoomError:
            # Uno dei due è entrato in partita per un'altra via: gli altri tornano in coda
            log.warning("Partita dalla coda non creata: utenti %s", [e.user_id for e in entries])
            for entry in entries:
                if find_room_of_user(entry.user_id) is None:
                    self.queue.requeue(entry)
            return
        log.info("Partita %s dalla coda %s a %s: utenti %s", room.id, first.mode, first.target_score,
                 [e.user_id for e in entries])


matchmaker = Matchmaker()
