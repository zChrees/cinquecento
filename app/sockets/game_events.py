"""Eventi del tavolo (P24, contratto 3.2): game:join, game:play_card, game:sing, game:lay_down.

- Tutto quello che arriva dalla pagina si controlla qui (tipi e valori ammessi):
  un dato non valido si rifiuta con `invalid_data`, senza correzioni.
- Ogni evento di una stanza si elabora sotto il lock della stanza (room.run).
- `version`: una mossa decisa su una vista vecchia riceve `stale_state` e la vista attuale.
- D14: l'ultima scheda che fa game:join prende il posto; quella di prima riceve
  game:replaced e le sue mosse sono rifiutate (`not_allowed`).
- Dopo ogni cambiamento ogni giocatore riceve la propria vista (game:state).
- P25: game:leave = abbandono immediato (nel 2v2 perde la squadra, D13); a partita
  finita (per punteggio o per abbandono) le mosse si rifiutano. Il timer del turno e
  il rientro entro RECONNECT_SECONDS stanno in room.py; lo scollegamento arriva da
  connection_events.py.
- P92: game:advise, il consiglio al compagno nel 2v2 (D46): arriva solo a lui (game:advice),
  non si salva, non cambia la partita (niente `version`) e ha il limite di frequenza di ogni
  evento (P32).
- P55: game:send_phrase manda una frase pronta (D24) a tutti al tavolo (game:phrase);
  l'elenco arriva a chi entra con game:phrases. Si possono mandare anche a partita
  finita ("Bella partita!"). Codice e testo non vanno mai nel log.

Cosa contiene:
    on_join, on_play_card, on_sing, on_lay_down, on_advise, on_leave, on_send_phrase
                         un gestore per ogni evento del tavolo
    _game_id, _version, _suit, _card, _table, _check_move
                         i controlli dei dati e del posto, comuni ai gestori
    register(socketio)   registra i gestori

Ogni gestore fa i controlli che non toccano la partita, poi definisce una funzione
interna con il lavoro vero e la passa a room.run, che la esegue sotto il lucchetto
della stanza.

DA DOVE ARRIVANO I DATI: dal tavolo React (frontend/src/game/tableStore.ts), che manda
un dizionario con game_id e, a seconda dell'evento, version, card {"suit", "rank"},
suit o code.
"""

from flask import request
from flask_login import current_user
from flask_socketio import join_room, leave_room

from app.extensions import socketio
from app.game.engine.cards import Card, Rank, Suit
from app.game.engine.errors import InvalidMoveError, NotYourTurnError
from app.realtime import table_phrases
from app.realtime.events import EventError, handler
from app.realtime.room_manager import rooms

# SUITS e RANKS: dal valore mandato dalla pagina al seme o al valore del motore,
# per esempio SUITS["coppe"] = Suit.COPPE e RANKS[10] = Rank.KING
SUITS = {}
for _suit in Suit:
    SUITS[_suit.value] = _suit
RANKS = {}
for _rank in Rank:
    RANKS[_rank.value] = _rank
GAME_ID_MAX = 64


def _is_int(value):
    """True se `value` è un intero vero (True e False, che in Python sono anche numeri, no)."""
    return isinstance(value, int) and not isinstance(value, bool)


def _game_id(data):
    """Il codice della partita mandato dalla pagina, controllato.

    In parole semplici:
        _game_id(data)
        data deve essere un dizionario con "game_id" testo da 1 a GAME_ID_MAX caratteri;
        altrimenti invalid_data.
    """
    if not isinstance(data, dict):
        raise EventError("invalid_data", "Richiesta non valida.")
    game_id = data.get("game_id")
    if not isinstance(game_id, str) or len(game_id) == 0 or len(game_id) > GAME_ID_MAX:
        raise EventError("invalid_data", "Partita non valida.")
    return game_id


def _version(data):
    """Il numero della vista su cui la pagina ha deciso la mossa (un intero da 1 in su)."""
    version = data.get("version")
    if not _is_int(version) or version < 1:
        raise EventError("invalid_data", "Versione della partita non valida.")
    return version


def _suit(value):
    """Il seme del motore dal testo mandato dalla pagina, per esempio "coppe" → Suit.COPPE."""
    if not isinstance(value, str) or value not in SUITS:
        raise EventError("invalid_data", "Seme non valido.")
    return SUITS[value]


