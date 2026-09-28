"""Eventi del tavolo (P24, contratto 3.2): game:join, game:play_card, game:sing.

- Tutto quello che arriva dalla pagina si controlla qui (tipi e valori ammessi):
  un dato non valido si rifiuta con `invalid_data`, senza correzioni.
- Ogni evento di una stanza si elabora sotto il lock della stanza (room.run).
- `version`: una mossa decisa su una vista vecchia riceve `stale_state` e la vista attuale.
- D14: l'ultima scheda che fa game:join prende il posto; quella di prima riceve
  game:replaced e le sue mosse sono rifiutate (`not_allowed`).
- Dopo ogni cambiamento ogni giocatore riceve la propria vista (game:state).
Timer, riconnessione, abbandono (game:leave): P25. Frasi del tavolo: P55.
"""

from flask import request
from flask_login import current_user
from flask_socketio import join_room, leave_room

from app.extensions import socketio
from app.game.engine.cards import Card, Rank, Suit
from app.game.engine.errors import InvalidMoveError, NotYourTurnError
from app.realtime.events import EventError, handler
from app.realtime.room_manager import rooms

SUITS = {suit.value: suit for suit in Suit}
RANKS = {rank.value: rank for rank in Rank}
GAME_ID_MAX = 64


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _game_id(data):
    if not isinstance(data, dict):
        raise EventError("invalid_data", "Richiesta non valida.")
    game_id = data.get("game_id")
    if not isinstance(game_id, str) or not 0 < len(game_id) <= GAME_ID_MAX:
        raise EventError("invalid_data", "Partita non valida.")
    return game_id


def _version(data):
    version = data.get("version")
    if not _is_int(version) or version < 1:
        raise EventError("invalid_data", "Versione della partita non valida.")
    return version


def _suit(value):
    if not isinstance(value, str) or value not in SUITS:
        raise EventError("invalid_data", "Seme non valido.")
    return SUITS[value]


def _card(data):
    """Carta dalla forma del contratto {"suit", "rank"}; qualunque altra forma si rifiuta."""
    card = data.get("card")
    if not isinstance(card, dict) or set(card) != {"suit", "rank"}:
        raise EventError("invalid_data", "Carta non valida.")
    rank = card["rank"]
    if not _is_int(rank) or rank not in RANKS:
        raise EventError("invalid_data", "Carta non valida.")
    return Card(_suit(card["suit"]), RANKS[rank])


def _table(data):
    """La stanza e il posto dell'utente; errore se la partita non c'è o se lui non è seduto lì."""
    room = rooms.get(_game_id(data))
    if room is None or room.game is None:
        raise EventError("not_found", "Questa partita non esiste o è già finita.")
    seat = room.seat_of(current_user.id)
    if seat is None:
        raise EventError("not_allowed", "Non sei seduto a questo tavolo.")
    return room, seat


def _check_move(room, seat, version):
    """Controlli comuni alle mosse, sotto il lock della stanza."""
    if not room.is_table_connection(seat, request.sid):
        raise EventError("not_allowed", "La partita è aperta in un'altra scheda.")
    if version != room.version:
        room.send_state(seat)
        raise EventError("stale_state")


def _engine_errors(move):
    try:
        move()
    except NotYourTurnError:
        raise EventError("not_your_turn") from None
    except InvalidMoveError as exc:
        raise EventError("illegal_move", str(exc)) from None


@handler
def on_join(data):
    room, seat = _table(data)
    sid = request.sid

    def join():
        replaced = room.join(seat, sid)
        join_room(room.channel)
        if replaced is not None:
            socketio.emit("game:replaced", {"game_id": room.id}, to=replaced)
            leave_room(room.channel, sid=replaced)
        room.broadcast_states()

    room.run(join)


@handler
def on_play_card(data):
    room, seat = _table(data)
    version, card = _version(data), _card(data)

    def play():
        _check_move(room, seat, version)
        _engine_errors(lambda: room.play(seat, card))
        room.broadcast_states()

    room.run(play)


@handler
def on_sing(data):
    room, seat = _table(data)
    version, suit = _version(data), _suit(data.get("suit"))

    def sing():
        _check_move(room, seat, version)
        sang = {}
        _engine_errors(lambda: sang.update(room.sing(seat, suit)))
        socketio.emit("game:sang", sang, to=room.channel)
        room.broadcast_states()

    room.run(sing)


def register(socketio):
    socketio.on_event("game:join", on_join)
    socketio.on_event("game:play_card", on_play_card)
    socketio.on_event("game:sing", on_sing)
