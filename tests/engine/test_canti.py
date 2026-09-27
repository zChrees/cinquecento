"""P12: cantare 40 e 20, un seme alla volta.

Comando (finché P6 non aggiunge il runner): python -m pytest tests/engine
"""

import random

import pytest

from app.game.engine.cards import Card, Suit
from app.game.engine.deck import full_deck
from app.game.engine.errors import InvalidMoveError, NotYourTurnError
from app.game.engine.singing import Sing, sing, singable_suits, trump_from_sings


def cards(*codes):
    return [Card.from_code(code) for code in codes]


def try_sing(suit, *, seat=0, hand, sings=(), played=(), deck_count=20, is_turn=True):
    return sing(suit, seat=seat, hand=hand, sings=list(sings), played_cards=set(played),
                deck_count=deck_count, is_turn=is_turn)


def legal(*, hand, sings=(), played=(), deck_count=20, is_turn=True):
    return singable_suits(hand=hand, sings=list(sings), played_cards=set(played),
                          deck_count=deck_count, is_turn=is_turn)


HAND_COPPE = cards("coppe-10", "coppe-9", "denari-1", "spade-4", "bastoni-2")
HAND_DUE_COPPIE = cards("coppe-10", "coppe-9", "spade-10", "spade-9", "bastoni-2")


# --- 40 e 20 ----------------------------------------------------------------


def test_primo_canto_vale_40_e_fissa_la_briscola():
    done = try_sing(Suit.COPPE, seat=1, hand=HAND_COPPE)
    assert done == Sing(seat=1, suit=Suit.COPPE, points=40)
    assert trump_from_sings([done]) == Suit.COPPE


def test_senza_canti_niente_briscola():
    assert trump_from_sings([]) is None


def test_secondo_canto_vale_20_e_non_cambia_la_briscola():
    first = Sing(seat=1, suit=Suit.DENARI, points=40)
    second = try_sing(Suit.COPPE, seat=0, hand=HAND_COPPE, sings=[first])
    assert second.points == 20
    assert trump_from_sings([first, second]) == Suit.DENARI


def test_il_40_e_il_primo_canto_della_mano_di_chiunque():
    # Nel 2v2 l'altra squadra ha già cantato 40: il mio canto vale 20
    other_team = Sing(seat=3, suit=Suit.BASTONI, points=40)
    assert try_sing(Suit.COPPE, seat=0, hand=HAND_COPPE, sings=[other_team]).points == 20


def test_due_canti_nello_stesso_turno():
    first = try_sing(Suit.SPADE, hand=HAND_DUE_COPPIE)
    second = try_sing(Suit.COPPE, hand=HAND_DUE_COPPIE, sings=[first])
    assert (first.points, second.points) == (40, 20)
    assert trump_from_sings([first, second]) == Suit.SPADE


def test_con_due_coppie_sceglie_il_giocatore_la_briscola():
    assert trump_from_sings([try_sing(Suit.COPPE, hand=HAND_DUE_COPPIE)]) == Suit.COPPE
    assert trump_from_sings([try_sing(Suit.SPADE, hand=HAND_DUE_COPPIE)]) == Suit.SPADE


def test_si_canta_anche_senza_aprire_la_presa_e_senza_aver_preso():
    # Il canto dipende solo da turno, mano e carte giocate: nessun dato su chi apre o chi ha preso
    assert try_sing(Suit.COPPE, hand=HAND_COPPE, played=cards("spade-1")).points == 40


# --- Turno ------------------------------------------------------------------


def test_fuori_turno_non_si_canta():
    with pytest.raises(NotYourTurnError, match="Non è il tuo turno"):
        try_sing(Suit.COPPE, hand=HAND_COPPE, is_turn=False)
    assert legal(hand=HAND_COPPE, is_turn=False) == []


def test_dopo_aver_giocato_la_carta_non_si_canta():
    # Giocata la carta il turno passa: stessa mano meno una carta, is_turn falso
    after_play = HAND_COPPE[:-1]
    with pytest.raises(NotYourTurnError):
        try_sing(Suit.COPPE, hand=after_play, played=HAND_COPPE[-1:], is_turn=False)


def test_fuori_turno_e_una_mossa_non_valida():
    assert issubclass(NotYourTurnError, InvalidMoveError)


# --- Coppia -----------------------------------------------------------------


def test_serve_la_coppia_in_mano():
    only_king = cards("coppe-10", "denari-1", "spade-4", "bastoni-2", "bastoni-3")
    with pytest.raises(InvalidMoveError, match="servono Re e Cavallo di coppe"):
        try_sing(Suit.COPPE, hand=only_king)
    assert legal(hand=only_king) == []


