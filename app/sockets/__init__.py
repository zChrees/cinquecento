"""Ingressi in tempo reale: registra i gestori degli eventi di ogni modulo."""

from app.sockets import (
    chat_events,
    connection_events,
    friends_events,
    game_events,
    lobby_events,
)

MODULES = (connection_events, lobby_events, game_events, friends_events, chat_events)


def register_handlers(socketio):
    """Chiamata da create_app(): ogni modulo registra i propri eventi."""
    for module in MODULES:
        module.register(socketio)
