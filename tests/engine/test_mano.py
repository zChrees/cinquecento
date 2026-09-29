"""P13: svolgimento di una mano, 1v1 e 2v2.

Comando (finché P6 non aggiunge il runner): python -m pytest tests/engine
"""

import random
from itertools import pairwise

import pytest

from app.game.engine.actions import PlayCardAction, SingAction
from app.game.engine.cards import Card, Suit
from app.game.engine.deck import full_deck, shuffled_deck
from app.game.engine.errors import EngineError, InvalidMoveError, NotYourTurnError
from app.game.engine.game import apply, hand_result, legal_actions, new_hand
from app.game.engine.singing import Sing
from app.game.engine.state import team_of


def card(code):
    return Card.from_code(code)


def play(state, seat, code):
    return apply(state, PlayCardAction(seat, card(code)))


# Con full_deck() in ordine: 1v1 → posto 0 denari 1-5, posto 1 denari 6-10, mazzo da coppe-1.
# 2v2 → posto 0 denari 1-5, posto 1 denari 6-10, posto 2 coppe 1-5, posto 3 coppe 6-10, mazzo da spade-1.
ORDERED = full_deck()


# --- Distribuzione --------------------------------------------------------------


@pytest.mark.parametrize(("players", "deck_left"), [(2, 30), (4, 20)])
def test_cinque_carte_a_testa_e_il_resto_nel_mazzo(players, deck_left):
    state = new_hand(players, 1, shuffled_deck(random.Random(1)))
    assert [len(hand) for hand in state.hands] == [5] * players
    assert len(state.deck) == deck_left
    assert state.turn_seat == state.leader_seat == 1
    assert state.trump is None
    assert state.sings == () and state.trick == () and state.last_trick is None


def test_distribuzione_non_valida():
    with pytest.raises(EngineError, match="2 o in 4"):
        new_hand(3, 0, ORDERED)
    with pytest.raises(EngineError, match="Posto di partenza"):
        new_hand(2, 2, ORDERED)
    with pytest.raises(EngineError, match="40 carte"):
        new_hand(2, 0, ORDERED[:39])
    with pytest.raises(EngineError, match="40 carte"):
        new_hand(2, 0, (*ORDERED[:39], ORDERED[0]))


# --- Turni, presa e pesca ------------------------------------------------------------


def test_turni_verso_destra_nel_2v2():
    state = new_hand(4, 2, ORDERED)
    turns = [state.turn_seat]
    for code in ("coppe-1", "coppe-6", "denari-1"):
        seat = state.turn_seat
        state = play(state, seat, code)
        turns.append(state.turn_seat)
    assert turns == [2, 3, 0, 1]


def test_presa_1v1_pesca_prima_chi_vince():
    state = new_hand(2, 0, ORDERED)
    state = play(state, 0, "denari-2")
    assert state.turn_seat == 1
    state = play(state, 1, "denari-6")  # il 6 batte il 2
    assert state.last_trick.winner_seat == 1
    assert state.leader_seat == state.turn_seat == 1
    assert state.trick == ()
    assert state.hands[1][-1] == card("coppe-1")  # chi vince pesca per primo
    assert state.hands[0][-1] == card("coppe-2")
    assert state.deck[0] == card("coppe-3")
    assert [len(hand) for hand in state.hands] == [5, 5]
    assert set(state.captured[1]) == {card("denari-2"), card("denari-6")}
    assert state.captured[0] == ()


def test_presa_2v2_pesca_in_ordine_di_turno_dal_vincitore():
    state = new_hand(4, 0, ORDERED)
    for seat, code in [(0, "denari-2"), (1, "denari-6"), (2, "coppe-1"), (3, "coppe-10")]:
        state = play(state, seat, code)
    # Il 6 di denari vince: coppe è un altro seme e non prende, nemmeno l'Asso
    assert state.last_trick.winner_seat == 1
    assert [state.hands[seat][-1] for seat in (1, 2, 3, 0)] == [
        card("spade-1"), card("spade-2"), card("spade-3"), card("spade-4")]
    assert len(state.captured[team_of(1)]) == 4
    assert state.turn_seat == 1


