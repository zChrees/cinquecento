"""Cantare 40 e 20 (P12, regole in docs/REGOLE-GIOCO.md, "Canti").

Si canta un seme alla volta: il primo canto della mano vale 40 e fissa la briscola,
i successivi valgono 20. I canti della mano sono un elenco di Sing in ordine, come
"sings" nella vista (docs/CONTRATTO-SOCKET.md, 3.3): la briscola e i semi già
cantati si ricavano da lì.

Lo stato della mano arriva con P13: qui i dati si passano uno per uno.
"""

from collections.abc import Collection, Sequence
from dataclasses import dataclass

from app.game.engine.cards import Card, Rank, Suit
from app.game.engine.errors import InvalidMoveError, NotYourTurnError
from app.game.engine.rules import MARIANNA, RuleSet


@dataclass(frozen=True)
class Sing:
    seat: int
    suit: Suit
    points: int


def trump_from_sings(sings: Sequence[Sing]) -> Suit | None:
    """La briscola è il seme del primo canto; None finché nessuno ha cantato (carte franche)."""
    return sings[0].suit if sings else None


def _refusal(
    suit: Suit,
    hand: Collection[Card],
    sings: Sequence[Sing],
    played_cards: Collection[Card],
    deck_count: int,
    first_trick: bool,
    rules: RuleSet,
) -> str | None:
    """Perché quel seme non si può cantare adesso, oppure None se si può."""
    if first_trick:
        return "Nella prima presa della mano non si canta."
    if any(done.suit == suit for done in sings):
        return f"Il seme di {suit.value} è già stato cantato in questa mano."
    king, knight = Card(suit, Rank.KING), Card(suit, Rank.KNIGHT)
    for card in (king, knight):
        if card in played_cards:
            return f"Il {card} è già stato giocato: {suit.value} non si può più cantare."
    if king not in hand or knight not in hand:
        return f"Per cantare servono Re e Cavallo di {suit.value} nella tua mano."
    if deck_count == 0 and len(hand) < rules.min_hand_to_sing_after_deck:
        return f"A mazzo finito si canta solo con almeno {rules.min_hand_to_sing_after_deck} carte in mano."
    return None


def singable_suits(
    *,
    hand: Collection[Card],
    sings: Sequence[Sing],
    played_cards: Collection[Card],
    deck_count: int,
    is_turn: bool,
    first_trick: bool,
    rules: RuleSet = MARIANNA,
) -> list[Suit]:
    """I semi che il giocatore può cantare adesso, sempre nello stesso ordine (legal.sing)."""
    if not is_turn:
        return []
    return [suit for suit in Suit
            if _refusal(suit, hand, sings, played_cards, deck_count, first_trick, rules) is None]


def sing(
    suit: Suit,
    *,
    seat: int,
    hand: Collection[Card],
    sings: Sequence[Sing],
    played_cards: Collection[Card],
    deck_count: int,
    is_turn: bool,
    first_trick: bool,
    rules: RuleSet = MARIANNA,
) -> Sing:
    """Controlla il canto e lo restituisce con i suoi punti; se non è ammesso lo rifiuta.

    is_turn è False anche dopo aver giocato la carta, perché la carta chiude il turno.
    first_trick è True finché la prima presa della mano non si chiude: lì nessuno canta (P64).
    """
    if not isinstance(suit, Suit):
        raise InvalidMoveError("Seme non valido.")
    if not is_turn:
        raise NotYourTurnError("Non è il tuo turno.")
    reason = _refusal(suit, hand, sings, played_cards, deck_count, first_trick, rules)
    if reason is not None:
        raise InvalidMoveError(reason)
    points = rules.sing_20_points if sings else rules.sing_40_points
    return Sing(seat, suit, points)
