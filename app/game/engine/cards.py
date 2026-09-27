"""Carte siciliane: seme, valore, punti e forza nella presa (P10, regole in docs/REGOLE-GIOCO.md)."""

from dataclasses import dataclass
from enum import Enum

from app.game.engine.errors import InvalidMoveError


class Suit(Enum):
    DENARI = "denari"
    COPPE = "coppe"
    SPADE = "spade"
    BASTONI = "bastoni"


class Rank(Enum):
    """Il valore è il numero stampato sulla carta siciliana (Fante 8, Cavallo 9, Re 10)."""

    ACE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    JACK = 8
    KNIGHT = 9
    KING = 10


RANK_NAMES = {
    Rank.ACE: "Asso",
    Rank.TWO: "2",
    Rank.THREE: "3",
    Rank.FOUR: "4",
    Rank.FIVE: "5",
    Rank.SIX: "6",
    Rank.SEVEN: "7",
    Rank.JACK: "Fante",
    Rank.KNIGHT: "Cavallo",
    Rank.KING: "Re",
}

POINTS = {
    Rank.ACE: 11,
    Rank.THREE: 10,
    Rank.KING: 4,
    Rank.KNIGHT: 3,
    Rank.JACK: 2,
    Rank.SEVEN: 0,
    Rank.SIX: 0,
    Rank.FIVE: 0,
    Rank.FOUR: 0,
    Rank.TWO: 0,
}

# Dalla più debole alla più forte: A > 3 > R > C > F > 7 > 6 > 5 > 4 > 2
STRENGTH_ORDER = (
    Rank.TWO,
    Rank.FOUR,
    Rank.FIVE,
    Rank.SIX,
    Rank.SEVEN,
    Rank.JACK,
    Rank.KNIGHT,
    Rank.KING,
    Rank.THREE,
    Rank.ACE,
)
STRENGTH = {rank: position for position, rank in enumerate(STRENGTH_ORDER, start=1)}


@dataclass(frozen=True)
class Card:
    suit: Suit
    rank: Rank

    @property
    def points(self) -> int:
        return POINTS[self.rank]

    @property
    def strength(self) -> int:
        """Forza nella presa: più alta è, più la carta è forte (2 vale 1, Asso vale 10)."""
        return STRENGTH[self.rank]

    @property
    def code(self) -> str:
        """Codice stabile usato nelle viste e nelle azioni, per esempio "denari-1"."""
        return f"{self.suit.value}-{self.rank.value}"

    @classmethod
    def from_code(cls, code: str) -> "Card":
        """Carta dal suo codice; un codice sconosciuto è una mossa non valida."""
        card = _BY_CODE.get(code) if isinstance(code, str) else None
        if card is None:
            raise InvalidMoveError("Carta non valida.")
        return card

    def __str__(self) -> str:
        return f"{RANK_NAMES[self.rank]} di {self.suit.value}"


# Confronto esatto con i 40 codici: niente conversioni che accettino "denari-01" o "denari- 1"
_BY_CODE = {card.code: card for card in (Card(suit, rank) for suit in Suit for rank in Rank)}
