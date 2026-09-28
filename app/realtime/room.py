"""Stanza in memoria: chi c'è dentro, il lock che mette in fila i suoi eventi e la partita (P23, P24, P25).

Regola (CLAUDE.md, "Stanze di gioco"): ogni evento di una stanza si elabora sotto
il lock di quella stanza, e timer e mosse passano dalla stessa via, `room.run(...)`.

P24: la stanza tiene la partita del motore, il numero `version` della vista (sale a
ogni cambiamento, anche di connessione) e la connessione al tavolo di ogni posto.
Ogni giocatore riceve solo la propria vista.

P25:
- Timer del turno (D12): a ogni cambio di turno riparte; se scade, il server gioca la
  mossa automatica del motore (auto_move, non canta mai). Il timer lavora sotto il
  lock della stanza e porta un numero di turno: se nel frattempo il giocatore ha già
  giocato, il timer non fa niente (una mossa e il timer insieme non giocano due carte).
  Il timer continua anche mentre il giocatore di turno è scollegato.
- Scollegamento: quando la scheda al tavolo di un posto si scollega, il posto risulta
  scollegato e ha RECONNECT_SECONDS per rientrare con game:join; oltre, la partita è
  persa per abbandono. Chi non è mai arrivato al tavolo non ha limite: la mossa
  automatica gioca per lui (scelta di Antonio, 28/09/2026).
- Abbandono (game:leave, o rientro fuori tempo): la partita finisce subito; nel 2v2
  perde tutta la squadra di chi ha abbandonato (D13). Il motore non conosce
  l'abbandono: il risultato lo scrive la stanza nella vista (reason "abandon").
- I tempi si leggono da TURN_SECONDS e RECONNECT_SECONDS quando la partita parte:
  i test li riducono prima di creare la stanza.

P26: la stanza tiene in memoria l'elenco delle mosse (gioca_carta, canta,
mossa_automatica, abbandono) e, quando la partita finisce (per punteggio in _apply,
per abbandono in abandon), la salva UNA volta con match_service.save_match. La
partita può finire anche per un timer, fuori da una richiesta: per questo la stanza
si ricorda l'applicazione Flask quando la partita parte. Senza applicazione (per
esempio una stanza creata dai test fuori da Flask) non si salva e lo si scrive nel
log. Se il salvataggio fallisce i giocatori vedono comunque il risultato; l'errore
va nel log.

P55: la stanza tiene solo l'ora dell'ultima frase del tavolo di ogni posto
(phrase_times, per il limite di table_phrases.py); le frasi non si salvano.

P44, P47: quando la partita finisce (una volta sola, insieme al salvataggio) la
stanza chiama le funzioni di `finish_listeners` con i giocatori e l'app Flask (o None):
home_events.py manda loro home:status (l'avviso di rientro sparisce), friends_events.py
avvisa i loro amici (friends:presence). Quando comincia le chiama `create_room`
(room_manager.py) con `start_listeners`. Si chiamano in un thread a parte, fuori dal
lock della stanza (guardano anche le altre stanze e il database).
"""

import logging
import secrets
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime

from flask import current_app, has_app_context

from app.extensions import socketio
from app.game.engine.actions import PlayCardAction, SingAction
from app.game.engine.auto_move import auto_move
from app.game.engine.cards import Card, Rank
from app.game.engine.game import apply_game, new_game
from app.game.engine.views import card_to_dict, player_view
from app.realtime.events import room_channel
from app.services import match_service
from app.services.match_service import MatchRecord, MoveRecord, PlayerRecord
from config import BaseConfig

log = logging.getLogger(__name__)

MODES = {"1v1": 2, "2v2": 4}
TURN_SECONDS = BaseConfig.TURN_SECONDS
RECONNECT_SECONDS = BaseConfig.RECONNECT_SECONDS
SING_SHOW_SECONDS = 3  # D15: per quanto la pagina mostra Re e Cavallo cantati
MODE_OF_PLAYERS = {n: mode for mode, n in MODES.items()}

# P44, P47: funzioni chiamate con (user_id dei giocatori, app) a inizio e fine partita,
# in un thread a parte (fuori dal lock)
start_listeners = []
finish_listeners = []


