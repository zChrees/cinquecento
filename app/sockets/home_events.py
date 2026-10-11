"""Stato della home (P44, contratto 5.1): home:status {"online_count", "resume"}.

- La pagina non manda eventi: home:status parte sempre dal server.
- Lo riceve ogni scheda appena si collega (connection_events.py) e poi a ogni
  cambiamento: quando un utente entra online o esce (tutti gli utenti collegati) e
  quando una partita finisce (i suoi giocatori: l'avviso di rientro sparisce).
- `resume` è la partita in corso dell'utente (find_room_of_user, P24) oppure null.
Nei log solo numeri di utente.
"""

from app.extensions import socketio
from app.realtime import room as room_module
from app.realtime.events import user_channel
from app.realtime.presence import presence
from app.realtime.room import MODE_OF_PLAYERS
from app.realtime.room_manager import find_room_of_user


def home_status(user_id):
    room = find_room_of_user(user_id)
    resume = None
    if room is not None:
        resume = {
            "game_id": room.id,
            "url": f"/game/{room.id}",
            "mode": MODE_OF_PLAYERS[len(room.players)],
            "target_score": room.game.target_score,
        }
    return {"online_count": presence.count(), "resume": resume}


def send_status(user_ids):
    """home:status a tutte le schede di quegli utenti."""
    for user_id in user_ids:
        socketio.emit("home:status", home_status(user_id), to=user_channel(user_id))


def broadcast_status(exclude=None):
    """home:status a tutti gli utenti collegati (è cambiato il numero di utenti online)."""
    send_status(u for u in presence.online_users() if u != exclude)


def _game_finished(user_ids, _app):
    send_status(user_ids)


def register(socketio):
    """Nessun evento dalla pagina; a fine partita i giocatori ricevono lo stato nuovo."""
    if _game_finished not in room_module.finish_listeners:
        room_module.finish_listeners.append(_game_finished)