def _card(data):
    """Carta dalla forma del contratto {"suit", "rank"}; qualunque altra forma si rifiuta.

    In parole semplici:
        _card(data)
        data["card"] deve essere un dizionario con esattamente le chiavi "suit" e
        "rank" (set(card) è l'insieme delle sue chiavi), per esempio
        {"suit": "coppe", "rank": 1}. Restituisce Card(Suit.COPPE, Rank.ACE).
    """
    card = data.get("card")
    if not isinstance(card, dict) or set(card) != {"suit", "rank"}:
        raise EventError("invalid_data", "Carta non valida.")
    rank = card["rank"]
    if not _is_int(rank) or rank not in RANKS:
        raise EventError("invalid_data", "Carta non valida.")
    return Card(_suit(card["suit"]), RANKS[rank])


def _table(data):
    """La stanza e il posto dell'utente; errore se la partita non c'è o se lui non è seduto lì.

    In parole semplici:
        _table(data)
        Restituisce una coppia (room, seat), per esempio (stanza, 1).
    """
    room = rooms.get(_game_id(data))
    if room is None or room.game is None:
        raise EventError("not_found", "Questa partita non esiste o è già finita.")
    seat = room.seat_of(current_user.id)
    if seat is None:
        raise EventError("not_allowed", "Non sei seduto a questo tavolo.")
    return room, seat


def _check_move(room, seat, version):
    """Controlli comuni alle mosse, sotto il lock della stanza.

    In parole semplici:
        _check_move(room, seat, version)
        1. la mossa deve arrivare dalla scheda al tavolo (D14);
        2. la partita non deve essere finita;
        3. la pagina deve aver visto l'ultima vista: se no riceve la vista attuale e
           la mossa si rifiuta con stale_state.
    """
    if not room.is_table_connection(seat, request.sid):
        raise EventError("not_allowed", "La partita è aperta in un'altra scheda.")
    if room.finished:
        raise EventError("not_allowed", "La partita è finita.")
    if version != room.version:
        room.send_state(seat)
        raise EventError("stale_state")


def _engine_errors(move):
    """Esegue `move` e trasforma gli errori del motore in errori del contratto.

    In parole semplici:
        _engine_errors(move)
        move: una funzione senza parametri che fa la mossa nella stanza.
        NotYourTurnError diventa not_your_turn, InvalidMoveError illegal_move con il
        messaggio del motore. "from None": l'errore nuovo non si porta dietro quello vecchio.
    """
    try:
        move()
    except NotYourTurnError:
        raise EventError("not_your_turn") from None
    except InvalidMoveError as exc:
        raise EventError("illegal_move", str(exc)) from None


# @handler (app/realtime/events.py): controlla login e limite di frequenza e
# trasforma quello che il gestore restituisce nella risposta del contratto
@handler
def on_join(data=None):
    """game:join: la scheda si siede al tavolo (o ci torna).

    In parole semplici:
        data: {"game_id": "abc"}.
        La scheda entra nel canale della stanza; se prima al tavolo c'era un'altra
        scheda, quella riceve game:replaced ed esce dal canale (D14). Poi la scheda
        riceve l'elenco delle frasi e tutti la vista nuova.
    """
    table = _table(data)
    room = table[0]
    seat = table[1]
    sid = request.sid

    def join():
        """Il lavoro vero, sotto il lucchetto della stanza."""
        replaced = room.join(seat, sid)
        join_room(room.channel)
        if replaced is not None:
            socketio.emit("game:replaced", {"game_id": room.id}, to=replaced)
            leave_room(room.channel, sid=replaced)
        socketio.emit("game:phrases", table_phrases.phrases_event(), to=sid)  # prima della vista (contratto 3.2)
        room.broadcast_states()

    room.run(join)


@handler
def on_play_card(data=None):
    """game:play_card: gioca una carta.

    In parole semplici:
        data: {"game_id": "abc", "version": 12, "card": {"suit": "coppe", "rank": 1}}.
    """
    table = _table(data)
    room = table[0]
    seat = table[1]
    version = _version(data)
    card = _card(data)

    def play():
        """Il lavoro vero, sotto il lucchetto della stanza."""
        _check_move(room, seat, version)

        def move():
            """La mossa, che _engine_errors esegue trasformando gli errori del motore."""
            room.play(seat, card)

        _engine_errors(move)
        room.broadcast_states()

    room.run(play)


