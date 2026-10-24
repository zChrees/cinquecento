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
  persa per abbandono. P138 (R2 di REVIEW.md, cambia la scelta di Antonio del
  28/09/2026): anche chi non è ancora arrivato al tavolo ha RECONNECT_SECONDS, contati
  dall'inizio della partita; intanto la mossa automatica gioca per lui.
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

P68 (D43): partita 1v1 contro la CPU. I posti della CPU (`cpu_seats`) hanno un
giocatore finto (CPU_PLAYER, user_id 0: nessun utente vero ha 0) che non è tra i
membri, risulta sempre collegato e gioca da sé: quando tocca a lui la stanza aspetta
qualche secondo (per non giocare mentre la pagina mostra la presa o il riepilogo) e
sceglie con cpu_move dalla sua vista, sotto il lock e con il numero di turno, come il
timer. Se canta, la stanza manda game:sang a tutti e aspetta di nuovo prima della carta.
La partita non si salva e non conta per il rating; gli avvisi di inizio e fine
partita vanno solo ai giocatori veri.

P122 (D49): anche nel 2v2, con tre CPU (tutte user_id 0, nomi dati da lobby_events.py).
La CPU compagna non riceve consigli (advise li rifiuta) e non ne manda.

Cosa contiene:
    MODES, TURN_SECONDS, ...      modalità, tempi del turno e pause del tavolo
    start_listeners, finish_listeners, notify(...)   gli avvisi di inizio e fine partita
    deal_seconds, table_pause, first_deal_pause      quanto dura una pausa del tavolo
    Player, CPU_PLAYER            un giocatore seduto (nome e avatar), e la CPU
    Room                          la stanza: lock, membri, partita, timer, viste, salvataggio

Un "timer" (threading.Timer) è un thread che aspetta un certo numero di secondi e poi
chiama una funzione: qui si usano per il turno, il rientro e la CPU. Ogni funzione
chiamata da un timer prende per prima cosa il lucchetto della stanza.

