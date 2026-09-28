"""Code di matchmaking (P28, P29; decisioni D16, D17; contratto 4).

- Una coda per modalità e punteggio (code separate). Ogni utente sta in coda una volta
  sola: un secondo queue:join (un'altra scheda, un request_id nuovo) riceve `busy`.
- In coda ci sono **voci**: un giocatore singolo, oppure nel 2v2 una **coppia già
  formata** (l'amico compagno, P47: join_pair), che resta sempre nella stessa squadra.
- Intervallo di rating accettato (D16): ±MATCH_RANGE_START, che si allarga di
  MATCH_RANGE_STEP ogni MATCH_RANGE_STEP_SECONDS fino a ±MATCH_RANGE_MAX; dopo
  MATCH_ANY_AFTER_SECONDS va bene qualunque avversario (`rating_range` null). Il rating
  di una coppia è la media dei due.
- Le voci si abbinano solo se **si accettano a vicenda**: la differenza di rating tra
  due voci qualsiasi della partita sta nell'intervallo di tutte e due (scelta di
  Giuseppe, P28). Si serve prima chi aspetta da più tempo; tra le partite possibili si
  sceglie quella con i rating più vicini, poi con le squadre più bilanciate.
- 2v2 (D17, scelta di Giuseppe): con quattro singoli le squadre si formano in modo che
  le medie delle due squadre siano il più vicine possibile; una coppia gioca contro due
  singoli o contro un'altra coppia.
- Se esce uno della coppia (Annulla, ultima scheda chiusa) esce tutta la coppia: lui
  riceve queue:left "cancelled", il compagno "partner_left".
- Il controllo delle code gira in un thread, avviato al primo ingresso con
  l'applicazione Flask: prova gli abbinamenti ogni CHECK_SECONDS e subito dopo ogni
  ingresso, e rimanda queue:status quando l'intervallo si allarga. La partita si crea
  con create_room dentro app.app_context(), così a fine partita si salva (P26).
- Chi chiude tutte le schede esce dalla coda (connection_events.py, scelta di Giuseppe).
- Tutto in memoria (un solo processo), sotto il lock della coda; create_room e gli
  invii ai client stanno fuori da quel lock.
Nei log solo numeri di utente.
"""

import itertools
import logging
import math
import secrets
import threading
import time
from dataclasses import dataclass

from app.extensions import socketio
from app.realtime.events import EventError, user_channel
from app.realtime.room import MODES, Player
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
CANDIDATES = 8  # voci più vicine di rating esaminate per ogni partita: il calcolo resta leggero

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
    """Una voce della coda: un giocatore, o una coppia (stessa squadra)."""

    players: tuple  # Player
    ratings: tuple  # float, uno per giocatore
    mode: str
    target_score: int
    joined_at: float
    stage: object = 0  # ultimo stadio mandato con queue:status

    @property
    def user_ids(self):
        return tuple(p.user_id for p in self.players)

    @property
    def rating(self):
        return sum(self.ratings) / len(self.ratings)

    @property
    def size(self):
        return len(self.players)

    def partner_of(self, user_id):
        return next((p for p in self.players if p.user_id != user_id), None)


@dataclass(frozen=True)
class Match:
    """Una partita trovata: le voci abbinate e le due squadre (tuple di Player)."""

    mode: str
    target_score: int
    entries: tuple
    teams: tuple

    @property
    def user_ids(self):
        return tuple(u for entry in self.entries for u in entry.user_ids)


def _balanced_teams(entries):
    """Le due squadre con le medie più vicine, senza dividere le coppie (D17).
    Restituisce (squadre, differenza tra le medie)."""
    size = MODES[entries[0].mode] // 2
    best = None
    for sides in itertools.product((0, 1), repeat=len(entries)):
        if sides[0] != 0:  # le stesse squadre scambiate: già provate
            continue
        teams = ([], [])
        for entry, side in zip(entries, sides, strict=True):
            teams[side].extend(zip(entry.players, entry.ratings, strict=True))
        if len(teams[0]) != size or len(teams[1]) != size:
            continue
        gap = abs(sum(r for _, r in teams[0]) - sum(r for _, r in teams[1])) / size
        if best is None or gap < best[1]:
            best = (tuple(tuple(p for p, _ in team) for team in teams), gap)
    return best


