"""Mazzo da 40 carte siciliane (P10).

In gioco si mescola con secrets.SystemRandom, che non si può prevedere; i test
passano un random.Random con un seme fisso per avere sempre lo stesso ordine.

Cosa contiene:
    full_deck()          le 40 carte in ordine fisso
    shuffled_deck(rng)   le 40 carte mescolate, per esempio shuffled_deck(None) in gioco

DA DOVE ARRIVANO I DATI: game.py chiama shuffled_deck all'inizio di ogni mano
(new_game e la mano successiva), passando l'rng che riceve dalla stanza
(app/realtime/room.py) o dai test.
"""

import random
import secrets

from app.game.engine.cards import Card, Rank, Suit


def full_deck() -> tuple[Card, ...]:
    """Le 40 carte in ordine fisso: seme per seme, dall'Asso al Re.

    In parole semplici:
        full_deck()
        Restituisce una tupla (un elenco che non si può cambiare) con le 40 carte:
        prima i 10 denari dall'Asso al Re, poi le coppe, le spade e i bastoni.
        La usano shuffled_deck qui sotto e game.py, che controlla che un mazzo
        passato dai test abbia proprio queste 40 carte.

        tuple[Card, ...]: il tipo scritto dopo la freccia. Vuol dire "una tupla di
        carte, lunga quanto serve" (i tre puntini).
    """
    cards = []
    for suit in Suit:
        for rank in Rank:
            cards.append(Card(suit, rank))
    return tuple(cards)


def shuffled_deck(rng: random.Random | None = None) -> tuple[Card, ...]:
    """Le 40 carte mescolate.

    In parole semplici:
        shuffled_deck(rng)
        Restituisce le 40 carte in un ordine a caso; si pesca dalla prima.

        rng: il generatore di numeri a caso che decide l'ordine. Facoltativo
             (= None vuol dire che, se manca, vale None; "random.Random | None" vuol
             dire "un random.Random oppure None"). Arriva da game.py, che lo riceve
             dalla stanza (None in gioco) o dai test (random.Random(42), sempre lo
             stesso ordine). Con None si usa secrets.SystemRandom, che prende il caso
             dal sistema operativo e non si può prevedere.
    """
    if rng is None:
        rng = secrets.SystemRandom()
    # shuffle mescola una lista sul posto, quindi serve una lista (la tupla non si cambia)
    cards = list(full_deck())
    rng.shuffle(cards)
    return tuple(cards)
