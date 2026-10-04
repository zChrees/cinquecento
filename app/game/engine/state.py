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
class LaidDown:
    """Carte calate (P84): chi ha calato, le carte che restavano a ognuno e i 20 del compagno."""

    seat: int
    hands: tuple[tuple[Card, ...], ...]  # per posto, com'erano al momento di calare
    sings: tuple[Sing, ...]  # canti aggiunti dal server per il compagno (D45)


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
    laid_down: LaidDown | None = None  # la mano è finita perché qualcuno ha calato le carte

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
    last_trick: LastTrick  # la presa che ha chiuso la mano (P58): la mano dopo parte con last_trick None
    laid_down: LaidDown | None = None  # con una calata (P84) last_trick è l'ultima presa chiusa prima

    @property
    def totals(self) -> tuple[int, ...]:
        return tuple(cards + sings for cards, sings in zip(self.card_points, self.sing_points, strict=True))


@dataclass(frozen=True)
class GameResult:
    winner_team: int | None  # None = pareggio


@dataclass(frozen=True)
class GameState:
    """Partita intera (P14): mani una dopo l'altra fino al punteggio scelto."""

    num_players: int
    target_score: int
    hand_number: int  # da 1
    first_seat: int  # chi comincia la mano in corso
    hand: HandState  # a partita finita resta l'ultima mano, finita
    scores: tuple[int, ...]  # per squadra, delle mani già finite
    last_hand: HandResult | None  # None nella prima mano
    result: GameResult | None  # None durante la partita

    @property
    def finished(self) -> bool:
        return self.result is not None

    @property
    def dealer_seat(self) -> int:
        """Il mazziere è sempre alla sinistra di chi comincia (D11)."""
        return (self.first_seat - 1) % self.num_players
