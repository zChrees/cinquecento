"""P11: chi vince la presa, con e senza briscola, in 1v1 (2 carte) e 2v2 (4 carte).

Comando (finché P6 non aggiunge il runner): python -m pytest tests/engine
"""

import itertools
import random

import pytest

from app.game.engine.cards import Card, Suit
from app.game.engine.deck import full_deck
from app.game.engine.errors import EngineError
from app.game.engine.trick import trick_winner

SUITS_OR_NONE = [None, "denari", "coppe", "spade", "bastoni"]


def cards(*codes):
    return [Card.from_code(code) for code in codes]


def suit(name):
    return None if name is None else Suit(name)


# --- 1v1: due carte ---------------------------------------------------------


def test_senza_briscola_vince_la_piu_forte_del_seme_di_uscita():
    assert trick_winner(cards("coppe-7", "coppe-3"), None) == 1
    assert trick_winner(cards("coppe-3", "coppe-7"), None) == 0


def test_senza_briscola_un_altro_seme_non_prende():
    # L'Asso di spade è più forte del 2 di coppe, ma non è del seme di uscita
    assert trick_winner(cards("coppe-2", "spade-1"), None) == 0


def test_con_briscola_la_briscola_prende():
    assert trick_winner(cards("coppe-1", "spade-2"), suit("spade")) == 1


def test_briscola_contro_briscola_vince_la_piu_forte():
    assert trick_winner(cards("spade-10", "spade-3"), suit("spade")) == 1
    assert trick_winner(cards("spade-3", "spade-10"), suit("spade")) == 0


def test_con_briscola_ma_nessuna_giocata_vince_il_seme_di_uscita():
    assert trick_winner(cards("coppe-9", "coppe-8"), suit("spade")) == 0
    assert trick_winner(cards("coppe-4", "bastoni-1"), suit("spade")) == 0


def test_uscita_di_briscola():
    assert trick_winner(cards("spade-2", "coppe-1"), suit("spade")) == 0


def test_ordine_di_forza_completo_nella_presa():
    # A > 3 > R > C > F > 7 > 6 > 5 > 4 > 2: ogni carta batte tutte quelle dopo di lei
    order = ["1", "3", "10", "9", "8", "7", "6", "5", "4", "2"]
    for stronger, weaker in itertools.combinations(order, 2):
        assert trick_winner(cards(f"denari-{weaker}", f"denari-{stronger}"), None) == 1
        assert trick_winner(cards(f"denari-{stronger}", f"denari-{weaker}"), None) == 0


# --- 2v2: quattro carte -----------------------------------------------------


def test_4_carte_senza_briscola():
    assert trick_winner(cards("coppe-7", "spade-1", "coppe-10", "bastoni-3"), None) == 2


def test_4_carte_senza_briscola_vince_chi_esce_se_nessuno_risponde():
    assert trick_winner(cards("coppe-2", "spade-1", "denari-1", "bastoni-1"), None) == 0


def test_4_carte_con_una_briscola():
    assert trick_winner(cards("coppe-1", "coppe-3", "denari-2", "coppe-10"), suit("denari")) == 2


def test_4_carte_con_piu_briscole():
    assert trick_winner(cards("denari-7", "coppe-1", "denari-9", "denari-4"), suit("denari")) == 2


def test_4_carte_con_briscola_ma_nessuna_giocata():
    assert trick_winner(cards("bastoni-8", "coppe-1", "bastoni-3", "spade-1"), suit("denari")) == 2


def test_4_carte_vince_l_ultimo():
    assert trick_winner(cards("spade-4", "spade-5", "spade-6", "spade-1"), suit("coppe")) == 3


# --- Controllo su tutte le coppie e su molte prese da 4 ---------------------


def check_rule(trick, trump, winner):
    """La regola scritta in docs/REGOLE-GIOCO.md, controllata sul risultato."""
    played_trumps = [card for card in trick if card.suit == trump]
    winning_suit = trump if played_trumps else trick[0].suit
    assert trick[winner].suit == winning_suit
    same_suit = [card for card in trick if card.suit == winning_suit]
    assert trick[winner].strength == max(card.strength for card in same_suit)


@pytest.mark.parametrize("trump_name", SUITS_OR_NONE)
def test_tutte_le_coppie_di_carte(trump_name):
    trump = suit(trump_name)
    for trick in itertools.permutations(full_deck(), 2):
        check_rule(trick, trump, trick_winner(trick, trump))


@pytest.mark.parametrize("trump_name", SUITS_OR_NONE)
def test_molte_prese_da_4_con_seme_fisso(trump_name):
    trump = suit(trump_name)
    rng = random.Random(11)
    deck = full_deck()
    for _ in range(2000):
        trick = rng.sample(deck, 4)
        check_rule(trick, trump, trick_winner(trick, trump))


# --- Prese non valide ------------------------------------------------------


@pytest.mark.parametrize("count", [0, 1, 3, 5])
def test_numero_di_carte_sbagliato(count):
    with pytest.raises(EngineError, match="2 o 4 carte"):
        trick_winner(full_deck()[:count], None)


def test_carta_ripetuta():
    with pytest.raises(EngineError, match="due volte"):
        trick_winner(cards("coppe-1", "coppe-1"), None)


def test_non_carta():
    with pytest.raises(EngineError, match="non è una carta"):
        trick_winner(["coppe-1", "coppe-3"], None)


def test_briscola_non_valida():
    with pytest.raises(EngineError, match="Briscola non valida"):
        trick_winner(cards("coppe-1", "coppe-3"), "coppe")