DA DOVE ARRIVANO I DATI: create_room di room_manager.py crea la stanza e chiama start;
game_events.py chiama join, play, sing, lay_down, advise e abandon con i dati mandati
dalla pagina; connection_events.py chiama disconnect quando una scheda si scollega.
Le viste vanno ai giocatori con l'evento game:state.
"""

import logging
import random
import secrets
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime

from flask import current_app, has_app_context

from app.extensions import socketio
from app.game.engine.actions import LayDownAction, PlayCardAction, SingAction
from app.game.engine.auto_move import auto_move
from app.game.engine.cards import Card, Rank
from app.game.engine.cpu import CpuMemory, cpu_move
from app.game.engine.errors import InvalidMoveError
from app.game.engine.game import apply_game, new_game, partner_cards_visible
from app.game.engine.views import card_to_dict, player_view
from app.realtime.events import room_channel
from app.services import match_service
from app.services.match_service import MatchRecord, MoveRecord, PlayerRecord
from config import BaseConfig

log = logging.getLogger(__name__)

# MODES: quanti giocatori ha ogni modalità
MODES = {"1v1": 2, "2v2": 4}
TURN_SECONDS = BaseConfig.TURN_SECONDS
RECONNECT_SECONDS = BaseConfig.RECONNECT_SECONDS
SING_SHOW_SECONDS = 3  # D15: per quanto la pagina mostra Re e Cavallo cantati

# MODE_OF_PLAYERS: il contrario di MODES, dal numero di giocatori alla modalità ({2: "1v1", 4: "2v2"})
MODE_OF_PLAYERS = {}
for _mode, _count in MODES.items():
    MODE_OF_PLAYERS[_count] = _mode

# P94: pause del tavolo, le stesse di frontend/src/game/animations.ts (le confronta
# tests/sockets/test_durate_tavolo.py).
# Il conto alla rovescia del turno parte dopo la pausa, così i TURN_SECONDS sono tutti giocabili
LAST_TRICK_SECONDS = 1.5  # LAST_TRICK_MS: presa appena chiusa al centro del tavolo
SUMMARY_SECONDS = 5  # SUMMARY_MS: riepilogo di fine mano (si chiude anche prima, con "Ok")
THROW_SECONDS = 0.4  # THROW_MS: volo della carta che chiude la presa
DRAW_SECONDS = 0.5  # DRAW_MS: una pescata (una alla volta, P78)
SHUFFLE_SECONDS = 1.3  # SHUFFLE_MS: mescolata a inizio mano (D47)
DEAL_STEP_SECONDS = 0.08  # DEAL_STEP_MS: tra una carta distribuita e la successiva
LAID_DOWN_SECONDS = 3  # carte calate scoperte (D45, P85), al posto dell'ultima presa
PAUSE_SCALE = 1  # i test dei timer la mettono a 0, per non aspettare le pause

# P68: attesa della CPU prima di giocare, dopo la pausa del tavolo
CPU_SECONDS = 1.2  # per un numero a caso di CPU_JITTER (D43); poi la CPU pensa (0,1-0,3 s): circa 1-2 s
CPU_JITTER = (0.6, 1.4)

# P44, P47: funzioni chiamate con (user_id dei giocatori, app) a inizio e fine partita,
# in un thread a parte (fuori dal lock)
start_listeners = []
finish_listeners = []


def notify(listeners, user_ids, app):
    """Chiama ogni funzione di `listeners` in un thread a parte.

    In parole semplici:
        notify(finish_listeners, room.human_ids, room._app)
        listeners: un elenco di funzioni, start_listeners o finish_listeners, che altri
                   file riempiono (home_events.py, friends_events.py).
        user_ids:  i numeri dei giocatori veri.
        app:       l'applicazione Flask (o None), per leggere il database.
        Le chiamano create_room (inizio partita) e _save (fine partita).
    """
    user_ids = tuple(user_ids)  # prima del ciclo: un generatore lo leggerebbe solo il primo (P31)
    for listener in listeners:
        socketio.start_background_task(listener, user_ids, app)


def utc_now():
    """L'ora di adesso in UTC, senza fuso orario, come la vuole MySQL (DATETIME).

    In parole semplici:
        utc_now()
        Per esempio datetime(2026, 10, 24, 18, 30, 5, 123456). Si usa per l'inizio e
        la fine della partita e per l'ora di ogni mossa.
    """
    return datetime.now(UTC).replace(tzinfo=None)


def deal_seconds(players):
    """Mescolata e distribuzione di una mano: le carte partono una alla volta (DEAL_STEP_MS)
    e ognuna vola per DRAW_MS (startDeal di frontend/src/game/tableStore.ts); in secondi,
    senza PAUSE_SCALE.

    In parole semplici:
        deal_seconds(players)
        players: 2 o 4. Per esempio deal_seconds(2) = 1,3 + 9 × 0,08 + 0,5 = 2,52 secondi.
    """
    cards = players * 5  # rules.hand_size: le carte distribuite a inizio mano
    return SHUFFLE_SECONDS + (cards - 1) * DEAL_STEP_SECONDS + DRAW_SECONDS


def table_pause(before, after):
    """P94: secondi di pausa del tavolo che cominciano con la mossa da `before` a `after`.

    - mano nuova: l'ultima presa della mano (o le carte calate, P85), il riepilogo, la
      mescolata e la distribuzione;
    - presa chiusa a metà mano: l'ultima presa al centro, e intanto la carta che chiude la
      presa si posa e si pesca una carta a testa, una alla volta (P78), finché c'è il mazzo;
    - altrimenti nessuna (una carta giocata dentro la presa).
    La prima mano della partita ha la sua pausa, la distribuzione (P118: first_deal_pause).

    In parole semplici:
        table_pause(before, after)
        before, after: la partita (GameState) prima e dopo la mossa. Arrivano da _apply.
        Restituisce i secondi, già moltiplicati per PAUSE_SCALE (0 nei test dei timer).
    """
    players = after.num_players
    if after.hand_number != before.hand_number:
        # laid: True se la mano è finita con una calata
        laid = after.last_hand is not None and after.last_hand.laid_down is not None
        if laid:
            shown = LAID_DOWN_SECONDS
        else:
            shown = LAST_TRICK_SECONDS
        pause = shown + SUMMARY_SECONDS + deal_seconds(players)
    elif len(before.hand.trick) > 0 and len(after.hand.trick) == 0:
        # drawing: il volo dell'ultima carta e le pescate, solo se c'era ancora il mazzo
        if len(before.hand.deck) > 0:
            drawing = THROW_SECONDS + players * DRAW_SECONDS
        else:
            drawing = 0
        pause = max(LAST_TRICK_SECONDS, drawing)
    else:
        pause = 0.0
    return pause * PAUSE_SCALE


def first_deal_pause(players):
    """P118: all'inizio della partita la pagina mostra mescolata e distribuzione: il primo
    turno comincia dopo.

    In parole semplici:
        first_deal_pause(players)
        Come deal_seconds, moltiplicato per PAUSE_SCALE.
    """
    return deal_seconds(players) * PAUSE_SCALE


def card_details(card):
    """Una carta come si salva tra le mosse della partita (nomi italiani, D38).

    In parole semplici:
        card_details(card)
        Per esempio {"seme": "coppe", "valore": 1}.
    """
    return {"seme": card.suit.value, "valore": card.rank.value}


def _laid_down_details(game):
    """Mossa cala_carte (P84): le carte che restavano a ogni posto e i canti aggiunti per il compagno.

    In parole semplici:
        _laid_down_details(game)
        game: la partita subito dopo la calata. La chiama _apply (vedi lay_down).
        Restituisce per esempio {"mani": [{"posto": 0, "carte": [...]}, ...],
        "canti": [{"posto": 2, "seme": "spade", "punti": 20}]}.
    """
    laid = game.last_hand.laid_down
    hands = []
    for seat in range(len(laid.hands)):
        cards = []
        for card in laid.hands[seat]:
            cards.append(card_details(card))
        hands.append({"posto": seat, "carte": cards})
    sings = []
    for done in laid.sings:
        sings.append({"posto": done.seat, "seme": done.suit.value, "punti": done.points})
    return {"mani": hands, "canti": sings}


# @dataclass(frozen=True): costruttore automatico e campi che non si cambiano più
# (vedi il commento in app/game/engine/cards.py)
@dataclass(frozen=True)
class Player:
    """Un giocatore seduto al tavolo: solo i dati da mostrare.

    In parole semplici:
        Player(user_id=7, username="Mario", avatar="gatto")
        avatar: facoltativo, None se non c'è (la CPU).
    """

    user_id: int
    username: str
    avatar: str | None = None

    # @classmethod: si chiama dalla classe (Player.of(...)); cls è la classe Player
    @classmethod
    def of(cls, user):
        """Da un Player o da un utente (User di app.models): se ne copiano solo i dati da mostrare.

        In parole semplici:
            Player.of(user)
            user: un Player (si restituisce così com'è) oppure un utente del database.
            La usano create_room e gli inviti, che ricevono utenti.
        """
        if isinstance(user, cls):
            return user
        return cls(user_id=user.id, username=user.username, avatar=user.avatar)


CPU_PLAYER = Player(user_id=0, username="CPU")  # P68: nessun utente vero ha id 0


class Room:
    """Una stanza di gioco: una partita, i suoi giocatori e i suoi timer.

    In parole semplici:
        room = Room("abc")
        room.start(giocatori, 300)        fa partire la partita
        room.play(seat, card)             gioca una carta
        room.view_for(seat)               la vista di un posto
        Tutto passa dal lucchetto room.lock: un evento alla volta.
    """

    def __init__(self, room_id):
        """Crea una stanza vuota, senza partita.

        In parole semplici:
            Room(room_id)
            room_id: il codice della stanza (è il game_id del contratto), dato da
            _new_id di room_manager.py.
        """
        self.id = room_id
        self.channel = room_channel(room_id)
        # RLock: un lucchetto "rientrante", che lo stesso thread può prendere più volte
        # (per esempio sing prende il lucchetto e chiama _apply, che lo usa di nuovo)
        self.lock = threading.RLock()
        self.members = set()  # user_id dei giocatori

        # Partita (P24): None finché start() non la fa partire
        self.players = ()  # Player per posto
        self.cpu_seats = frozenset()  # P68: posti giocati dalla CPU
        self.ratings = ()  # P88: per posto {"value", "provisional"}, o None (CPU, o letto fuori da Flask)
        self.rated = True
        self.game = None
        self.version = 0
        self.sids = {}  # posto -> connessione al tavolo (l'ultima scheda che ha fatto game:join, D14)
        self._rng = None
        self._turn_started = None
        self._all_seated = False  # P118: tutti i giocatori veri sono arrivati al tavolo almeno una volta

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

        # CPU (P68): timer della prossima mossa, memoria delle carte uscite (D43), rng suo
        self._cpu_timer = None
        self._cpu_memory = {}  # posto della CPU -> CpuMemory, fatta solo dalle sue viste
        self._cpu_rng = None

        # Frasi del tavolo (P55): posto -> ora (time.monotonic) dell'ultima frase; mai il testo
        self.phrase_times = {}

        # Consiglio al compagno (P92, D46): posto di chi lo riceve -> (posto di chi lo dà, carta).
        # Come le frasi non si salva; sparisce quando chi lo riceve gioca e a fine mano
        self._advice = {}

    # --- Lock e membri (P23) ---

    def run(self, action, *args, **kwargs):
        """Esegue `action` sotto il lock della stanza: un evento alla volta.

        In parole semplici:
            room.run(funzione, a, b)
            Prende il lucchetto, chiama funzione(a, b) e restituisce quello che lei
            restituisce. *args e **kwargs raccolgono i parametri (in ordine e con il
            nome) e li ripassano uguali: run serve per funzioni con parametri diversi.
            La usano i gestori di game_events.py.
        """
        with self.lock:
            return action(*args, **kwargs)

    def add_member(self, user_id):
        """Aggiunge un giocatore tra i membri (lo usano i test di P23)."""
        with self.lock:
            self.members.add(user_id)

    def remove_member(self, user_id):
        """Toglie un giocatore dai membri (lo usano i test di P23)."""
        with self.lock:
            self.members.discard(user_id)

    def has_member(self, user_id):
        """True se l'utente è un giocatore vero di questa stanza.

        In parole semplici:
            room.has_member(7)
            La usano room_manager.py (in che partita è un utente) e game_events.py
            (solo i giocatori entrano al tavolo).
        """
        with self.lock:
            return user_id in self.members

    # --- Partita (P24) ---

    def start(self, players, target_score, rated=True, rng=None, cpu_seats=(), ratings=None):
        """Mette i giocatori ai posti (nell'ordine dato) e fa partire la partita del motore.

        `cpu_seats` (P68): i posti giocati dalla CPU; i membri sono solo i giocatori veri.
        `ratings` (P88): per posto il rating da mostrare, letto da create_room; None = nessuno.

        In parole semplici:
            room.start(players, target_score)
            players:      i Player in ordine di posto. Arrivano da create_room.
            target_score: 150, 300 o 500.
            rated:        facoltativo (se manca True): la partita conta per il rating.
            rng:          facoltativo, il generatore di numeri a caso; se manca si usa
                          secrets.SystemRandom (non prevedibile). I test lo fissano.
            cpu_seats:    facoltativo, i posti della CPU, per esempio (1,).
            ratings:      facoltativo, il rating di ogni posto da mostrare al tavolo.
            Parte anche il primo turno, dopo la pausa della distribuzione (P118).
        """
        with self.lock:
            if rng is not None:
                self._rng = rng
            else:
                self._rng = secrets.SystemRandom()
            self.players = tuple(players)
            self.cpu_seats = frozenset(cpu_seats)
            # ratings: uno per posto; senza, None per tutti ((None,) * 2 = (None, None))
            if ratings is not None:
                self.ratings = tuple(ratings)
            else:
                self.ratings = (None,) * len(self.players)
            self.members = set(self.human_ids)
            self.rated = rated
            self.game = new_game(len(self.players), target_score, self._rng)
            self.version = 1
            self.turn_seconds = TURN_SECONDS
            self.reconnect_seconds = RECONNECT_SECONDS
            # _app: l'applicazione Flask vera (non il "segnaposto" current_app), per
            # salvare la partita anche da un timer, fuori da una richiesta (P26)
            if has_app_context():
                self._app = current_app._get_current_object()
            else:
                self._app = None
            self._started_at = utc_now()
            self._moves = []
            self._saved = False
            self._advice = {}
            # una memoria delle carte uscite per ogni posto della CPU (D43)
            self._cpu_memory = {}
            for seat in self.cpu_seats:
                self._cpu_memory[seat] = CpuMemory()
            self._cpu_rng = random.Random(self._rng.random())  # la CPU pensa fuori dal lock
            self._all_seated = False
            for seat in range(len(self.players)):
                if seat not in self.cpu_seats:
                    self._wait_for(seat)  # P138: chi non arriva al tavolo perde per abbandono
            self._start_turn(first_deal_pause(len(self.players)))
            self._cpu_see()  # dopo il turno (la vista ne ha il tempo); la CPU gioca solo con il lock

    # @property: si legge come un campo (room.human_ids, senza parentesi)
    @property
    def human_ids(self):
        """user_id dei giocatori veri, in ordine di posto (P68: senza la CPU).

        In parole semplici:
            room.human_ids
            Per esempio (7, 12) nel 1v1 tra due persone, (7,) contro la CPU.
        """
        ids = []
        for seat in range(len(self.players)):
            if seat not in self.cpu_seats:
                ids.append(self.players[seat].user_id)
        return tuple(ids)

    @property
    def finished(self):
        """Partita finita: per punteggio (motore) o per abbandono (stanza).

        In parole semplici:
            room.finished
            False anche se la partita non è ancora partita (game None).
        """
        if self.game is None:
            return False
        return self.game.finished or len(self.abandoned_seats) > 0

    def seat_of(self, user_id):
        """Il posto di un giocatore, oppure None.

        In parole semplici:
            room.seat_of(7)
            Il primo posto con quell'utente. Tutte le CPU hanno user_id 0: seat_of(0)
            trova solo la prima. La usa game_events.py.
        """
        for seat in range(len(self.players)):
            if self.players[seat].user_id == user_id:
                return seat
        return None

    def join(self, seat, sid):
        """Collega la scheda `sid` al posto; restituisce la connessione sostituita (D14) o None.

        Se il posto era scollegato, il rientro ferma il conto alla rovescia (P25).

        In parole semplici:
            room.join(seat, sid)
            seat: il posto del giocatore. sid: la scheda che ha mandato game:join.
            Arrivano da game_events.py. Restituisce il sid della scheda di prima, se
            era un'altra (game_events.py le dice che il tavolo è passato a una nuova).
        """
        with self.lock:
            old = self.sids.get(seat)
            self.sids[seat] = sid
            # pop: toglie il conto alla rovescia del posto, se c'era, e lo ferma
            waiting = self._reconnect.pop(seat, None)
            if waiting is not None:
                waiting[1].cancel()
            self._first_deal_for_everyone()
            if old != sid:
                self.version += 1
            if old is None or old == sid:
                return None
            return old

    def _first_deal_for_everyone(self):
        """P118: quando l'ultimo giocatore vero arriva al tavolo, se nessuno ha ancora fatto una
        mossa il primo turno riparte con la pausa della distribuzione: la pagina la mostra alla
        prima vista, e chi arriva dopo gli altri ha tutto il tempo del turno (sotto il lock).

        In parole semplici:
            _first_deal_for_everyone()
            La chiama join. Fa qualcosa una volta sola per partita (_all_seated).
        """
        if self._all_seated or self.game is None or self.finished:
            return
        # se un giocatore vero non è ancora al tavolo, si aspetta
        for seat in range(len(self.players)):
            if seat not in self.cpu_seats and seat not in self.sids:
                return
        self._all_seated = True
        if len(self._moves) == 0:
            self._start_turn(first_deal_pause(len(self.players)))

    def is_table_connection(self, seat, sid):
        """True se `sid` è la scheda al tavolo di quel posto (D14: conta solo l'ultima).

        In parole semplici:
            room.is_table_connection(seat, sid)
            La usa game_events.py: le mosse valgono solo dalla scheda al tavolo.
        """
        with self.lock:
            return self.sids.get(seat) == sid

    def play(self, seat, card: Card):
        """Gioca una carta (il motore controlla turno e regole); poi sale la version.

        In parole semplici:
            room.play(seat, card)
            Arrivano da game:play_card (game_events.py). Una mossa non valida lancia
            l'errore del motore e la partita non cambia.
        """
        with self.lock:
            self._apply(PlayCardAction(seat, card), "gioca_carta", card_details(card))

    def sing(self, seat, suit):
        """Canta un seme; restituisce l'evento game:sang da mostrare a tutti (D15).

        In parole semplici:
            room.sing(seat, suit)
            Arrivano da game:sing (game_events.py) o dalla CPU. Restituisce per esempio
            {"seat": 0, "suit": "coppe", "points": 40, "cards": [Re, Cavallo], "show_seconds": 3}.
        """
        with self.lock:
            # before: quanti canti c'erano; il canto nuovo sarà in quella posizione
            before = len(self.game.hand.sings)

            def sing_details(game):
                """Cosa si salva del canto: seme e punti, letti dalla partita dopo il canto.

                In parole semplici:
                    sing_details(game)
                    40 o 20 lo decide il motore: per questo i punti si leggono dal canto
                    appena fatto, e la funzione la chiama _apply dopo la mossa.
                """
                return {"seme": suit.value, "punti": game.hand.sings[before].points}

            self._apply(SingAction(seat, suit), "canta", sing_details)
            done = self.game.hand.sings[before]
            return {
                "seat": seat,
                "suit": done.suit.value,
                "points": done.points,
                "cards": [card_to_dict(Card(suit, Rank.KING)), card_to_dict(Card(suit, Rank.KNIGHT))],
                "show_seconds": SING_SHOW_SECONDS,
            }

    def lay_down(self, seat):
        """Cala le carte (P84): la mano finisce subito e si salvano le carte che restavano a tutti.

        In parole semplici:
            room.lay_down(seat)
            Arriva da game:lay_down (game_events.py) o dalla CPU.
        """
        with self.lock:
            self._apply(LayDownAction(seat), "cala_carte", _laid_down_details)

    def advise(self, seat, card):
        """Consiglio al compagno (P92, D46): una carta della sua mano, oppure None per toglierlo.

        Restituisce il posto del compagno e l'evento game:advice da mandargli. Si può dare in
        qualunque momento, purché le carte del compagno si vedano; non cambia la partita.

        In parole semplici:
            room.advise(seat, card)
            seat: chi consiglia. card: la carta del compagno consigliata, o None.
            Arrivano da game:advise (game_events.py). Restituisce una coppia (tupla di
            due elementi): (posto del compagno, {"seat": seat, "card": {...} o None}).
        """
        with self.lock:
            hand = self.game.hand
            if hand.num_players != 4:
                raise InvalidMoveError("Il consiglio al compagno c'è solo nel 2v2.")
            if self.finished or not partner_cards_visible(hand):
                raise InvalidMoveError("Le carte del compagno si vedono solo a mazzo finito, con la briscola.")
            partner = (seat + 2) % 4
            if partner in self.cpu_seats:
                raise InvalidMoveError("La CPU non riceve consigli.")  # P122, D49
            if card is None:
                self._advice.pop(partner, None)
            elif card not in hand.hands[partner]:
                raise InvalidMoveError("Il tuo compagno non ha questa carta.")
            else:
                self._advice[partner] = (seat, card)  # un consiglio alla volta: il nuovo prende il posto
            if card is None:
                shown = None
            else:
                shown = card_to_dict(card)
            return partner, {"seat": seat, "card": shown}

    def _apply(self, action, kind, details):
        """Applica la mossa del motore e la aggiunge all'elenco delle mosse (P26).

        `details` è il dizionario da salvare, oppure una funzione che lo ricava dalla
        partita dopo la mossa.

        In parole semplici:
            _apply(action, kind, details)
            action:  l'azione del motore (PlayCardAction, SingAction, LayDownAction).
            kind:    il tipo di mossa da salvare: "gioca_carta", "canta",
                     "mossa_automatica" o "cala_carte".
            details: i dati della mossa da salvare, o una funzione (vedi sopra).
            Poi: sale version, si aggiornano il consiglio e la memoria della CPU, e
            parte il turno nuovo o, a fine partita, il salvataggio.
        """
        before = self.game
        self.game = apply_game(self.game, action, self._rng)
        # callable: True se details è una funzione (si può "chiamare")
        if callable(details):
            details = details(self.game)
        self._moves.append(MoveRecord(hand=before.hand_number, seat=action.seat, kind=kind,
                                      details=details, at=utc_now()))
        self.version += 1
        if self.game.hand_number != before.hand_number or self.game.finished:
            self._advice.clear()  # mano finita: le carte del compagno non si vedono più
        elif isinstance(action, PlayCardAction):
            self._advice.pop(action.seat, None)  # ha giocato: il consiglio che aveva non serve più
        self._cpu_see()
        if self.game.finished:
            self._stop_timers()
            self._save()
        elif not isinstance(action, SingAction):
            # Dopo ogni carta è un turno nuovo, anche quando tocca di nuovo allo stesso posto
            # (chi chiude la presa e la vince apre la successiva): prima di P66 il timer
            # ripartiva solo se cambiava il posto di turno, e in quel caso non ripartiva più
            self._start_turn(table_pause(before, self.game))
        # Dopo un canto il turno resta a chi ha cantato: il suo tempo continua a scorrere

    # --- Timer del turno (P25, D12) ---

    def _start_turn(self, pause=0.0):
        """Nuovo turno: riparte il tempo e il timer della mossa automatica (sotto il lock).

        P94: il conto alla rovescia parte dopo `pause`, la pausa del tavolo che comincia con
        la mossa appena fatta (table_pause); fino ad allora nella vista il turno resta pieno.

        In parole semplici:
            _start_turn(pause)
            pause: facoltativo (se manca 0), i secondi della pausa del tavolo.
            Ferma il timer di prima, alza il numero del turno (_turn_token) e avvia un
            timer nuovo che, se nessuno gioca, chiama _turn_expired. Se tocca alla CPU,
            programma anche la sua mossa.
        """
        if self._turn_timer is not None:
            self._turn_timer.cancel()
        self._turn_token += 1
        self._turn_started = time.monotonic() + pause
        # Timer: dopo pausa + tempo del turno chiama self._turn_expired(numero del turno);
        # daemon = True: non impedisce al programma di chiudersi
        timer = threading.Timer(pause + self.turn_seconds, self._turn_expired, args=(self._turn_token,))
        timer.daemon = True
        self._turn_timer = timer
        timer.start()
        self._schedule_cpu(pause)

    def _turn_expired(self, token):
        """Il tempo del turno è scaduto: gioca la mossa automatica (la chiama il timer).

        In parole semplici:
            _turn_expired(token)
            token: il numero del turno di quando il timer è partito. Se adesso il numero
            è diverso, il giocatore ha già giocato e il timer non fa niente.
        """
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

    # --- CPU (P68, D43) ---

    def _schedule_cpu(self, pause=0.0):
        """Se tocca alla CPU, la sua mossa parte dopo la pausa del tavolo e la sua attesa (sotto il lock).

        In parole semplici:
            _schedule_cpu(pause)
            pause: facoltativo (se manca 0), la pausa del tavolo.
            L'attesa è CPU_SECONDS per un numero a caso tra CPU_JITTER[0] e
            CPU_JITTER[1] (uniform), così la CPU non gioca sempre con lo stesso ritmo.
        """
        if self._cpu_timer is not None:
            self._cpu_timer.cancel()
            self._cpu_timer = None
        hand = self.game.hand
        if self.finished or hand.turn_seat not in self.cpu_seats:
            return
        delay = pause + CPU_SECONDS * self._cpu_rng.uniform(CPU_JITTER[0], CPU_JITTER[1])
        timer = threading.Timer(delay, self._cpu_turn, args=(self._turn_token,))
        timer.daemon = True
        self._cpu_timer = timer
        timer.start()

    def _cpu_see(self):
        """Ogni vista nuova passa dalla memoria della CPU, come la vedrebbe lei (sotto il lock).

        In parole semplici:
            _cpu_see()
            Per ogni posto della CPU, la sua memoria (CpuMemory di cpu.py) guarda la
            vista di quel posto e si ricorda le carte uscite. Va chiamata a ogni
            cambiamento della partita (start e _apply), altrimenti la CPU gioca peggio.
        """
        for seat, memory in self._cpu_memory.items():
            memory.see(self.view_for(seat))

    def _cpu_turn(self, token):
        """La mossa della CPU (la chiama il timer di _schedule_cpu).

        In parole semplici:
            _cpu_turn(token)
            1. con il lucchetto: controlla il turno e copia vista, version e memoria;
            2. senza lucchetto: la CPU sceglie la mossa (cpu_move, fino a 0,3 s);
            3. di nuovo con il lucchetto: se nel frattempo è cambiato qualcosa ci ripensa,
               altrimenti gioca la mossa e manda le viste a tutti.
        """
        with self.lock:
            if token != self._turn_token or self.finished:
                return  # turno già passato (per esempio la mossa automatica), o partita finita
            seat = self.game.hand.turn_seat
            view = self.view_for(seat)
            version = self.version
            # una copia della memoria, da usare fuori dal lucchetto senza toccare l'originale
            memory = CpuMemory(self._cpu_memory[seat].hand_number, set(self._cpu_memory[seat].seen))
        # La CPU pensa fino a circa 0,3 s: fuori dal lock, così intanto la stanza risponde
        try:
            action = cpu_move(view, self._cpu_rng, memory)
        except Exception:
            log.exception("Mossa della CPU non riuscita nella stanza %s", self.id)
            return
        with self.lock:
            if token != self._turn_token or self.finished:
                return  # intanto il turno è passato (mossa automatica) o la partita è finita
            if version != self.version:
                # Stesso turno ma vista cambiata (per esempio l'avversario si è scollegato o è
                # rientrato): la mossa pensata non vale più, la CPU ci ripensa
                self._schedule_cpu()
                return
            try:
                if isinstance(action, SingAction):
                    socketio.emit("game:sang", self.sing(seat, action.suit), to=self.channel)
                    self._schedule_cpu()  # il turno resta alla CPU: ora la carta, dopo un'altra attesa
                elif isinstance(action, LayDownAction):
                    self.lay_down(seat)
                else:
                    self._apply(action, "gioca_carta", card_details(action.card))
            except Exception:
                log.exception("Mossa della CPU non riuscita nella stanza %s", self.id)
                return
            self.broadcast_states()

    def _stop_timers(self):
        """Ferma tutti i timer della stanza (fine partita, sotto il lock).

        In parole semplici:
            _stop_timers()
            Turno, CPU e conti alla rovescia per rientrare; alza anche il numero del
            turno, così un timer già partito non fa niente.
        """
        if self._turn_timer is not None:
            self._turn_timer.cancel()
            self._turn_timer = None
        if self._cpu_timer is not None:
            self._cpu_timer.cancel()
            self._cpu_timer = None
        self._turn_token += 1
        # ogni valore di _reconnect è una coppia (scadenza, timer): [1] è il timer
        for waiting in self._reconnect.values():
            waiting[1].cancel()
        self._reconnect.clear()

    # --- Scollegamento, rientro e abbandono (P25) ---

    def disconnect(self, sid):
        """La scheda `sid` si è scollegata. Se era quella al tavolo di un posto, il posto
        risulta scollegato e parte il conto alla rovescia per rientrare; restituisce il
        posto, oppure None se `sid` non era al tavolo.

        In parole semplici:
            room.disconnect(sid)
            sid: la scheda che si è scollegata. Arriva da connection_events.py.
        """
        with self.lock:
            # seat: il primo posto che ha questa scheda al tavolo (ricerca lineare)
            seat = None
            for other_seat, table_sid in self.sids.items():
                if table_sid == sid:
                    seat = other_seat
                    break
            if seat is None:
                return None
            del self.sids[seat]
            self.version += 1
            if not self.finished:
                self._wait_for(seat)
            return seat

    def _wait_for(self, seat):
        """Conto alla rovescia per arrivare o rientrare al tavolo (sotto il lock); game:join lo ferma.

        In parole semplici:
            _wait_for(seat)
            Dopo reconnect_seconds (60 s) chiama _reconnect_expired; la scadenza si
            ricorda in _reconnect, per mostrare i secondi che restano nella vista.
        """
        deadline = time.monotonic() + self.reconnect_seconds
        timer = threading.Timer(self.reconnect_seconds, self._reconnect_expired, args=(seat, deadline))
        timer.daemon = True
        self._reconnect[seat] = (deadline, timer)
        timer.start()

    def _reconnect_expired(self, seat, deadline):
        """Il tempo per arrivare o rientrare è finito: partita persa per abbandono (la chiama il timer).

        In parole semplici:
            _reconnect_expired(seat, deadline)
            deadline: la scadenza di quando il timer è partito. Se adesso in _reconnect
            c'è un'altra scadenza (o nessuna), il giocatore è rientrato e non succede niente.
        """
        with self.lock:
            waiting = self._reconnect.get(seat)
            if waiting is None or waiting[0] != deadline or self.finished:
                return  # è arrivato o rientrato in tempo, o la partita è già finita
            log.info("Posto %s non arrivato o non rientrato in tempo nella stanza %s: abbandono", seat, self.id)
            if self.abandon(seat, "tempo_scaduto"):
                self.broadcast_states()

    def abandon(self, seat, reason="esci"):
        """La partita è persa per abbandono di `seat`: `reason` è "esci" (game:leave) o
        "tempo_scaduto" (non rientrato in tempo).

        Restituisce False se la partita era già finita (in quel caso non cambia niente).

        In parole semplici:
            room.abandon(seat, reason)
            Arriva da game:leave (game_events.py) o da _reconnect_expired. Segna chi ha
            abbandonato, aggiunge la mossa "abbandono", ferma i timer e salva.
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
        """Salva la partita finita, una volta sola (sotto il lock). Un errore va nel log.

        In parole semplici:
            _save()
            Avvisa finish_listeners (home e amici), poi salva con match_service.save_match
            dentro l'applicazione Flask. Non salva la partita contro la CPU (D43) né una
            stanza creata fuori da Flask (lo scrive nel log).
        """
        if self._saved:
            return
        self._saved = True
        notify(finish_listeners, self.human_ids, self._app)
        if len(self.cpu_seats) > 0:
            log.info("Partita contro la CPU nella stanza %s: non si salva (D43)", self.id)
            return
        if self._app is None:
            log.warning("Partita della stanza %s non salvata: nessuna applicazione Flask", self.id)
            return
        try:
            # app_context: "entra" nell'applicazione Flask, così il database funziona
            # anche dentro un timer
            with self._app.app_context():
                match_service.save_match(self._match_record())
        except Exception:
            log.exception("Salvataggio della partita della stanza %s non riuscito", self.id)

    def _match_record(self):
        """La partita nella forma che salva match_service (MatchRecord).

        In parole semplici:
            _match_record()
            Motivo della fine ("abbandono" o "punteggio"), squadra vincitrice, punteggi,
            giocatori e mosse. Con un abbandono vince l'altra squadra: 1 - (posto % 2).
        """
        if len(self.abandoned_seats) > 0:
            reason = "abbandono"
            winner = 1 - self.abandoned_seats[0] % 2
        else:
            reason = "punteggio"
            winner = self.game.result.winner_team
        players = []
        for seat in range(len(self.players)):
            players.append(PlayerRecord(seat=seat, user_id=self.players[seat].user_id,
                                        abandoned=seat in self.abandoned_seats))
        return MatchRecord(
            mode=MODE_OF_PLAYERS[len(self.players)],
            target_score=self.game.target_score,
            rated=self.rated,
            started_at=self._started_at,
            ended_at=utc_now(),
            reason=reason,
            winner_team=winner,
            scores=tuple(self.game.scores),
            players=tuple(players),
            moves=tuple(self._moves),
        )

    def _abandon_result(self, scores):
        """Il campo result della vista dopo un abbandono (reason "abandon").

        In parole semplici:
            _abandon_result(scores)
            scores: i punteggi già nella forma della vista. Per esempio
            {"reason": "abandon", "winner_team": 1, "abandoned_seats": [0], "scores": [...]}.
        """
        losing_team = self.abandoned_seats[0] % 2  # la squadra di un posto è posto % 2 (nel 1v1 = il posto)
        return {
            "reason": "abandon",
            "winner_team": 1 - losing_team,
            "abandoned_seats": list(self.abandoned_seats),
            "scores": scores,
        }

    # --- Viste ---

    def view_for(self, seat):
        """La vista del contratto (3.3) per quel posto: quella del motore più i campi della stanza.

        In parole semplici:
            room.view_for(seat)
            Parte da player_view del motore e aggiunge: in cima game_id, version e
            rated; il consiglio (nel 2v2); la fine per abbandono; per ogni giocatore
            nome, avatar, rating, CPU, collegato e secondi per rientrare; per il turno
            i secondi totali e quelli che restano.
        """
        with self.lock:
            engine_view = player_view(self.game, seat)
            # view: prima i campi della stanza, poi tutti quelli del motore, nello stesso ordine
            view = {"game_id": self.id, "version": self.version, "rated": self.rated}
            for key, value in engine_view.items():
                view[key] = value

            if len(self.players) == 4:
                # given: il consiglio ricevuto, una coppia (posto di chi lo dà, carta), o None
                given = self._advice.get(seat)
                if given is None:
                    view["advice"] = None
                else:
                    view["advice"] = {"seat": given[0], "card": card_to_dict(given[1])}

            if len(self.abandoned_seats) > 0 and not self.game.finished:
                # Il motore non sa dell'abbandono: la vista si corregge qui
                view["status"] = "finished"
                view["turn"] = None
                view["legal"] = {"play": [], "sing": [], "lay_down": False}
                view["result"] = self._abandon_result(view["scores"])
                if "partner_hand" in view:
                    view["partner_hand"] = None  # partita finita: le carte del compagno non si vedono più

            now = time.monotonic()
            for entry in view["players"]:
                seat_of_entry = entry["seat"]
                player = self.players[seat_of_entry]
                waiting = self._reconnect.get(seat_of_entry)
                # reconnect_seconds_left: i secondi per rientrare (mai meno di 0), o None
                if waiting is None:
                    seconds_left = None
                else:
                    seconds_left = round(max(0.0, waiting[0] - now), 1)
                entry["user_id"] = player.user_id
                entry["username"] = player.username
                entry["avatar"] = player.avatar
                entry["rating"] = self.ratings[seat_of_entry]
                entry["cpu"] = seat_of_entry in self.cpu_seats  # D43: la pagina riconosce la CPU da qui
                entry["connected"] = seat_of_entry in self.sids or seat_of_entry in self.cpu_seats
                entry["reconnect_seconds_left"] = seconds_left

            if view["turn"] is not None:
                # P94: durante la pausa del tavolo il turno resta pieno (elapsed negativo)
                elapsed = max(0.0, now - self._turn_started)
                view["turn"]["seconds_total"] = self.turn_seconds
                view["turn"]["seconds_left"] = round(max(0.0, self.turn_seconds - elapsed), 1)
            return view

    def send_state(self, seat):
        """Manda a un posto la sua vista, sulla sua connessione al tavolo (se c'è).

        In parole semplici:
            room.send_state(seat)
            Manda game:state solo alla scheda al tavolo di quel posto (to=sid).
        """
        with self.lock:
            sid = self.sids.get(seat)
            if sid is not None:
                socketio.emit("game:state", self.view_for(seat), to=sid)

    def broadcast_states(self):
        """Ogni giocatore collegato riceve la propria vista: mai quella degli altri.

        In parole semplici:
            room.broadcast_states()
            Chiama send_state per ogni posto; ogni vista è diversa (P15).
        """
        with self.lock:
            for seat in range(len(self.players)):
                self.send_state(seat)
