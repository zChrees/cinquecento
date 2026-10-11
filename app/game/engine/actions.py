"""Azioni che un giocatore può fare nel suo turno (P13): cantare un seme, giocare una carta
o, a mazzo finito, calare le carte (P84)."""

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


@dataclass(frozen=True)
class LayDownAction:
    """"Cala le carte" (P84, D45): la squadra di chi cala prende tutte le prese rimaste."""

    seat: int


Action = PlayCardAction | SingAction | LayDownAction
