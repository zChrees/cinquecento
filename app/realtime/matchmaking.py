"""Code di matchmaking (P28, P29; decisioni D16, D17; contratto 4).

- Una coda per modalità e punteggio (code separate). Ogni utente sta in coda una volta
  sola: un secondo queue:join (un'altra scheda, un request_id nuovo) riceve `busy`.
- In coda ci sono **voci**: un giocatore singolo, oppure nel 2v2 una **coppia già
  formata** (l'amico compagno, P47: join_pair), che resta sempre nella stessa squadra,
  oppure un **gruppo di tre amici** (P59: join_group): due tirati a sorte fanno
  coppia, il terzo gioca contro di loro con un compagno preso dalla coda. Ogni voce
  sa in che squadra sta ciascuno dei suoi giocatori (`sides`).
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
- Se esce uno della coppia o del gruppo (Annulla, ultima scheda chiusa) esce tutta la
  voce: lui riceve queue:left "cancelled", gli altri "partner_left".
- Il controllo delle code gira in un thread, avviato al primo ingresso con
  l'applicazione Flask: prova gli abbinamenti ogni CHECK_SECONDS e subito dopo ogni
  ingresso, e rimanda queue:status quando l'intervallo si allarga. La partita si crea
  con create_room dentro app.app_context(), così a fine partita si salva (P26).
- Chi chiude tutte le schede esce dalla coda (connection_events.py, scelta di Giuseppe).
- Tutto in memoria (un solo processo), sotto il lock della coda; create_room e gli
  invii ai client stanno fuori da quel lock.
Nei log solo numeri di utente.

Cosa contiene:
    RANGE_START, ...            i numeri dell'intervallo di rating (da config.py)
    stage_of(waited)            lo "stadio" dell'attesa, per esempio stage_of(25) = 2
    half_width(stage)           metà dell'intervallo in quello stadio, per esempio 150
    Entry                       una voce della coda (uno, due o tre giocatori)
    Match                       una partita trovata: voci e squadre
    MatchQueue                  le code vere e proprie, senza Flask né socket
    Matchmaker, matchmaker      la coda con i socket e il thread che crea le partite

DA DOVE ARRIVANO I DATI: lobby_events.py chiama matchmaker.join (queue:join) e
matchmaker.leave (queue:leave); friends_events.py chiama join_pair e join_group
(invite:start nel 2v2); connection_events.py chiama leave quando un utente chiude
l'ultima scheda. Il rating di ognuno si legge dal database (rating_repo).
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
    """Stadio dell'intervallo dopo `waited` secondi: 0, 1, 2… fino al massimo, poi ANY.

    In parole semplici:
        stage_of(waited)
        waited: da quanti secondi la voce aspetta in coda.
        Ogni RANGE_STEP_SECONDS di attesa lo stadio sale di 1, fino a quello in cui
        l'intervallo arriva a RANGE_MAX; dopo ANY_AFTER_SECONDS è ANY. "//" è la
        divisione intera (come / tra due int in C).
    """
    if waited >= ANY_AFTER_SECONDS:
        return ANY
    max_stage = math.ceil((RANGE_MAX - RANGE_START) / RANGE_STEP)
    return min(int(waited // RANGE_STEP_SECONDS), max_stage)


def half_width(stage):
    """Metà dell'intervallo di rating accettato in quello stadio; None = qualunque.

    In parole semplici:
        half_width(stage)
        Per esempio con RANGE_START 100 e RANGE_STEP 50, half_width(2) = 200: va bene
        chi ha un rating fino a 200 punti più alto o più basso.
    """
    if stage == ANY:
        return None
    return min(RANGE_START + stage * RANGE_STEP, RANGE_MAX)


# @dataclass: scrive da solo il costruttore dai campi qui sotto (vedi il commento in
# app/game/engine/cards.py). Senza frozen: lo stadio di una voce cambia.
@dataclass
class Entry:
    """Una voce della coda: un giocatore, una coppia (stessa squadra) o un gruppo di tre
    (una coppia e il suo avversario).

    In parole semplici:
        Entry((mario,), (1500.0,), "1v1", 300, adesso)
        players:      i giocatori della voce (Player)
        ratings:      il rating di ognuno, nello stesso ordine
        mode, target_score: la coda in cui sta
        joined_at:    l'ora (orologio della coda) in cui è entrata
        stage:        l'ultimo stadio mandato con queue:status
        sides:        la squadra di ogni giocatore dentro la voce, per esempio (0, 0, 1)
                      per un gruppo di tre; vuota = tutti nella stessa squadra
    """

    players: tuple  # Player
    ratings: tuple  # float, uno per giocatore
    mode: str
    target_score: int
    joined_at: float
    stage: object = 0  # ultimo stadio mandato con queue:status
    sides: tuple = ()  # squadra di ogni giocatore dentro la voce (0 o 1); vuota = tutti insieme

    # @property: si legge come un campo (entry.user_ids, senza parentesi)
    @property
    def user_ids(self):
        """I numeri degli utenti della voce, per esempio (7, 12)."""
        ids = []
        for player in self.players:
            ids.append(player.user_id)
        return tuple(ids)

    @property
    def rating(self):
        """Il rating della voce: la media dei rating dei suoi giocatori."""
        total = 0
        for value in self.ratings:
            total = total + value
        return total / len(self.ratings)

    @property
    def size(self):
        """Quanti giocatori ha la voce: 1, 2 o 3."""
        return len(self.players)

    @property
    def team_sides(self):
        """La squadra di ogni giocatore dentro la voce; con sides vuota, 0 per tutti.

        In parole semplici:
            entry.team_sides
            Per esempio (0, 0) per una coppia, (0, 0, 1) per un gruppo di tre.
        """
        if len(self.sides) > 0:
            return self.sides
        return (0,) * len(self.players)

    def _side_of(self, user_id):
        """La squadra (0 o 1) di quell'utente dentro la voce.

        In parole semplici:
            _side_of(user_id)
            L'utente deve essere nella voce: lo chiamano solo partner_of e opponents_of,
            con un utente della voce.
        """
        # zip: prende un giocatore e la sua squadra alla volta; strict=True dà errore
        # se le due tuple non sono lunghe uguali
        for player, side in zip(self.players, self.team_sides, strict=True):
            if player.user_id == user_id:
                return side
        raise ValueError(f"utente {user_id} non nella voce")

    def partner_of(self, user_id):
        """Il compagno di squadra già nella voce, o None.

        In parole semplici:
            entry.partner_of(7)
            In una coppia, l'altro dei due; da solo, None.
        """
        side = self._side_of(user_id)
        for player, other_side in zip(self.players, self.team_sides, strict=True):
            if player.user_id != user_id and other_side == side:
                return player
        return None

    def opponents_of(self, user_id):
        """Gli avversari già nella voce (gruppo di tre), di solito nessuno.

        In parole semplici:
            entry.opponents_of(7)
            Una lista di Player, vuota tranne che nel gruppo di tre.
        """
        side = self._side_of(user_id)
        opponents = []
        for player, other_side in zip(self.players, self.team_sides, strict=True):
            if other_side != side:
                opponents.append(player)
        return opponents


@dataclass(frozen=True)
class Match:
    """Una partita trovata: le voci abbinate e le due squadre (tuple di Player).

    In parole semplici:
        Match("2v2", 300, (voce1, voce2, voce3), ((a, b), (c, d)))
    """

    mode: str
    target_score: int
    entries: tuple
    teams: tuple

    @property
    def user_ids(self):
        """I numeri di tutti gli utenti della partita, voce dopo voce."""
        ids = []
        # extend aggiunge in fondo tutti i numeri della voce, uno dopo l'altro
        for entry in self.entries:
            ids.extend(entry.user_ids)
        return tuple(ids)


def _balanced_teams(entries):
    """Le due squadre con le medie più vicine, senza dividere le coppie (D17) e con i
    gruppi di tre come sono (la coppia da una parte, il terzo dall'altra).
    Restituisce (squadre, differenza tra le medie).

    In parole semplici:
        _balanced_teams(entries)
        entries: le voci di una partita possibile. Arriva da _best_match.
        Prova tutti i modi di mettere ogni voce da una parte o dall'altra
        (itertools.product((0, 1), repeat=3) dà (0,0,0), (0,0,1), (0,1,0), ...), tiene
        quelli con le squadre della misura giusta e sceglie quello con le medie più
        vicine. Restituisce per esempio (((a, b), (c, d)), 12.5), oppure None se non
        c'è nessun modo.
    """
    size = MODES[entries[0].mode] // 2
    best = None
    for sides in itertools.product((0, 1), repeat=len(entries)):
        if sides[0] != 0:  # le stesse squadre scambiate: già provate
            continue
        # teams: due liste di coppie (giocatore, rating), una per squadra
        teams = ([], [])
        for entry, side in zip(entries, sides, strict=True):
            for player, rating, own in zip(entry.players, entry.ratings, entry.team_sides, strict=True):
                # ^ è lo xor dei bit: la squadra dentro la voce (own) "girata" se la
                # voce va dall'altra parte (side 1)
                teams[side ^ own].append((player, rating))
        if len(teams[0]) != size or len(teams[1]) != size:
            continue

        # gap: la differenza tra le medie delle due squadre
        totals = [0, 0]
        for index in range(2):
            for pair in teams[index]:
                totals[index] = totals[index] + pair[1]
        gap = abs(totals[0] - totals[1]) / size

        if best is None or gap < best[1]:
            # le squadre come tuple di soli giocatori (senza i rating)
            found = []
            for team in teams:
                team_players = []
                for pair in team:
                    team_players.append(pair[0])
                found.append(tuple(team_players))
            best = (tuple(found), gap)
    return best


def _user(player):
    """Un giocatore nella forma del contratto, per esempio {"user_id": 7, "username": "Mario", "avatar": "gatto"}."""
    return {"user_id": player.user_id, "username": player.username, "avatar": player.avatar}


def _busy_text(count, where):
    """Il messaggio di busy per una voce di `count` giocatori già "in coda" o "in partita".

    In parole semplici:
        _busy_text(2, "in coda")
        Restituisce per esempio "Tu o il tuo compagno siete già in coda.".
    """
    if count == 1:
        if where == "in coda":
            return "Sei già in coda."
        return "Hai già una partita in corso."
    if count == 2:
        who = "Tu o il tuo compagno"
    else:
        who = "Tu o uno dei tuoi amici"
    if where == "in coda":
        return f"{who} siete già in coda."
    return f"{who} avete già una partita in corso."


def _joined_at(entry):
    """L'ora di ingresso di una voce: la chiave per ordinarle da chi aspetta da più tempo."""
    return entry.joined_at


class MatchQueue:
    """Le code, senza Flask né socket: si prova con un orologio finto.

    In parole semplici:
        queue.join(player, "1v1", 300, 1500.0)   mette in coda
        queue.take_matches()                     le partite che si possono fare adesso
        queue.leave(7)                           toglie dalla coda
    """

    def __init__(self, clock=time.monotonic):
        """Crea le code vuote.

        In parole semplici:
            MatchQueue()
            clock: facoltativo, la funzione che dà l'ora in secondi; i test ne passano
            una finta per far passare il tempo a comando.
        """
        self._clock = clock
        # _lock: un "lucchetto" (come un mutex in C) per tutte le code
        self._lock = threading.Lock()
        self._entries = {}  # user_id -> Entry (i due della coppia puntano alla stessa voce)

    def join(self, player, mode, target_score, rating):
        """Mette in coda un giocatore e restituisce il suo stato (queue:status). Già in coda → busy.

        In parole semplici:
            queue.join(player, "1v1", 300, 1500.0)
            Una voce di un giocatore solo: chiama join_entry e prende il suo stato.
        """
        return self.join_entry((player,), (rating,), mode, target_score)[player.user_id]

    def join_entry(self, players, ratings, mode, target_score, sides=()):
        """Mette in coda un giocatore, una coppia o un gruppo; {user_id: stato} per ognuno.

        In parole semplici:
            queue.join_entry(players, ratings, mode, target_score, sides)
            Se uno dei giocatori è già in coda, rifiuta con busy. Altrimenti crea la voce
            e la registra sotto il numero di ognuno dei suoi giocatori.
            Restituisce per esempio {7: {...stato...}, 12: {...stato...}}.
        """
        with self._lock:
            for player in players:
                if player.user_id in self._entries:
                    raise EventError("busy", _busy_text(len(players), "in coda"))
            now = self._clock()
            entry = Entry(tuple(players), tuple(ratings), mode, target_score, now, stage_of(0), tuple(sides))
            for user_id in entry.user_ids:
                self._entries[user_id] = entry
            statuses = {}
            for user_id in entry.user_ids:
                statuses[user_id] = self._status(entry, now, user_id)
            return statuses

    def leave(self, user_id):
        """Toglie dalla coda la voce di quell'utente (con la coppia, tutti e due);
        restituisce la voce, o None se non c'era.

        In parole semplici:
            queue.leave(7)
            Si toglie sempre così, mai con un "del" di un utente solo (CLAUDE.md, P28).
        """
        with self._lock:
            entry = self._entries.get(user_id)
            if entry is not None:
                self._remove(entry)
            return entry

    def requeue(self, entry):
        """Rimette in coda una voce abbinata a una partita che non è partita, con la sua attesa.

        In parole semplici:
            queue.requeue(entry)
            Se nel frattempo uno dei suoi giocatori è rientrato in coda, non fa niente.
        """
        with self._lock:
            for user_id in entry.user_ids:
                if user_id in self._entries:
                    return
            for user_id in entry.user_ids:
                self._entries[user_id] = entry

    def status(self, user_id):
        """Lo stato della coda di quell'utente, o None se non è in coda."""
        with self._lock:
            entry = self._entries.get(user_id)
            if entry is None:
                return None
            return self._status(entry, self._clock(), user_id)

    def __contains__(self, user_id):
        """True se l'utente è in coda: "7 in queue" chiama questa funzione."""
        with self._lock:
            return user_id in self._entries

    def __len__(self):
        """Quanti utenti sono in coda."""
        with self._lock:
            return len(self._entries)

    def _remove(self, entry):
        """Toglie la voce da sotto il numero di ognuno dei suoi giocatori (con il lucchetto già preso).

        In parole semplici:
            _remove(entry)
            "is" confronta che sia proprio la stessa voce (lo stesso oggetto in
            memoria), non una uguale: un utente rientrato in coda ha una voce nuova.
        """
        for user_id in entry.user_ids:
            if self._entries.get(user_id) is entry:
                del self._entries[user_id]

    def _unique_entries(self):
        """Le voci della coda, ognuna una volta sola (la coppia è registrata sotto due numeri).

        In parole semplici:
            _unique_entries()
            id(e) è il numero che identifica un oggetto in memoria (come un indirizzo in
            C): due numeri che puntano alla stessa voce hanno lo stesso id. L'ordine è
            quello in cui le voci compaiono la prima volta.
        """
        seen = {}
        for entry in self._entries.values():
            if id(entry) not in seen:
                seen[id(entry)] = entry
        return list(seen.values())

    def _status(self, entry, now, user_id):
        """Lo stato della coda di un utente, nella forma di queue:status (contratto 4).

        In parole semplici:
            _status(entry, now, user_id)
            Restituisce per esempio {"mode": "1v1", "target_score": 300,
            "seconds_waiting": 12, "rating_range": {"min": 1400, "max": 1600},
            "partner": None, "opponents": []}.
        """
        waited = now - entry.joined_at
        half = half_width(stage_of(waited))
        # rating_range: l'intervallo accettato (mai sotto 0), o None se va bene chiunque
        if half is None:
            rating_range = None
        else:
            rating_range = {
                "min": max(0, round(entry.rating - half)),
                "max": round(entry.rating + half),
            }
        partner = entry.partner_of(user_id)
        if partner is None:
            partner_data = None
        else:
            partner_data = _user(partner)
        opponents = []
        for player in entry.opponents_of(user_id):
            opponents.append(_user(player))
        return {
            "mode": entry.mode,
            "target_score": entry.target_score,
            "seconds_waiting": int(waited),
            "rating_range": rating_range,
            "partner": partner_data,
            "opponents": opponents,
        }

    def _accepts(self, entry, other, now):
        """True se `entry`, con la sua attesa, accetta il rating di `other`.

        In parole semplici:
            _accepts(entry, other, now)
            Vero se va bene chiunque, o se la differenza tra i due rating sta dentro
            metà intervallo di entry. Non è simmetrico: chi aspetta da più tempo
            accetta di più, per questo si controlla nei due versi.
        """
        half = half_width(stage_of(now - entry.joined_at))
        return half is None or abs(entry.rating - other.rating) <= half

    def _best_match(self, first, others, now):
        """La partita migliore che comprende `first`, con voci prese da `others`, o None.

        In parole semplici:
            _best_match(first, others, now)
            first:  la voce che aspetta da più tempo tra quelle non ancora usate.
            others: le altre voci libere. Arrivano da take_matches.
            1. compatible: le voci della stessa coda che si accettano a vicenda con
               first, dalla più vicina di rating (al massimo CANDIDATES);
            2. si provano tutti i gruppi di voci (itertools.combinations) che con first
               fanno il numero giusto di giocatori e si accettano tutte tra loro;
            3. vince il gruppo con la chiave più piccola: prima la distanza tra i
               rating, poi lo squilibrio delle squadre, poi chi aspetta da più tempo.
            Restituisce un Match, o None.
        """
        players = MODES[first.mode]

        def closeness(other):
            """La chiave per ordinare le voci: prima la più vicina di rating, poi chi è entrata prima."""
            return (abs(other.rating - first.rating), other.joined_at)

        candidates = []
        for other in others:
            if other.mode != first.mode or other.target_score != first.target_score:
                continue
            if self._accepts(first, other, now) and self._accepts(other, first, now):
                candidates.append(other)
        # sorted non cambia l'ordine delle voci con la stessa chiave; [:CANDIDATES] tiene le prime
        compatible = sorted(candidates, key=closeness)[:CANDIDATES]

        best = None
        for count in range(1, players):
            # combinations: tutti i gruppi di `count` voci prese da compatible, senza ripetizioni
            for group in itertools.combinations(compatible, count):
                entries = (first,) + group
                total = 0
                for entry in entries:
                    total = total + entry.size
                if total != players:
                    continue
                # ogni voce del gruppo deve accettare ogni altra (permutations: tutte le coppie in ordine)
                all_accept = True
                for a, b in itertools.permutations(group, 2):
                    if not self._accepts(a, b, now):
                        all_accept = False
                        break
                if not all_accept:
                    continue
                # _balanced_teams restituisce una coppia: (squadre, squilibrio)
                balanced = _balanced_teams(entries)
                teams = balanced[0]
                gap = balanced[1]
                ratings = []
                for entry in entries:
                    ratings.append(entry.rating)
                waits = []
                for entry in group:
                    waits.append(entry.joined_at)
                # Python confronta le tuple elemento per elemento (anche la lista finale)
                key = (max(ratings) - min(ratings), gap, waits)
                if best is None or key < best[0]:
                    best = (key, Match(first.mode, first.target_score, entries, teams))
        if best is None:
            return None
        return best[1]

    def take_matches(self):
        """Le partite possibili adesso, con le voci tolte dalla coda: lista di Match.

        In parole semplici:
            queue.take_matches()
            Le voci si servono in ordine di attesa; ogni voce entra in una partita sola
            (used). La chiama check di Matchmaker, una volta al secondo.
        """
        with self._lock:
            now = self._clock()
            waiting = sorted(self._unique_entries(), key=_joined_at)
            # used: gli id delle voci già messe in una partita
            used = set()
            matches = []
            for entry in waiting:
                if id(entry) in used:
                    continue
                others = []
                for other in waiting:
                    if other is not entry and id(other) not in used:
                        others.append(other)
                match = self._best_match(entry, others, now)
                if match is None:
                    continue
                for matched in match.entries:
                    used.add(id(matched))
                matches.append(match)
            for match in matches:
                for entry in match.entries:
                    self._remove(entry)
            return matches

    def take_updates(self):
        """Chi deve ricevere un queue:status perché il suo intervallo si è allargato: [(user_id, stato)].

        In parole semplici:
            queue.take_updates()
            Per ogni voce che ha cambiato stadio dall'ultima volta, una coppia
            (user_id, stato) per ognuno dei suoi giocatori.
        """
        with self._lock:
            now = self._clock()
            updates = []
            for entry in self._unique_entries():
                stage = stage_of(now - entry.joined_at)
                if stage != entry.stage:
                    entry.stage = stage
                    for user_id in entry.user_ids:
                        updates.append((user_id, self._status(entry, now, user_id)))
            return updates


class Matchmaker:
    """La coda con i socket: ingresso, uscita e il thread che crea le partite.

    In parole semplici:
        matchmaker.join(app, user, "1v1", 300, sid)   queue:join
        matchmaker.leave(7)                           queue:leave o ultima scheda chiusa
    """

    def __init__(self):
        """Crea la coda e prepara il thread (che parte al primo ingresso).

        In parole semplici:
            Matchmaker()
            _wake è un "segnale" (threading.Event): chi lo accende sveglia subito il
            thread delle code, senza aspettare il secondo di CHECK_SECONDS.
        """
        self.queue = MatchQueue()
        self._wake = threading.Event()
        self._thread_lock = threading.Lock()
        self._app = None

    def join(self, app, user, mode, target_score, sid):
        """queue:join di `user` dalla scheda `sid`; restituisce lo stato della coda.

        In parole semplici:
            matchmaker.join(app, user, mode, target_score, sid)
            app: l'applicazione Flask, per il thread delle code. user: l'utente.
            sid: la scheda che ha chiesto (riceve lo stato come risposta, non come evento).
            Arrivano da lobby_events.py.
        """
        return self._join(app, (user,), mode, target_score, sid)[user.id]

    def join_pair(self, app, user, partner, target_score, sid=None):
        """Una coppia già formata entra nella coda 2v2 (per P47, invite:start dell'amico
        compagno). Accetta utenti (User) o Player. Restituisce lo stato della coda di
        `user`; il compagno lo riceve con queue:status. `sid` è la scheda di `user` che ha
        fatto la richiesta, se c'è.

        In parole semplici:
            matchmaker.join_pair(app, user, partner, target_score, sid)
            Arriva da friends_events.py. Va chiamata dentro Flask, come create_room.
        """
        user = Player.of(user)
        partner = Player.of(partner)
        if user.user_id == partner.user_id:
            raise EventError("invalid_data", "Non puoi fare coppia con te stesso.")
        return self._join(app, (user, partner), "2v2", target_score, sid)[user.user_id]

    def join_group(self, app, user, friends, target_score, sid=None):
        """Chi invita e due amici (P59, invite:start con due inviti accettati) entrano
        nella coda 2v2: due tirati a sorte fanno coppia, il terzo gioca contro di loro
        con un compagno preso dalla coda. Accetta utenti (User) o Player. Restituisce lo
        stato della coda di `user`; gli altri lo ricevono con queue:status.

        In parole semplici:
            matchmaker.join_group(app, user, friends, target_score, sid)
            friends: i due amici che hanno accettato. Arriva da friends_events.py.
            Dopo il mescolamento, i primi due della lista sono la coppia (sides 0, 0)
            e il terzo l'avversario (sides 1).
        """
        user = Player.of(user)
        players = [user]
        for friend in friends:
            players.append(Player.of(friend))
        # different: i numeri diversi tra loro (un insieme non tiene doppioni)
        different = set()
        for player in players:
            different.add(player.user_id)
        if len(players) != 3 or len(different) != 3:
            raise EventError("invalid_data", "Il gruppo deve avere tre giocatori diversi.")
        secrets.SystemRandom().shuffle(players)   # la coppia la decide il caso
        return self._join(app, players, "2v2", target_score, sid, sides=(0, 0, 1),
                          requester=user.user_id)[user.user_id]

    def _join(self, app, users, mode, target_score, sid, sides=(), requester=None):
        """L'ingresso in coda di una voce, per join, join_pair e join_group.

        In parole semplici:
            _join(app, users, mode, target_score, sid, sides, requester)
            1. chi è già in partita non entra (busy);
            2. si legge il rating di ognuno (RATING_INITIAL, 1500, per chi non ce l'ha);
            3. la voce entra in coda e ognuno riceve queue:status, tranne la scheda che
               ha chiesto (riceve lo stato come risposta);
            4. parte (la prima volta) e si sveglia il thread delle code.
            requester: facoltativo, chi ha fatto la richiesta; se manca, il primo di users.
        """
        player_list = []
        for user in users:
            player_list.append(Player.of(user))
        users = tuple(player_list)
        if requester is None:
            requester = users[0].user_id
        for user in users:
            if find_room_of_user(user.user_id) is not None:
                raise EventError("busy", _busy_text(len(users), "in partita"))
        ratings = []
        for user in users:
            value = rating_repo.get_value(user.user_id, mode)
            if value is None:
                ratings.append(RATING_INITIAL)
            else:
                ratings.append(value)
        statuses = self.queue.join_entry(users, tuple(ratings), mode, target_score, sides)
        log.info("In coda %s a %s: utenti %s", mode, target_score, list(statuses))
        for user_id, status in statuses.items():
            # la scheda che ha chiesto riceve la risposta: l'evento le si salta (skip_sid)
            if user_id == requester:
                skip = sid
            else:
                skip = None
            socketio.emit("queue:status", status, to=user_channel(user_id), skip_sid=skip)
        self._start(app)
        self._wake.set()
        return statuses

    def leave(self, user_id, reason="cancelled"):
        """Esce dalla coda (anche da un'altra scheda); con una coppia o un gruppo escono
        anche gli altri, che ricevono "partner_left". True se era in coda.

        In parole semplici:
            matchmaker.leave(user_id, reason)
            reason: facoltativo, il motivo per chi esce (se manca "cancelled").
        """
        entry = self.queue.leave(user_id)
        if entry is None:
            return False
        log.info("Utente %s uscito dalla coda (%s)", user_id, reason)
        for other in entry.user_ids:
            if other == user_id:
                other_reason = reason
            else:
                other_reason = "partner_left"
            socketio.emit("queue:left", {"reason": other_reason}, to=user_channel(other))
        return True

    def _start(self, app):
        """Fa partire il thread delle code, una volta sola, con l'applicazione Flask.

        In parole semplici:
            _start(app)
            start_background_task fa girare _loop in un thread a parte.
        """
        with self._thread_lock:
            if self._app is None:
                self._app = app
                socketio.start_background_task(self._loop, app)

    def _loop(self, app):
        """Il thread delle code: un giro di check al secondo, o subito se qualcuno lo sveglia.

        In parole semplici:
            _loop(app)
            Non finisce mai (while True). wait(CHECK_SECONDS) aspetta al massimo un
            secondo, meno se _wake viene acceso da un ingresso in coda. Ogni giro sta
            dentro app.app_context(), così create_room può salvare la partita (P26).
        """
        while True:
            self._wake.wait(CHECK_SECONDS)
            self._wake.clear()
            try:
                with app.app_context():
                    self.check()
            except Exception:
                log.exception("Errore nel controllo delle code")

    def check(self):
        """Un giro di controllo: crea le partite possibili e aggiorna gli intervalli.

        In parole semplici:
            matchmaker.check()
            Lo chiama _loop (e i test, per non aspettare il thread).
        """
        for match in self.queue.take_matches():
            self._start_game(match)
        for user_id, status in self.queue.take_updates():
            socketio.emit("queue:status", status, to=user_channel(user_id))

    def _start_game(self, match):
        """Crea la partita di un Match: posti a caso, una squadra ai posti pari e una ai dispari.

        In parole semplici:
            _start_game(match)
            Si mescolano le squadre (quale comincia) e i giocatori dentro ogni squadra
            (chi siede dove), poi si alternano: posti 0 e 2 una squadra, 1 e 3 l'altra.
            Se create_room rifiuta (qualcuno è già entrato in partita per un'altra via),
            gli altri tornano in coda.
        """
        rng = secrets.SystemRandom()
        teams = []
        for team in match.teams:
            teams.append(list(team))
        rng.shuffle(teams)  # quale squadra comincia e chi siede dove lo decide il caso
        for team in teams:
            rng.shuffle(team)
        # seats: un giocatore di una squadra e uno dell'altra, alternati (posti 0 e 2 una squadra)
        seats = []
        for first_team_player, second_team_player in zip(teams[0], teams[1], strict=True):
            seats.append(first_team_player)
            seats.append(second_team_player)
        try:
            room = create_room(seats, match.mode, match.target_score, rated=True)
        except RoomError:
            # Qualcuno è entrato in partita per un'altra via: gli altri tornano in coda
            log.warning("Partita dalla coda non creata: utenti %s", list(match.user_ids))
            for entry in match.entries:
                free = True
                for user_id in entry.user_ids:
                    if find_room_of_user(user_id) is not None:
                        free = False
                        break
                if free:
                    self.queue.requeue(entry)
            return
        seat_ids = []
        for player in seats:
            seat_ids.append(player.user_id)
        log.info("Partita %s dalla coda %s a %s: utenti %s", room.id, match.mode, match.target_score, seat_ids)


# matchmaker: l'unica coda del programma (un solo processo)
matchmaker = Matchmaker()