def test_non_si_canta_con_la_coppia_divisa_tra_compagni():
    # Il Re è mio, il Cavallo è del compagno: conta solo la mia mano
    mine = cards("coppe-10", "denari-1", "spade-4", "bastoni-2", "bastoni-3")
    with pytest.raises(InvalidMoveError, match="nella tua mano"):
        try_sing(Suit.COPPE, hand=mine)


def test_re_e_fante_non_bastano():
    hand = cards("coppe-10", "coppe-8", "denari-1", "spade-4", "bastoni-2")
    with pytest.raises(InvalidMoveError):
        try_sing(Suit.COPPE, hand=hand)


# --- Seme bruciato e seme già cantato -----------------------------------------


@pytest.mark.parametrize(("played", "name"), [("coppe-10", "Re di coppe"), ("coppe-9", "Cavallo di coppe")])
def test_non_si_canta_se_re_o_cavallo_gia_giocato(played, name):
    hand = [card for card in HAND_COPPE if card.code != played] + cards("spade-5")
    with pytest.raises(InvalidMoveError, match=f"Il {name} è già stato giocato"):
        try_sing(Suit.COPPE, hand=hand, played=cards(played))
    assert Suit.COPPE not in legal(hand=hand, played=cards(played))


def test_lo_stesso_seme_non_si_canta_due_volte():
    first = try_sing(Suit.COPPE, hand=HAND_COPPE)
    with pytest.raises(InvalidMoveError, match="già stato cantato"):
        try_sing(Suit.COPPE, hand=HAND_COPPE, sings=[first])
    # Nemmeno nel turno dopo, con Re e Cavallo ancora in mano
    with pytest.raises(InvalidMoveError, match="già stato cantato"):
        try_sing(Suit.COPPE, hand=HAND_COPPE[:4], sings=[first], deck_count=18)
    assert legal(hand=HAND_COPPE, sings=[first]) == []


# --- Mazzo finito -------------------------------------------------------------


def test_a_mazzo_finito_si_canta_con_3_carte():
    hand = cards("coppe-10", "coppe-9", "denari-1")
    assert try_sing(Suit.COPPE, hand=hand, deck_count=0).points == 40
    assert legal(hand=hand, deck_count=0) == [Suit.COPPE]


def test_a_mazzo_finito_si_canta_con_4_o_5_carte():
    assert try_sing(Suit.COPPE, hand=HAND_COPPE[:4], deck_count=0).points == 40
    assert try_sing(Suit.COPPE, hand=HAND_COPPE, deck_count=0).points == 40


def test_a_mazzo_finito_non_si_canta_con_2_carte():
    hand = cards("coppe-10", "coppe-9")
    with pytest.raises(InvalidMoveError, match="almeno 3 carte"):
        try_sing(Suit.COPPE, hand=hand, deck_count=0)
    assert legal(hand=hand, deck_count=0) == []


def test_con_il_mazzo_non_finito_conta_solo_la_coppia():
    assert try_sing(Suit.COPPE, hand=HAND_COPPE, deck_count=2).points == 40


# --- Mosse legali -------------------------------------------------------------


def test_semi_legali_in_ordine_fisso():
    assert legal(hand=HAND_DUE_COPPIE) == [Suit.COPPE, Suit.SPADE]


def test_seme_non_valido():
    with pytest.raises(InvalidMoveError, match="Seme non valido"):
        try_sing("coppe", hand=HAND_COPPE)


def test_mosse_legali_coincidono_con_i_canti_accettati():
    rng = random.Random(12)
    deck = full_deck()
    for _ in range(3000):
        size = rng.choice([2, 3, 4, 5])
        hand = rng.sample(deck, size)
        rest = [card for card in deck if card not in hand]
        played = rng.sample(rest, rng.randint(0, 12))
        sings = [Sing(1, suit, 40 if i == 0 else 20) for i, suit in enumerate(rng.sample(list(Suit), rng.randint(0, 2)))]
        deck_count = rng.choice([0, 0, 2, 10, 20])
        is_turn = rng.random() < 0.8
        allowed = legal(hand=hand, sings=sings, played=played, deck_count=deck_count, is_turn=is_turn)
        for suit in Suit:
            try:
                try_sing(suit, hand=hand, sings=sings, played=played, deck_count=deck_count, is_turn=is_turn)
                accepted = True
            except InvalidMoveError:
                accepted = False
            assert accepted == (suit in allowed)