def notify(listeners, user_ids, app):
    user_ids = tuple(user_ids)  # prima del ciclo: un generatore lo leggerebbe solo il primo (P31)
    for listener in listeners:
        socketio.start_background_task(listener, user_ids, app)


def utc_now():
    return datetime.now(UTC).replace(tzinfo=None)


def card_details(card):
    return {"seme": card.suit.value, "valore": card.rank.value}


@dataclass(frozen=True)
class Player:
    user_id: int
    username: str
    avatar: str | None = None

    @classmethod
    def of(cls, user):
        """Da un Player o da un utente (User di app.models): se ne copiano solo i dati da mostrare."""
        if isinstance(user, cls):
            return user
        return cls(user_id=user.id, username=user.username, avatar=user.avatar)


class Room:
    def __init__(self, room_id):
        self.id = room_id
        self.channel = room_channel(room_id)
        self.lock = threading.RLock()
        self.members = set()  # user_id dei giocatori

        # Partita (P24): None finché start() non la fa partire
        self.players = ()  # Player per posto
        self.rated = True
        self.game = None
        self.version = 0
        self.sids = {}  # posto -> connessione al tavolo (l'ultima scheda che ha fatto game:join, D14)
        self._rng = None
        self._turn_started = None

        # Timer, riconnessione e abbandono (P25)
        self.turn_seconds = TURN_SECONDS
        self.reconnect_seconds = RECONNECT_SECONDS
        self.abandoned_seats = ()  # posti di chi ha abbandonato; vuoto finché nessuno abbandona
        self._turn_token = 0  # sale a ogni turno: un timer di un turno passato non fa niente
        self._turn_timer = None
        self._reconnect = {}  # posto scollegato -> (scadenza, timer)

        # Salvataggio a fine partita (P26)
        self._app = None  # l'applicazione Flask, per salvare anche dai timer
        self._started_at = None
        self._moves = []  # MoveRecord, nell'ordine della partita
        self._saved = False

        # Frasi del tavolo (P55): posto -> ora (time.monotonic) dell'ultima frase; mai il testo
        self.phrase_times = {}

    # --- Lock e membri (P23) ---

    def run(self, action, *args, **kwargs):
        """Esegue `action` sotto il lock della stanza: un evento alla volta."""
        with self.lock:
            return action(*args, **kwargs)

    def add_member(self, user_id):
        with self.lock:
            self.members.add(user_id)

    def remove_member(self, user_id):
        with self.lock:
            self.members.discard(user_id)

    def has_member(self, user_id):
        with self.lock:
            return user_id in self.members

    # --- Partita (P24) ---

    def start(self, players, target_score, rated=True, rng=None):
        """Mette i giocatori ai posti (nell'ordine dato) e fa partire la partita del motore."""
        with self.lock:
            self._rng = rng if rng is not None else secrets.SystemRandom()
            self.players = tuple(players)
            self.members = {p.user_id for p in self.players}
            self.rated = rated
            self.game = new_game(len(self.players), target_score, self._rng)
            self.version = 1
            self.turn_seconds = TURN_SECONDS
            self.reconnect_seconds = RECONNECT_SECONDS
            self._app = current_app._get_current_object() if has_app_context() else None
            self._started_at = utc_now()
            self._moves = []
            self._saved = False
            self._start_turn()

    @property
    def finished(self):
        """Partita finita: per punteggio (motore) o per abbandono (stanza)."""
        return self.game is not None and (self.game.finished or bool(self.abandoned_seats))

    def seat_of(self, user_id):
        for seat, player in enumerate(self.players):
            if player.user_id == user_id:
                return seat
        return None

    def join(self, seat, sid):
        """Collega la scheda `sid` al posto; restituisce la connessione sostituita (D14) o None.

        Se il posto era scollegato, il rientro ferma il conto alla rovescia (P25).
        """
        with self.lock:
            old = self.sids.get(seat)
            self.sids[seat] = sid
            waiting = self._reconnect.pop(seat, None)
            if waiting is not None:
                waiting[1].cancel()
            if old != sid:
                self.version += 1
            return old if old not in (None, sid) else None

    def is_table_connection(self, seat, sid):
        with self.lock:
            return self.sids.get(seat) == sid

    def play(self, seat, card: Card):
        """Gioca una carta (il motore controlla turno e regole); poi sale la version."""
        with self.lock:
            self._apply(PlayCardAction(seat, card), "gioca_carta", card_details(card))

    def sing(self, seat, suit):
        """Canta un seme; restituisce l'evento game:sang da mostrare a tutti (D15)."""
        with self.lock:
            before = len(self.game.hand.sings)
            # 40 o 20 lo decide il motore: i punti si leggono dal canto appena fatto
            self._apply(SingAction(seat, suit), "canta",
                        lambda game: {"seme": suit.value, "punti": game.hand.sings[before].points})
            done = self.game.hand.sings[before]
            return {
                "seat": seat,
                "suit": done.suit.value,
                "points": done.points,
                "cards": [card_to_dict(Card(suit, Rank.KING)), card_to_dict(Card(suit, Rank.KNIGHT))],
                "show_seconds": SING_SHOW_SECONDS,
            }

    def _apply(self, action, kind, details):
        """Applica la mossa del motore e la aggiunge all'elenco delle mosse (P26).

        `details` è il dizionario da salvare, oppure una funzione che lo ricava dalla
        partita dopo la mossa.
        """
        before = self.game
        self.game = apply_game(self.game, action, self._rng)
        if callable(details):
            details = details(self.game)
        self._moves.append(MoveRecord(hand=before.hand_number, seat=action.seat, kind=kind,
                                      details=details, at=utc_now()))
        self.version += 1
        if self.game.finished:
            self._stop_timers()
            self._save()
        elif self.game.hand.turn_seat != before.hand.turn_seat or self.game.hand_number != before.hand_number:
            self._start_turn()
        # Dopo un canto il turno resta a chi ha cantato: il suo tempo continua a scorrere

    # --- Timer del turno (P25, D12) ---

    def _start_turn(self):
        """Nuovo turno: riparte il tempo e il timer della mossa automatica (sotto il lock)."""
        if self._turn_timer is not None:
            self._turn_timer.cancel()
        self._turn_token += 1
        self._turn_started = time.monotonic()
        timer = threading.Timer(self.turn_seconds, self._turn_expired, args=(self._turn_token,))
        timer.daemon = True
        self._turn_timer = timer
        timer.start()

    def _turn_expired(self, token):
        with self.lock:
            if token != self._turn_token or self.finished:
                return  # il giocatore ha già giocato, o la partita è finita
            try:
                action = auto_move(self.game, self._rng)
                self._apply(action, "mossa_automatica", card_details(action.card))
            except Exception:
                log.exception("Mossa automatica non riuscita nella stanza %s", self.id)
                return
            log.info("Tempo scaduto nella stanza %s: mossa automatica", self.id)
            self.broadcast_states()

    def _stop_timers(self):
        if self._turn_timer is not None:
            self._turn_timer.cancel()
            self._turn_timer = None
        self._turn_token += 1
        for _deadline, timer in self._reconnect.values():
            timer.cancel()
        self._reconnect.clear()

    # --- Scollegamento, rientro e abbandono (P25) ---

    def disconnect(self, sid):
        """La scheda `sid` si è scollegata. Se era quella al tavolo di un posto, il posto
        risulta scollegato e parte il conto alla rovescia per rientrare; restituisce il
        posto, oppure None se `sid` non era al tavolo."""
        with self.lock:
            seat = next((s for s, table_sid in self.sids.items() if table_sid == sid), None)
            if seat is None:
                return None
            del self.sids[seat]
            self.version += 1
            if not self.finished:
                deadline = time.monotonic() + self.reconnect_seconds
                timer = threading.Timer(self.reconnect_seconds, self._reconnect_expired, args=(seat, deadline))
                timer.daemon = True
                self._reconnect[seat] = (deadline, timer)
                timer.start()
            return seat

    def _reconnect_expired(self, seat, deadline):
        with self.lock:
            waiting = self._reconnect.get(seat)
            if waiting is None or waiting[0] != deadline or self.finished:
                return  # è rientrato in tempo, o la partita è già finita
            log.info("Posto %s non rientrato in tempo nella stanza %s: abbandono", seat, self.id)
            if self.abandon(seat, "tempo_scaduto"):
                self.broadcast_states()

    def abandon(self, seat, reason="esci"):
        """La partita è persa per abbandono di `seat`: `reason` è "esci" (game:leave) o
        "tempo_scaduto" (non rientrato in tempo).

        Restituisce False se la partita era già finita (in quel caso non cambia niente).
        """
        with self.lock:
            if self.game is None or self.finished:
                return False
            self.abandoned_seats = (seat,)
            self._moves.append(MoveRecord(hand=self.game.hand_number, seat=seat, kind="abbandono",
                                          details={"motivo": reason}, at=utc_now()))
            self.version += 1
            self._stop_timers()
            self._save()
            return True

    # --- Salvataggio a fine partita (P26) ---

    def _save(self):
        """Salva la partita finita, una volta sola (sotto il lock). Un errore va nel log."""
        if self._saved:
            return
        self._saved = True
        notify(finish_listeners, (p.user_id for p in self.players), self._app)
        if self._app is None:
            log.warning("Partita della stanza %s non salvata: nessuna applicazione Flask", self.id)
            return
        try:
            with self._app.app_context():
                match_service.save_match(self._match_record())
        except Exception:
            log.exception("Salvataggio della partita della stanza %s non riuscito", self.id)

    def _match_record(self):
        if self.abandoned_seats:
            reason, winner = "abbandono", 1 - self.abandoned_seats[0] % 2
        else:
            reason, winner = "punteggio", self.game.result.winner_team
        return MatchRecord(
            mode=MODE_OF_PLAYERS[len(self.players)],
            target_score=self.game.target_score,
            rated=self.rated,
            started_at=self._started_at,
            ended_at=utc_now(),
            reason=reason,
            winner_team=winner,
            scores=tuple(self.game.scores),
            players=tuple(
                PlayerRecord(seat=seat, user_id=player.user_id, abandoned=seat in self.abandoned_seats)
                for seat, player in enumerate(self.players)
            ),
            moves=tuple(self._moves),
        )

    def _abandon_result(self, scores):
        losing_team = self.abandoned_seats[0] % 2  # la squadra di un posto è posto % 2 (nel 1v1 = il posto)
        return {
            "reason": "abandon",
            "winner_team": 1 - losing_team,
            "abandoned_seats": list(self.abandoned_seats),
            "scores": scores,
        }

    # --- Viste ---

    def view_for(self, seat):
        """La vista del contratto (3.3) per quel posto: quella del motore più i campi della stanza."""
        with self.lock:
            view = player_view(self.game, seat)
            view = {"game_id": self.id, "version": self.version, "rated": self.rated, **view}
            if self.abandoned_seats and not self.game.finished:
                view.update(status="finished", turn=None, legal={"play": [], "sing": []},
                            result=self._abandon_result(view["scores"]))
            now = time.monotonic()
            for entry in view["players"]:
                player = self.players[entry["seat"]]
                waiting = self._reconnect.get(entry["seat"])
                entry.update(
                    user_id=player.user_id,
                    username=player.username,
                    avatar=player.avatar,
                    connected=entry["seat"] in self.sids,
                    reconnect_seconds_left=None if waiting is None else round(max(0.0, waiting[0] - now), 1),
                )
            if view["turn"] is not None:
                elapsed = now - self._turn_started
                view["turn"].update(seconds_total=self.turn_seconds,
                                    seconds_left=round(max(0.0, self.turn_seconds - elapsed), 1))
            return view

    def send_state(self, seat):
        """Manda a un posto la sua vista, sulla sua connessione al tavolo (se c'è)."""
        with self.lock:
            sid = self.sids.get(seat)
            if sid is not None:
                socketio.emit("game:state", self.view_for(seat), to=sid)

    def broadcast_states(self):
        """Ogni giocatore collegato riceve la propria vista: mai quella degli altri."""
        with self.lock:
            for seat in range(len(self.players)):
                self.send_state(seat)