class MatchQueue:
    """Le code, senza Flask né socket: si prova con un orologio finto."""

    def __init__(self, clock=time.monotonic):
        self._clock = clock
        self._lock = threading.Lock()
        self._entries = {}  # user_id -> Entry (i due della coppia puntano alla stessa voce)

    def join(self, player, mode, target_score, rating):
        """Mette in coda un giocatore e restituisce il suo stato (queue:status). Già in coda → busy."""
        return self.join_entry((player,), (rating,), mode, target_score)[player.user_id]

    def join_entry(self, players, ratings, mode, target_score):
        """Mette in coda un giocatore o una coppia; {user_id: stato} per ognuno."""
        with self._lock:
            if any(p.user_id in self._entries for p in players):
                raise EventError("busy", "Sei già in coda." if len(players) == 1
                                 else "Tu o il tuo compagno siete già in coda.")
            now = self._clock()
            entry = Entry(tuple(players), tuple(ratings), mode, target_score, now, stage_of(0))
            for user_id in entry.user_ids:
                self._entries[user_id] = entry
            return {user_id: self._status(entry, now, user_id) for user_id in entry.user_ids}

    def leave(self, user_id):
        """Toglie dalla coda la voce di quell'utente (con la coppia, tutti e due);
        restituisce la voce, o None se non c'era."""
        with self._lock:
            entry = self._entries.get(user_id)
            if entry is not None:
                self._remove(entry)
            return entry

    def requeue(self, entry):
        """Rimette in coda una voce abbinata a una partita che non è partita, con la sua attesa."""
        with self._lock:
            if not any(u in self._entries for u in entry.user_ids):
                for user_id in entry.user_ids:
                    self._entries[user_id] = entry

    def status(self, user_id):
        """Lo stato della coda di quell'utente, o None se non è in coda."""
        with self._lock:
            entry = self._entries.get(user_id)
            return None if entry is None else self._status(entry, self._clock(), user_id)

    def __contains__(self, user_id):
        with self._lock:
            return user_id in self._entries

    def __len__(self):
        """Quanti utenti sono in coda."""
        with self._lock:
            return len(self._entries)

    def _remove(self, entry):
        for user_id in entry.user_ids:
            if self._entries.get(user_id) is entry:
                del self._entries[user_id]

    def _unique_entries(self):
        return list({id(e): e for e in self._entries.values()}.values())

    def _status(self, entry, now, user_id):
        waited = now - entry.joined_at
        half = half_width(stage_of(waited))
        rating_range = None if half is None else {
            "min": max(0, round(entry.rating - half)),
            "max": round(entry.rating + half),
        }
        partner = entry.partner_of(user_id)
        return {
            "mode": entry.mode,
            "target_score": entry.target_score,
            "seconds_waiting": int(waited),
            "rating_range": rating_range,
            "partner": None if partner is None else {
                "user_id": partner.user_id, "username": partner.username, "avatar": partner.avatar,
            },
        }

    def _accepts(self, entry, other, now):
        half = half_width(stage_of(now - entry.joined_at))
        return half is None or abs(entry.rating - other.rating) <= half

    def _best_match(self, first, others, now):
        """La partita migliore che comprende `first`, con voci prese da `others`, o None."""
        players = MODES[first.mode]
        compatible = sorted(
            (o for o in others
             if (o.mode, o.target_score) == (first.mode, first.target_score)
             and self._accepts(first, o, now) and self._accepts(o, first, now)),
            key=lambda o: (abs(o.rating - first.rating), o.joined_at),
        )[:CANDIDATES]
        best = None
        for count in range(1, players):
            for group in itertools.combinations(compatible, count):
                entries = (first, *group)
                if sum(e.size for e in entries) != players:
                    continue
                if not all(self._accepts(a, b, now) for a, b in itertools.permutations(group, 2)):
                    continue
                teams, gap = _balanced_teams(entries)
                ratings = [e.rating for e in entries]
                key = (max(ratings) - min(ratings), gap, [e.joined_at for e in group])
                if best is None or key < best[0]:
                    best = (key, Match(first.mode, first.target_score, entries, teams))
        return None if best is None else best[1]

    def take_matches(self):
        """Le partite possibili adesso, con le voci tolte dalla coda: lista di Match."""
        with self._lock:
            now = self._clock()
            waiting = sorted(self._unique_entries(), key=lambda e: e.joined_at)
            used, matches = set(), []
            for entry in waiting:
                if id(entry) in used:
                    continue
                others = [o for o in waiting if o is not entry and id(o) not in used]
                match = self._best_match(entry, others, now)
                if match is None:
                    continue
                used.update(id(e) for e in match.entries)
                matches.append(match)
            for match in matches:
                for entry in match.entries:
                    self._remove(entry)
            return matches

    def take_updates(self):
        """Chi deve ricevere un queue:status perché il suo intervallo si è allargato: [(user_id, stato)]."""
        with self._lock:
            now = self._clock()
            updates = []
            for entry in self._unique_entries():
                stage = stage_of(now - entry.joined_at)
                if stage != entry.stage:
                    entry.stage = stage
                    updates.extend((u, self._status(entry, now, u)) for u in entry.user_ids)
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
        return self._join(app, (user,), mode, target_score, sid)[user.id]

    def join_pair(self, app, user, partner, target_score, sid=None):
        """Una coppia già formata entra nella coda 2v2 (per P47, invite:start dell'amico
        compagno). Accetta utenti (User) o Player. Restituisce lo stato della coda di
        `user`; il compagno lo riceve con queue:status. `sid` è la scheda di `user` che ha
        fatto la richiesta, se c'è."""
        user, partner = Player.of(user), Player.of(partner)
        if user.user_id == partner.user_id:
            raise EventError("invalid_data", "Non puoi fare coppia con te stesso.")
        return self._join(app, (user, partner), "2v2", target_score, sid)[user.user_id]

    def _join(self, app, users, mode, target_score, sid):
        users = tuple(Player.of(u) for u in users)
        if any(find_room_of_user(u.user_id) is not None for u in users):
            raise EventError("busy", "Hai già una partita in corso." if len(users) == 1
                             else "Tu o il tuo compagno avete già una partita in corso.")
        ratings = []
        for user in users:
            value = rating_repo.get_value(user.user_id, mode)
            ratings.append(RATING_INITIAL if value is None else value)
        statuses = self.queue.join_entry(users, tuple(ratings), mode, target_score)
        log.info("In coda %s a %s: utenti %s", mode, target_score, list(statuses))
        for user_id, status in statuses.items():
            skip = sid if user_id == users[0].user_id else None  # la scheda che ha chiesto riceve la risposta
            socketio.emit("queue:status", status, to=user_channel(user_id), skip_sid=skip)
        self._start(app)
        self._wake.set()
        return statuses

    def leave(self, user_id, reason="cancelled"):
        """Esce dalla coda (anche da un'altra scheda); con una coppia esce anche il compagno,
        che riceve "partner_left". True se era in coda."""
        entry = self.queue.leave(user_id)
        if entry is None:
            return False
        log.info("Utente %s uscito dalla coda (%s)", user_id, reason)
        for other in entry.user_ids:
            socketio.emit("queue:left", {"reason": reason if other == user_id else "partner_left"},
                          to=user_channel(other))
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
        for match in self.queue.take_matches():
            self._start_game(match)
        for user_id, status in self.queue.take_updates():
            socketio.emit("queue:status", status, to=user_channel(user_id))

    def _start_game(self, match):
        rng = secrets.SystemRandom()
        teams = [list(team) for team in match.teams]
        rng.shuffle(teams)  # quale squadra comincia e chi siede dove lo decide il caso
        for team in teams:
            rng.shuffle(team)
        seats = [player for pair in zip(*teams, strict=True) for player in pair]  # posti 0 e 2 una squadra
        try:
            room = create_room(seats, match.mode, match.target_score, rated=True)
        except RoomError:
            # Qualcuno è entrato in partita per un'altra via: gli altri tornano in coda
            log.warning("Partita dalla coda non creata: utenti %s", list(match.user_ids))
            for entry in match.entries:
                if all(find_room_of_user(u) is None for u in entry.user_ids):
                    self.queue.requeue(entry)
            return
        log.info("Partita %s dalla coda %s a %s: utenti %s", room.id, match.mode, match.target_score,
                 [p.user_id for p in seats])


matchmaker = Matchmaker()