@handler
def on_sing(data=None):
    """game:sing: canta un seme.

    In parole semplici:
        data: {"game_id": "abc", "version": 12, "suit": "coppe"}.
        Tutti al tavolo ricevono game:sang (per mostrare Re e Cavallo), poi la vista.
    """
    table = _table(data)
    room = table[0]
    seat = table[1]
    version = _version(data)
    suit = _suit(data.get("suit"))

    def sing():
        """Il lavoro vero, sotto il lucchetto della stanza."""
        _check_move(room, seat, version)
        # sang: si riempie con l'evento game:sang restituito da room.sing
        sang = {}

        def move():
            """La mossa, che _engine_errors esegue trasformando gli errori del motore."""
            sang.update(room.sing(seat, suit))

        _engine_errors(move)
        socketio.emit("game:sang", sang, to=room.channel)
        room.broadcast_states()

    room.run(sing)


@handler
def on_lay_down(data=None):
    """Cala le carte (P84): se il motore lo ammette la mano finisce e tutti vedono le carte calate.

    In parole semplici:
        data: {"game_id": "abc", "version": 12}.
    """
    table = _table(data)
    room = table[0]
    seat = table[1]
    version = _version(data)

    def lay_down():
        """Il lavoro vero, sotto il lucchetto della stanza."""
        _check_move(room, seat, version)

        def move():
            """La mossa, che _engine_errors esegue trasformando gli errori del motore."""
            room.lay_down(seat)

        _engine_errors(move)
        room.broadcast_states()

    room.run(lay_down)


@handler
def on_advise(data=None):
    """Consiglio al compagno (P92): `card` è una carta della sua mano, oppure null per toglierlo.

    In parole semplici:
        data: {"game_id": "abc", "card": {"suit": "spade", "rank": 3}} oppure "card": null.
        Il consiglio arriva solo alla scheda al tavolo del compagno (game:advice).
    """
    table = _table(data)
    room = table[0]
    seat = table[1]
    if "card" not in data:
        raise EventError("invalid_data", "Carta non valida.")
    if data["card"] is None:
        card = None
    else:
        card = _card(data)
    sid = request.sid

    def advise():
        """Il lavoro vero, sotto il lucchetto della stanza."""
        if not room.is_table_connection(seat, sid):
            raise EventError("not_allowed", "La partita è aperta in un'altra scheda.")
        # given: si riempie con la coppia (posto del compagno, evento) restituita da room.advise
        given = []

        def move():
            """Il consiglio, che _engine_errors esegue trasformando gli errori del motore."""
            given.append(room.advise(seat, card))

        _engine_errors(move)
        partner = given[0][0]
        event = given[0][1]
        partner_sid = room.sids.get(partner)
        if partner_sid is not None:
            socketio.emit("game:advice", event, to=partner_sid)

    room.run(advise)


@handler
def on_leave(data=None):
    """ "Esci" dal tavolo, dopo la conferma nella pagina: la partita è persa per abbandono.

    A partita già finita risponde ok senza cambiare niente.

    In parole semplici:
        data: {"game_id": "abc"}. Vale solo dalla scheda al tavolo.
    """
    table = _table(data)
    room = table[0]
    seat = table[1]
    sid = request.sid

    def leave():
        """Il lavoro vero, sotto il lucchetto della stanza."""
        if not room.is_table_connection(seat, sid):
            raise EventError("not_allowed", "La partita è aperta in un'altra scheda.")
        if room.abandon(seat):
            room.broadcast_states()

    room.run(leave)


@handler
def on_send_phrase(data=None):
    """Frase pronta (D24): a tutti i giocatori del tavolo, al massimo una ogni 3 secondi. Non si salva.

    In parole semplici:
        data: {"game_id": "abc", "code": "ciao"}. Tutti al tavolo ricevono
        game:phrase {"seat": 0, "code": "ciao"}: il testo lo trova la pagina dall'elenco.
    """
    table = _table(data)
    room = table[0]
    seat = table[1]
    code = table_phrases.check_code(data.get("code"))
    sid = request.sid

    def send():
        """Il lavoro vero, sotto il lucchetto della stanza."""
        if not room.is_table_connection(seat, sid):
            raise EventError("not_allowed", "Siediti al tavolo per mandare una frase.")
        table_phrases.take_turn(room, seat)
        socketio.emit("game:phrase", {"seat": seat, "code": code}, to=room.channel)

    room.run(send)


def register(socketio):
    """Registra i gestori degli eventi del tavolo."""
    socketio.on_event("game:join", on_join)
    socketio.on_event("game:play_card", on_play_card)
    socketio.on_event("game:sing", on_sing)
    socketio.on_event("game:lay_down", on_lay_down)
    socketio.on_event("game:advise", on_advise)
    socketio.on_event("game:leave", on_leave)
    socketio.on_event("game:send_phrase", on_send_phrase)
