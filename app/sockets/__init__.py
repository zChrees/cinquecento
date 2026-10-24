"""Ingressi in tempo reale: registra i gestori degli eventi di ogni modulo.

Cosa contiene:
    MODULES                      i file di app/sockets/ con dei gestori di eventi
    register_handlers(socketio)  chiede a ognuno di loro di registrare i suoi eventi

Un "gestore" è la funzione che il server chiama quando arriva un certo evento dalla
pagina (per esempio on_play_card per game:play_card). "Registrarlo" vuol dire dire a
Socket.IO: quando arriva questo evento, chiama questa funzione.

DA DOVE ARRIVANO I DATI: create_app (app/__init__.py) chiama register_handlers una
volta, all'avvio del server.
"""

from app.sockets import (
    chat_events,
    connection_events,
    friends_events,
    game_events,
    home_events,
    lobby_events,
)

MODULES = (connection_events, lobby_events, game_events, home_events, friends_events, chat_events)


def register_handlers(socketio):
    """Chiamata da create_app(): ogni modulo registra i propri eventi.

    In parole semplici:
        register_handlers(socketio)
        socketio: l'oggetto di Flask-SocketIO (app/extensions.py). Per ogni modulo di
        MODULES chiama la sua funzione register, che fa socketio.on_event(nome, gestore).
    """
    for module in MODULES:
        module.register(socketio)