def test_il_canto_lascia_il_turno_e_fissa_la_briscola():
    state = new_hand(2, 1, ORDERED)  # il posto 1 ha Cavallo e Re di denari
    state = play(state, 1, "denari-8")
    state = play(state, 0, "denari-2")  # il Fante batte il 2: il posto 1 apre la seconda presa
    state = apply(state, SingAction(1, Suit.DENARI))
    assert state.sings == (Sing(1, Suit.DENARI, 40),)
    assert state.trump == Suit.DENARI
    assert state.turn_seat == 1
    assert legal_actions(state, 1).sing == ()  # denari è già cantato


def test_la_briscola_vince_la_presa_dopo_il_canto():
    deck = list(ORDERED)
    # Posto 0: denari 1-4 e coppe-10; posto 1: denari 6, 7, 8, Cavallo e Re di spade
    swap = {card("denari-5"): card("coppe-10"), card("denari-9"): card("spade-9"), card("denari-10"): card("spade-10")}
    for old, new in swap.items():
        i, j = deck.index(old), deck.index(new)
        deck[i], deck[j] = deck[j], deck[i]
    state = new_hand(2, 1, deck)
    state = play(state, 1, "denari-7")
    state = play(state, 0, "denari-2")  # il 7 batte il 2: il posto 1 apre la seconda presa
    state = apply(state, SingAction(1, Suit.SPADE))
    state = play(state, 1, "denari-6")
    state = play(state, 0, "denari-1")
    assert state.last_trick.winner_seat == 0  # senza briscola giocata vince l'Asso di denari
    state = play(state, 0, "coppe-10")
    state = play(state, 1, "spade-9")  # briscola
    assert state.last_trick.winner_seat == 1


def test_nella_prima_presa_nessuno_canta():
    # P64. Posto 1 (apre): denari 6-10, cioè Cavallo e Re di denari; posto 0 (gioca per secondo): denari 1-3,
    # Cavallo e Re di coppe
    deck = list(ORDERED)
    for old, new in {card("denari-4"): card("coppe-9"), card("denari-5"): card("coppe-10")}.items():
        i, j = deck.index(old), deck.index(new)
        deck[i], deck[j] = deck[j], deck[i]
    state = new_hand(2, 1, deck)
    for seat, suit, code in [(1, Suit.DENARI, "denari-6"), (0, Suit.COPPE, "denari-2")]:
        assert legal_actions(state, seat).sing == ()
        with pytest.raises(InvalidMoveError, match="Nella prima presa della mano non si canta"):
            apply(state, SingAction(seat, suit))
        state = play(state, seat, code)
    # Seconda presa: il 6 ha preso, il posto 1 apre e canta 40; poi il posto 0 canta 20
    assert state.last_trick.winner_seat == 1
    assert legal_actions(state, 1).sing == (Suit.DENARI,)
    state = apply(state, SingAction(1, Suit.DENARI))
    state = play(state, 1, "denari-7")
    assert legal_actions(state, 0).sing == (Suit.COPPE,)
    state = apply(state, SingAction(0, Suit.COPPE))
    assert state.sings == (Sing(1, Suit.DENARI, 40), Sing(0, Suit.COPPE, 20))


def test_punti_dei_canti_alla_squadra_nel_2v2():
    history = play_random_hand(4, seed=3, sing_chance=1.0)
    final = history[-1]
    result = hand_result(final)
    expected = [0, 0]
    for done in final.sings:
        expected[done.seat % 2] += done.points
    assert list(result.sing_points) == expected


# --- Mosse non valide: errore chiaro e stato invariato -----------------------------------


@pytest.mark.parametrize(
    ("action", "error", "message"),
    [
        (PlayCardAction(1, Card.from_code("denari-6")), NotYourTurnError, "Non è il tuo turno"),
        (SingAction(1, Suit.DENARI), NotYourTurnError, "Non è il tuo turno"),
        (PlayCardAction(0, Card.from_code("denari-6")), InvalidMoveError, "Non hai questa carta"),
        (PlayCardAction(0, "denari-1"), InvalidMoveError, "Non hai questa carta"),
        (SingAction(0, Suit.COPPE), InvalidMoveError, "Nella prima presa della mano non si canta"),
        (SingAction(0, "denari"), InvalidMoveError, "Seme non valido"),
        (PlayCardAction(2, Card.from_code("denari-1")), InvalidMoveError, "Posto non valido"),
        (PlayCardAction(-1, Card.from_code("denari-1")), InvalidMoveError, "Posto non valido"),
        (PlayCardAction(True, Card.from_code("denari-1")), InvalidMoveError, "Posto non valido"),
        ("gioca", InvalidMoveError, "Mossa non valida"),
    ],
)
def test_mossa_non_valida_rifiutata_e_stato_invariato(action, error, message):
    state = new_hand(2, 0, ORDERED)
    before = state
    with pytest.raises(error, match=message):
        apply(state, action)
    assert state == before
    assert state.hands[0] == ORDERED[:5]


