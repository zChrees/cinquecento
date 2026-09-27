"""Stato di una mano (P13). È immutabile: ogni mossa produce uno stato nuovo.

I posti sono numerati nell'ordine di gioco (verso destra, docs/CONTRATTO-SOCKET.md, 3.1):
dopo il posto 0 gioca l'1, poi il 2... La squadra di un posto è posto % 2
(1v1: posti 0 e 1; 2v2: squadra 0 = posti 0 e 2, squadra 1 = posti 1 e 3).
"""

from dataclasses import dataclass

from app.game.engine.cards import Card, Suit
from app.game.engine.singing import Sing, trump_from_sings

TEAMS = 2


def team_of(seat: int) -> int:
    return seat % TEAMS


@dataclass(frozen=True)
class TrickPlay:
    seat: int
    card: Card


@dataclass(frozen=True)
class LastTrick:
    winner_seat: int
    plays: tuple[TrickPlay, ...]


@dataclass(frozen=True)
class HandState:
    num_players: int
    hands: tuple[tuple[Card, ...], ...]  # per posto
    deck: tuple[Card, ...]  # si pesca dal primo
    trick: tuple[TrickPlay, ...]  # presa in corso, nell'ordine di gioco
    leader_seat: int  # chi apre la presa in corso
    turn_seat: int | None  # None a mano finita
    sings: tuple[Sing, ...]
    captured: tuple[tuple[Card, ...], ...]  # carte prese, per squadra
    last_trick: LastTrick | None

    @property
    def finished(self) -> bool:
        return self.turn_seat is None

    @property
    def trump(self) -> Suit | None:
        return trump_from_sings(self.sings)

    @property
    def played_cards(self) -> frozenset[Card]:
        """Carte già finite sul tavolo in questa mano: prese chiuse e presa in corso."""
        taken = (card for team in self.captured for card in team)
        return frozenset((*taken, *(play.card for play in self.trick)))


@dataclass(frozen=True)
class HandResult:
    card_points: tuple[int, ...]  # per squadra
    sing_points: tuple[int, ...]  # per squadra

    @property
    def totals(self) -> tuple[int, ...]:
        return tuple(cards + sings for cards, sings in zip(self.card_points, self.sing_points, strict=True))
