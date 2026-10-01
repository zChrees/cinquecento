"""Chi vince la presa (P11, regole in docs/REGOLE-GIOCO.md, "Chi vince la presa").

Non c'è obbligo di rispondere al seme: vince la briscola più forte, se ne è stata
giocata almeno una; altrimenti la carta più forte del seme giocato per primo.
Le carte di altri semi non prendono mai.
"""

from collections.abc import Sequence

from app.game.engine.cards import Card, Suit
from app.game.engine.errors import EngineError
from app.game.engine.rules import MARIANNA


def trick_winner(cards: Sequence[Card], trump: Suit | None) -> int:
    """Posizione della carta vincente nell'ordine di gioco (0 = chi ha aperto la presa).

    trump è None finché nessuno ha cantato 40 (carte franche).
    """
    if len(cards) not in MARIANNA.player_counts:
        raise EngineError("Una presa completa ha 2 o 4 carte.")
    return winning_position(cards, trump)


def winning_position(cards: Sequence[Card], trump: Suit | None) -> int:
    """Come trick_winner, ma anche a presa non finita (P75): la carta che la vincerebbe se finisse lì.

    trick_winner la usa per la presa completa, così la vista e il motore non possono dare
    risposte diverse.
    """
    if not 1 <= len(cards) <= max(MARIANNA.player_counts):
        raise EngineError("Una presa ha da 1 a 4 carte.")
    if not all(isinstance(card, Card) for card in cards):
        raise EngineError("La presa contiene qualcosa che non è una carta.")
    if len(set(cards)) != len(cards):
        raise EngineError("La stessa carta compare due volte nella presa.")
    if trump is not None and not isinstance(trump, Suit):
        raise EngineError("Briscola non valida.")

    lead = cards[0].suit

    def rank_in_trick(position: int) -> tuple[bool, bool, int]:
        card = cards[position]
        return (card.suit == trump, card.suit == lead, card.strength)

    return max(range(len(cards)), key=rank_in_trick)