def test_a_mano_finita_niente_mosse():
    final = play_random_hand(2, seed=5)[-1]
    assert final.finished and final.turn_seat is None
    with pytest.raises(InvalidMoveError, match="La mano è finita"):
        apply(final, PlayCardAction(0, card("denari-1")))
    assert legal_actions(final, 0).play == () and legal_actions(final, 1).play == ()


def test_risultato_solo_a_mano_finita():
    with pytest.raises(EngineError, match="non è ancora finita"):
        hand_result(new_hand(2, 0, ORDERED))


# --- Mani intere con seme fisso --------------------------------------------------------


def play_random_hand(players, seed, sing_chance=0.7):
    """Gioca una mano intera scegliendo a caso tra le mosse legali; restituisce tutti gli stati."""
    rng = random.Random(seed)
    state = new_hand(players, rng.randrange(players), shuffled_deck(rng))
    history = [state]
    while not state.finished:
        seat = state.turn_seat
        legal = legal_actions(state, seat)
        if legal.sing and rng.random() < sing_chance:
            action = SingAction(seat, rng.choice(legal.sing))
        else:
            action = PlayCardAction(seat, rng.choice(legal.play))
        state = apply(state, action)
        history.append(state)
    return history


@pytest.mark.parametrize("players", [2, 4])
@pytest.mark.parametrize("seed", range(100))
def test_mano_intera(players, seed):
    history = play_random_hand(players, seed)
    final = history[-1]
    assert final.finished
    assert final.deck == () and all(hand == () for hand in final.hands)
    taken = [c for team in final.captured for c in team]
    assert len(taken) == 40 and set(taken) == set(ORDERED)
    result = hand_result(final)
    assert sum(result.card_points) == 120  # l'ultima presa non dà bonus
    assert sum(result.totals) == 120 + sum(done.points for done in final.sings)
    assert sum(1 for done in final.sings if done.points == 40) == (1 if final.sings else 0)


@pytest.mark.parametrize("players", [2, 4])
@pytest.mark.parametrize("seed", range(30))
def test_ogni_passo_rispetta_le_regole(players, seed):
    history = play_random_hand(players, seed)
    for before, after in pairwise(history):
        # Nessuna carta si perde o si duplica
        everywhere = [*after.deck, *(c for h in after.hands for c in h), *after.played_cards]
        assert len(everywhere) == 40 and set(everywhere) == set(ORDERED)
        closed = len(after.trick) == 0 and len(before.trick) == players - 1
        if closed and before.deck:
            # Pesca: prima chi ha vinto la presa, poi gli altri in ordine di turno
            winner = after.last_trick.winner_seat
            for step in range(players):
                assert after.hands[(winner + step) % players][-1] == before.deck[step]
        if closed and not before.deck:
            # A mazzo finito non cambia niente: si gioca con le carte in mano, senza pescare
            assert sum(map(len, after.hands)) == sum(map(len, before.hands)) - 1
        # Nella prima presa della mano nessuno canta (P64)
        if before.last_trick is None:
            assert legal_actions(before, before.turn_seat).sing == ()
            assert after.sings == ()
        # Chi non è di turno non ha mosse
        for seat in range(players):
            if seat != before.turn_seat:
                assert legal_actions(before, seat).play == () and legal_actions(before, seat).sing == ()


@pytest.mark.parametrize("players", [2, 4])
def test_mosse_legali_coincidono_con_quelle_accettate(players):
    for seed in range(10):
        for state in play_random_hand(players, seed)[:-1]:
            seat = state.turn_seat
            legal = legal_actions(state, seat)
            for c in ORDERED:
                assert _accepted(state, PlayCardAction(seat, c)) == (c in legal.play)
            for suit in Suit:
                assert _accepted(state, SingAction(seat, suit)) == (suit in legal.sing)


def _accepted(state, action):
    try:
        apply(state, action)
    except InvalidMoveError:
        return False
    return True
