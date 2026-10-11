"""Mazzo da 40 carte siciliane (P10).

In gioco si mescola con secrets.SystemRandom, che non si può prevedere; i test
passano un random.Random con un seme fisso per avere sempre lo stesso ordine.
"""

import random
import secrets

from app.game.engine.cards import Card, Rank, Suit


def full_deck() -> tuple[Card, ...]:
    """Le 40 carte in ordine fisso: seme per seme, dall'Asso al Re."""
    return tuple(Card(suit, rank) for suit in Suit for rank in Rank)


def shuffled_deck(rng: random.Random | None = None) -> tuple[Card, ...]:
    if rng is None:
        rng = secrets.SystemRandom()
    cards = list(full_deck())
    rng.shuffle(cards)
    return tuple(cards)
