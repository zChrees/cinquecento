"""P15: mossa automatica allo scadere del turno (D12).

Comando (finché P6 non aggiunge il runner): python -m pytest tests/engine
"""

import random
from dataclasses import replace

import pytest

from app.game.engine import auto_move as auto_move_module
from app.game.engine.actions import PlayCardAction
from app.game.engine.auto_move import auto_move
from app.game.engine.cards import Card, Suit
from app.game.engine.deck import full_deck
from app.game.engine.errors import EngineError
from app.game.engine.game import apply_game, game_legal_actions, new_game, new_hand
from app.game.engine.rules import MARIANNA
from app.game.engine.singing import Sing


def game_with(codes, trump=None):
    """Partita 1v1 in cui il posto 0 è di turno con esattamente queste carte."""
    game = new_game(2, 300, rng=random.Random(0))
    hand = new_hand(2, 0, full_deck())
    hand = replace(
        hand,
        hands=(tuple(Card.from_code(code) for code in codes), hand.hands[1]),
        sings=() if trump is None else (Sing(1, trump, 40),),
    )
    return replace(game, first_seat=0, hand=hand)


def chosen(game, seed=0):
    action = auto_move(game, rng=random.Random(seed))
    assert isinstance(action, PlayCardAction)
    assert action.seat == game.hand.turn_seat
    return action.card.code


# --- Un test per ogni passo di D12 --------------------------------------------------


def test_1_la_carta_con_meno_punti():
    # Asso 11, 3 10, Re 4, Fante 2
    assert chosen(game_with(["denari-1", "coppe-3", "spade-10", "bastoni-8"])) == "bastoni-8"


def test_1_i_punti_contano_prima_della_briscola():
    # Il 2 di briscola vale 0 punti, l'Asso di spade 11: si gioca la briscola
    assert chosen(game_with(["spade-1", "coppe-2"], trump=Suit.COPPE)) == "coppe-2"


def test_2_a_parita_di_punti_una_non_di_briscola():
    # Il 2 di coppe è più debole del 7 di spade, ma è briscola
    assert chosen(game_with(["coppe-2", "spade-7"], trump=Suit.COPPE)) == "spade-7"


def test_3_a_parita_la_piu_debole():
    assert chosen(game_with(["spade-7", "bastoni-4", "denari-6", "coppe-1"])) == "bastoni-4"


def test_3_tutte_di_briscola_la_piu_debole():
    assert chosen(game_with(["coppe-7", "coppe-4", "coppe-5"], trump=Suit.COPPE)) == "coppe-4"


def test_3_a_parita_di_briscola_la_piu_debole_tra_le_non_briscola():
    cards = ["coppe-2", "spade-6", "bastoni-5", "denari-7"]
    assert chosen(game_with(cards, trump=Suit.COPPE)) == "bastoni-5"


def test_4_se_resta_una_parita_a_caso():
    game = game_with(["coppe-4", "spade-4", "denari-1", "bastoni-7"])
    picks = {chosen(game, seed) for seed in range(50)}
    assert picks == {"coppe-4", "spade-4"}
    # Stesso seme, stessa scelta
    for seed in range(10):
        assert chosen(game, seed) == chosen(game, seed)


def test_4_parita_tra_carte_non_di_briscola():
    game = game_with(["coppe-2", "spade-2", "bastoni-2"], trump=Suit.COPPE)
    assert {chosen(game, seed) for seed in range(50)} == {"spade-2", "bastoni-2"}


# --- Non canta mai, è sempre legale --------------------------------------------------


def test_non_canta_mai():
    # Mazzo in ordine: il posto 1 ha denari 6-10, cioè Cavallo e Re di denari
    game = new_game(2, 300, rng=random.Random(0))
    game = replace(game, first_seat=1, hand=new_hand(2, 1, full_deck()))
    # Nella prima presa non si canta (P64): il Fante del posto 1 batte il 2, e il posto 1 apre la seconda
    game = apply_game(game, PlayCardAction(1, Card.from_code("denari-8")))
    game = apply_game(game, PlayCardAction(0, Card.from_code("denari-2")))
    assert game_legal_actions(game, 1).sing == (Suit.DENARI,)
    action = auto_move(game, rng=random.Random(0))
    assert action == PlayCardAction(1, Card.from_code("denari-6"))
    assert apply_game(game, action).hand.sings == ()


@pytest.mark.parametrize("seed", range(5))
@pytest.mark.parametrize("players", (2, 4))
@pytest.mark.parametrize("target", MARIANNA.target_scores)
def test_partite_intere_solo_con_la_mossa_automatica(target, players, seed):
    rng = random.Random(seed)
    game = new_game(players, target, rng=rng)
    while not game.finished:
        action = auto_move(game, rng=rng)
        assert action.card in game_legal_actions(game, action.seat).play
        game = apply_game(game, action, rng=rng)  # mai rifiutata
        assert game.hand.sings == ()
    assert max(game.scores) >= target


def test_a_partita_finita_non_c_e_mossa():
    game = new_game(2, 150, rng=random.Random(0))
    rng = random.Random(0)
    while not game.finished:
        game = apply_game(game, auto_move(game, rng=rng), rng=rng)
    with pytest.raises(EngineError, match="La partita è finita."):
        auto_move(game, rng=random.Random(0))


def test_senza_seme_usa_systemrandom(monkeypatch):
    used = []

    class Spy(random.Random):
        def choice(self, seq):
            used.append(True)
            return super().choice(seq)

    monkeypatch.setattr(auto_move_module.secrets, "SystemRandom", Spy)
    game = game_with(["coppe-4", "spade-4"])
    assert auto_move(game).card.code in ("coppe-4", "spade-4")
    assert used == [True]
