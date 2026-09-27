"""Azioni che un giocatore può fare nel suo turno (P13): cantare un seme o giocare una carta."""

from dataclasses import dataclass

from app.game.engine.cards import Card, Suit


@dataclass(frozen=True)
class PlayCardAction:
    seat: int
    card: Card


@dataclass(frozen=True)
class SingAction:
    """Un seme alla volta: il primo canto della mano vale 40, i successivi 20."""

    seat: int
    suit: Suit


Action = PlayCardAction | SingAction
