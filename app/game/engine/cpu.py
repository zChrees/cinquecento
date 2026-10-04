"""Mossa della CPU (P68, D43): un "giocatore medio", non casuale.

La CPU sceglie guardando **solo la propria vista** (player_view, contratto 3.3): le
sue carte, la presa in corso, la briscola, le carte rimaste nel mazzo, i canti e le
mosse legali. Non vede mai le carte degli altri né il mazzo.

Strategia (decisa da Giuseppe il 30/09/2026):
- canta appena può; con più semi, quello di cui ha più carte (il primo canto fa la briscola);
- quando risponde: se può prendere senza briscola prende, con la carta più economica;
  con la briscola prende solo se la presa vale almeno TRUMP_WORTH punti (a mazzo
  finito basta che valga qualcosa); altrimenti scarta la carta che vale meno;
- quando apre gioca la carta che vale meno e tiene Assi, Tre e briscole; a mazzo finito
  apre con la briscola più forte;
- scartando o aprendo evita di rompere una coppia Re e Cavallo ancora da cantare;
- cala le carte appena può (P84, D45), dopo aver cantato.
A parità sceglie a caso.
"""

import random
import secrets

from app.game.engine.actions import Action, LayDownAction, PlayCardAction, SingAction
from app.game.engine.cards import Card, Rank, Suit
from app.game.engine.errors import EngineError

TRUMP_WORTH = 10  # punti della presa per cui vale la pena usare una briscola


def cpu_move(view: dict, rng: random.Random | None = None) -> Action:
    """La mossa della CPU dalla sua vista. In gioco rng è None; i test passano un seme fisso."""
    seat = view["you"]["seat"]
    legal = view["legal"]
    if not legal["play"]:
        raise EngineError("Non è il turno della CPU.")
    if rng is None:
        rng = secrets.SystemRandom()
    hand = [_card(card) for card in view["hand"]]
    if legal["sing"]:
        suits = [Suit(suit) for suit in legal["sing"]]
        return SingAction(seat, _best(suits, lambda suit: (-_count(hand, suit), -_strength(hand, suit)), rng))
    if legal["lay_down"]:
        return LayDownAction(seat)  # P84: prende tutte le prese rimaste, meglio di così non si fa

    playable = [_card(card) for card in legal["play"]]
    trump = None if view["trump"] is None else Suit(view["trump"])
    deck_empty = view["deck_count"] == 0
    pairs = _open_pairs(hand, view["sings"])
    trick = [_card(play["card"]) for play in view["trick"]["cards"]]
    if trick:
        card = _answer(playable, trick, trump, deck_empty, pairs, rng)
    else:
        card = _lead(playable, trump, deck_empty, pairs, rng)
    return PlayCardAction(seat, card)


def _answer(playable, trick, trump, deck_empty, pairs, rng):
    lead = trick[0].suit
    best = trick[0]
    for card in trick[1:]:
        if _beats(card, best, lead, trump):
            best = card
    worth = sum(card.points for card in trick)
    winners = [card for card in playable if _beats(card, best, lead, trump)]
    plain = [card for card in winners if card.suit != trump]
    if plain:
        return _best(plain, lambda card: (card.points, card.strength), rng)
    trumps = [card for card in winners if card.suit == trump]
    if trumps and (worth >= TRUMP_WORTH or (deck_empty and worth > 0)):
        return _best(trumps, lambda card: (card.points, card.strength), rng)
    return _discard(playable, trump, pairs, rng)


def _lead(playable, trump, deck_empty, pairs, rng):
    trumps = [card for card in playable if card.suit == trump]
    if deck_empty and trumps:
        return _best(trumps, lambda card: -card.strength, rng)
    return _discard(playable, trump, pairs, rng)


def _discard(playable, trump, pairs, rng):
    """La carta che costa meno: pochi punti, non briscola, debole, senza rompere una coppia."""
    return _best(playable, lambda card: (card in pairs, card.points, card.suit == trump, card.strength), rng)


def _beats(card, best, lead, trump):
    """Stessa regola di trick.py: vince la briscola più forte, poi la più forte del seme di uscita."""
    def rank(c):
        return (c.suit == trump, c.suit == lead, c.strength)
    return rank(card) > rank(best)


def _open_pairs(hand, sings):
    """Re e Cavallo dello stesso seme ancora in mano e non cantati: meglio non giocarli."""
    sung = {Suit(done["suit"]) for done in sings}
    cards = set(hand)
    pairs = set()
    for suit in Suit:
        king, knight = Card(suit, Rank.KING), Card(suit, Rank.KNIGHT)
        if suit not in sung and king in cards and knight in cards:
            pairs |= {king, knight}
    return pairs


def _best(items, key, rng):
    lowest = min(key(item) for item in items)
    return rng.choice([item for item in items if key(item) == lowest])


def _count(hand, suit):
    return sum(card.suit == suit for card in hand)


def _strength(hand, suit):
    return sum(card.strength for card in hand if card.suit == suit)


def _card(data: dict) -> Card:
    return Card(Suit(data["suit"]), Rank(data["rank"]))
