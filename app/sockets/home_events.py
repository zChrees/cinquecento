"""Stato della home (P44, contratto 5.1): home:status {"online_count", "resume"}.

- home:status parte dal server. La home può anche chiederlo con home:refresh,
  quando compare con il collegamento già aperto (tornando dal tavolo senza ricaricare): la risposta porta lo stato.
- Lo riceve ogni scheda appena si collega (connection_events.py) e poi a ogni
  cambiamento: quando un utente entra online o esce (tutti gli utenti collegati) e
  quando una partita finisce (i suoi giocatori: l'avviso di rientro sparisce).
- `resume` è la partita in corso dell'utente (find_room_of_user, P24) oppure null.
Nei log solo numeri di utente.

Cosa contiene:
    home_status(user_id)        lo stato della home di un utente
    send_status(user_ids)       home:status a quegli utenti
    broadcast_status(exclude)   home:status a tutti gli utenti collegati
    on_refresh(data)            home:refresh, lo stato nella risposta
    register(socketio)          registra home:refresh e l'avviso di fine partita

DA DOVE ARRIVANO I DATI: connection_events.py chiama home_status e broadcast_status al
collegamento e allo scollegamento; la stanza chiama _game_finished a fine partita
(finish_listeners di room.py); la home React manda home:refresh.
"""

from flask_login import current_user

from app.extensions import socketio
from app.realtime import room as room_module
from app.realtime.events import handler, user_channel
from app.realtime.presence import presence
from app.realtime.room import MODE_OF_PLAYERS
from app.realtime.room_manager import find_room_of_user


def home_status(user_id):
    """Lo stato della home di un utente.

    In parole semplici:
        home_status(7)
        Restituisce per esempio {"online_count": 3, "resume": {"game_id": "abc",
        "url": "/game/abc", "mode": "1v1", "target_score": 300}}; resume è None se
        l'utente non ha una partita in corso.
    """
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
    """home:status a tutte le schede di quegli utenti.

    In parole semplici:
        send_status([7, 12])
        Ognuno riceve il suo stato (resume è diverso per ognuno).
    """
    for user_id in user_ids:
        socketio.emit("home:status", home_status(user_id), to=user_channel(user_id))


def broadcast_status(exclude=None):
    """home:status a tutti gli utenti collegati (è cambiato il numero di utenti online).

    In parole semplici:
        broadcast_status(exclude)
        exclude: facoltativo, un utente da saltare (chi si è appena collegato, che
        riceve già il suo home:status da on_connect).
    """
    user_ids = []
    for user_id in presence.online_users():
        if user_id != exclude:
            user_ids.append(user_id)
    send_status(user_ids)


def _game_finished(user_ids, _app):
    """A fine partita i giocatori ricevono lo stato nuovo (l'avviso di rientro sparisce).

    In parole semplici:
        _game_finished(user_ids, _app)
        La chiama la stanza (finish_listeners). _app non serve qui: il trattino basso
        davanti dice che il parametro c'è solo perché tutti gli avvisi lo ricevono.
    """
    send_status(user_ids)


# @handler (app/realtime/events.py): controlla login e limite di frequenza e
# trasforma quello che il gestore restituisce nella risposta del contratto
@handler
def on_refresh(data=None):
    """home:refresh: lo stato della home di chi lo chiede, nella risposta.

    In parole semplici:
        La pagina manda home:refresh (senza dati: quelli che arrivano non si usano,
        come per queue:leave) e riceve {"ok": true, "data": {"online_count",
        "resume"}}, gli stessi dati di home:status. Login e limite di frequenza li
        controlla @handler, come per ogni evento.
    """
    return home_status(current_user.id)


def register(socketio):
    """home:refresh dalla pagina; a fine partita i giocatori ricevono lo stato nuovo.

    In parole semplici:
        register(socketio)
        _game_finished si aggiunge a finish_listeners una volta sola (se create_app
        si chiama più volte, come nei test, non si raddoppia).
    """
    socketio.on_event("home:refresh", on_refresh)
    if _game_finished not in room_module.finish_listeners:
        room_module.finish_listeners.append(_game_finished)
