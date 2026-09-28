"""Tabelle del database viste da Python (P5).

Le tabelle le crea solo migrations/001_init.sql (con scripts/migrate.py): i
modelli le descrivono e basta, mai db.create_all(). versione_schema non ha un
modello: la usa solo migrate.py.
"""

from app.models.chat_message import ChatMessage
from app.models.friendship import Block, Friendship
from app.models.match import Match, MatchMove, MatchPlayer
from app.models.rating import Rating
from app.models.user import User

__all__ = ["Block", "ChatMessage", "Friendship", "Match", "MatchMove", "MatchPlayer", "Rating", "User"]
