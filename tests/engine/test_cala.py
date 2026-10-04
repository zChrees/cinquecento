"""P84: "Cala le carte" (D45). Regola in docs/REGOLE-GIOCO.md, "Calare le carte".

Il controllo veloce (lay_down.team_wins_all) si confronta con un calcolo lento che gioca
davvero ogni sequenza di carte con apply del motore, quindi con la regola vera di chi
prende la presa.
"""

import json
import random
from dataclasses import replace

import pytest

from app.game.engine.actions import LayDownAction, PlayCardAction, SingAction
from app.game.engine.auto_move import auto_move
from app.game.engine.cards import Card, Suit
from app.game.engine.cpu import cpu_move
from app.game.engine.deck import full_deck, shuffled_deck
from app.game.engine.errors import InvalidMoveError, NotYourTurnError
from app.game.engine.game import (
    apply,
    apply_game,
    hand_result,
    legal_actions,
    new_game,
    new_hand,
)
from app.game.engine.lay_down import team_wins_all
from app.game.engine.singing import Sing, singable_suits
from app.game.engine.state import HandState, LastTrick, TrickPlay, team_of
from app.game.engine.views import card_to_dict, player_view

DENARI, COPPE, SPADE, BASTONI = Suit.DENARI, Suit.COPPE, Suit.SPADE, Suit.BASTONI


def card(code):
    return Card.from_code(code)


def end_state(hands, leader=0, sings=()):
    """Mano a mazzo finito, a inizio presa, di turno `leader`.

    hands: codici delle carte rimaste a ogni posto; sings: (posto, seme, punti).
    Le altre carte sono già state prese, metà per squadra.
    """
    hands = tuple(tuple(card(code) for code in hand) for hand in hands)
    rest = [c for c in full_deck() if not any(c in hand for hand in hands)]
    players = len(hands)
    return HandState(
        num_players=players,
        hands=hands,
        deck=(),
        trick=(),
        leader_seat=leader,
        turn_seat=leader,
        sings=tuple(Sing(seat, suit, points) for seat, suit, points in sings),
        captured=(tuple(rest[: len(rest) // 2]), tuple(rest[len(rest) // 2:])),
        last_trick=LastTrick(leader, (TrickPlay(leader, rest[0]), TrickPlay((leader + 1) % players, rest[1]))),
    )


def brute_wins_all(state, team, known=None):
    """Lento ma sicuro: gioca ogni carta possibile con apply. La squadra sceglie la carta
    migliore, gli avversari quella peggiore per lei; ogni presa chiusa deve essere sua."""
    if known is None:
        known = {}
    if state.finished:
        return True
    key = (state.hands, state.trick, state.turn_seat)
    if key in known:
        return known[key]
    seat = state.turn_seat
    outcomes = []
    for c in state.hands[seat]:
        after = apply(state, PlayCardAction(seat, c))
        closed = not after.trick
        if closed and team_of(after.last_trick.winner_seat) != team:
            outcomes.append(False)
        else:
            outcomes.append(brute_wins_all(after, team, known))
    result = any(outcomes) if team_of(seat) == team else all(outcomes)
    known[key] = result
    return result


def random_hands(rng, players, size):
    deck = list(full_deck())
    rng.shuffle(deck)
    return [[c.code for c in deck[seat * size:(seat + 1) * size]] for seat in range(players)]


# --- Il calcolo veloce dà la stessa risposta di quello lento -----------------------------


@pytest.mark.parametrize(("players", "sizes", "cases"), [(2, (1, 2, 3, 4, 5), 400), (4, (1, 2, 3), 400)])
def test_calcolo_veloce_uguale_a_quello_che_gioca_tutto(players, sizes, cases):
    rng = random.Random(84)
    true_cases = 0
    for _ in range(cases):
        hands = random_hands(rng, players, rng.choice(sizes))
        leader = rng.randrange(players)
        trump = rng.choice([None, *Suit])
        state = end_state(hands, leader, sings=() if trump is None else ((1, trump, 40),))
        fast = team_wins_all(tuple(frozenset(hand) for hand in state.hands), leader, team_of(leader), trump)
        assert fast == brute_wins_all(state, team_of(leader)), (hands, leader, trump)
        true_cases += fast
    assert true_cases > cases // 20  # ci sono abbastanza casi veri da provare qualcosa


def test_calcolo_veloce_nel_2v2_con_quattro_carte():
    # Con 5 carte a testa il calcolo lento dura circa 20 s a caso: il confronto (15 casi, tutti
    # uguali) è stato fatto a mano il 04/10/2026 e non sta nel limite della suite
    rng = random.Random(5)
    for _ in range(20):
        hands = random_hands(rng, 4, 4)
        trump = rng.choice(list(Suit))
        state = end_state(hands, 0, sings=((1, trump, 40),))
        fast = team_wins_all(tuple(frozenset(hand) for hand in state.hands), 0, 0, trump)
        assert fast == brute_wins_all(state, 0), (hands, trump)


def play_until_deck_empty(players, seed):
    """Partita a caso, con i canti, fino a ogni inizio presa a mazzo finito."""
    rng = random.Random(seed)
    state = new_hand(players, rng.randrange(players), shuffled_deck(rng))
    found = []
    while not state.finished:
        seat = state.turn_seat
        legal = legal_actions(state, seat)
        if not state.deck and not state.trick:
            found.append(state)
        if legal.sing and rng.random() < 0.7:
            state = apply(state, SingAction(seat, rng.choice(legal.sing)))
        else:
            state = apply(state, PlayCardAction(seat, rng.choice(legal.play)))
    return found


def expected_lay_down(state, seat):
    """Le condizioni di D45 scritte da capo, più il calcolo lento (nel 2v2 con 5 carte a testa,
    troppo lento per la suite, quello veloce, già confrontato con il lento qui sopra)."""
    if seat != state.turn_seat or state.deck or state.trick:
        return False
    if state.trump is None and max(len(hand) for hand in state.hands) > 2:
        return False

    def can_sing(other):
        return bool(singable_suits(hand=state.hands[other], sings=state.sings, played_cards=state.played_cards,
                                   deck_count=0, is_turn=True, first_trick=False))

    if can_sing(seat) or any(can_sing(other) for other in range(state.num_players) if other % 2 != seat % 2):
        return False
    if state.num_players == 4 and len(state.hands[seat]) == 5:
        return team_wins_all(tuple(frozenset(hand) for hand in state.hands), seat, seat % 2, state.trump)
    return brute_wins_all(state, seat % 2)


@pytest.mark.parametrize("players", [2, 4])
def test_lay_down_legale_esattamente_quando_valgono_le_condizioni(players):
    checked = allowed = 0
    for seed in range(120 if players == 2 else 40):
        for state in play_until_deck_empty(players, seed):
            for seat in range(players):
                assert legal_actions(state, seat).lay_down == expected_lay_down(state, seat)
                checked += 1
            allowed += legal_actions(state, state.turn_seat).lay_down
    assert checked > 100 and allowed > 5, (checked, allowed)


# --- Le condizioni di D45 ---------------------------------------------------------------

# 1v1, briscola bastoni: Asso di coppe e Tre di bastoni contro 2 di coppe e 4 di spade (l'esempio di D45)
WINNING = (["coppe-1", "bastoni-3"], ["coppe-2", "spade-4"])
TRUMP_BASTONI = ((1, BASTONI, 40),)


def test_l_esempio_di_d45():
    state = end_state(WINNING, 0, TRUMP_BASTONI)
    assert legal_actions(state, 0).lay_down
    assert not legal_actions(state, 1).lay_down  # non è il suo turno
    # Con la lettura "rigida" (chiunque apra) non si calerebbe: se l'avversario aprisse con il 4 di
    # spade, l'Asso di coppe non lo prenderebbe. Ma chi vince tutte le prese apre sempre lui (D45)
    rigid = end_state((WINNING[0], ["spade-4"]), 1, TRUMP_BASTONI)
    rigid = apply(rigid, PlayCardAction(1, card("spade-4")))
    assert trick_taken_by(rigid, 0, "coppe-1") == 1


def trick_taken_by(state, seat, code):
    return apply(state, PlayCardAction(seat, card(code))).last_trick.winner_seat


def test_una_briscola_piu_forte_dell_avversario_impedisce_di_calare():
    state = end_state((["coppe-1", "spade-2"], ["coppe-3", "bastoni-4"]), 0, ((1, SPADE, 40),))
    assert legal_actions(state, 0).lay_down
    state = end_state((["coppe-1", "spade-2"], ["coppe-3", "spade-4"]), 0, ((1, SPADE, 40),))
    assert not legal_actions(state, 0).lay_down  # il 4 di spade prende l'Asso o il 2 di spade


def test_solo_a_mazzo_finito():
    state = replace(end_state(WINNING, 0, TRUMP_BASTONI), deck=(card("denari-7"),))
    assert not legal_actions(state, 0).lay_down


def test_solo_a_inizio_presa():
    state = end_state((["coppe-1", "bastoni-3"], ["coppe-2", "spade-4", "spade-5"]), 1, TRUMP_BASTONI)
    state = apply(state, PlayCardAction(1, card("spade-5")))
    assert state.turn_seat == 0 and state.trick
    assert not legal_actions(state, 0).lay_down
    with pytest.raises(InvalidMoveError, match="Adesso non puoi calare le carte."):
        apply(state, LayDownAction(0))


def test_senza_briscola_solo_con_due_carte_o_meno():
    two = end_state((["coppe-1", "spade-1"], ["coppe-2", "spade-2"]), 0)
    assert two.trump is None and legal_actions(two, 0).lay_down
    one = end_state((["coppe-1"], ["coppe-2"]), 0)
    assert legal_actions(one, 0).lay_down  # anche con l'ultima carta
    three = end_state((["coppe-1", "spade-1", "denari-1"], ["coppe-2", "spade-2", "denari-2"]), 0)
    assert team_wins_all(tuple(frozenset(h) for h in three.hands), 0, 0, None)  # vincerebbe tutto...
    assert not legal_actions(three, 0).lay_down  # ...ma senza briscola con 3 carte non si cala


def test_chi_apre_canta_prima_tutti_i_suoi_semi():
    hands = (["denari-10", "denari-9", "bastoni-1"], ["coppe-2", "spade-4", "spade-5"])
    state = end_state(hands, 0, TRUMP_BASTONI)
    assert legal_actions(state, 0).sing == (DENARI,)
    assert not legal_actions(state, 0).lay_down
    sung = apply(state, SingAction(0, DENARI))
    assert sung.turn_seat == 0 and legal_actions(sung, 0).lay_down


def test_se_un_avversario_puo_cantare_non_si_cala():
    hands = (["bastoni-1", "bastoni-3", "denari-1"], ["coppe-10", "coppe-9", "spade-4"])
    state = end_state(hands, 0, ((0, BASTONI, 40),))
    assert team_wins_all(tuple(frozenset(h) for h in state.hands), 0, 0, BASTONI)
    assert not legal_actions(state, 0).lay_down
    # Con il Re di coppe già uscito l'avversario non canta più: si cala
    hands = (["bastoni-1", "bastoni-3", "denari-1"], ["coppe-2", "coppe-9", "spade-4"])
    assert legal_actions(end_state(hands, 0, ((0, BASTONI, 40),)), 0).lay_down


def test_fuori_turno_non_si_cala():
    state = end_state(WINNING, 0, TRUMP_BASTONI)
    with pytest.raises(NotYourTurnError):
        apply(state, LayDownAction(1))


# --- Cosa succede calando ---------------------------------------------------------------


def test_calando_la_mano_finisce_e_le_carte_vanno_a_chi_cala():
    state = end_state(WINNING, 0, TRUMP_BASTONI)
    before = [sum(c.points for c in taken) for taken in state.captured]
    done = apply(state, LayDownAction(0))
    assert done.finished and all(hand == () for hand in done.hands)
    assert done.laid_down.seat == 0 and done.laid_down.hands == state.hands and done.laid_down.sings == ()
    result = hand_result(done)
    # Asso di coppe 11 + Tre di bastoni 10 + 2 di coppe e 4 di spade (0)
    assert result.card_points == (before[0] + 21, before[1])
    assert sum(result.card_points) == 120
    assert result.laid_down == done.laid_down


def test_nel_2v2_il_compagno_canta_i_suoi_20():
    hands = (
        ["bastoni-1", "bastoni-3", "bastoni-10"],  # chi cala: le briscole più forti
        ["coppe-2", "spade-4", "spade-5"],
        ["denari-10", "denari-9", "coppe-4"],  # il compagno ha Re e Cavallo di denari
        ["coppe-5", "spade-6", "spade-7"],
    )
    state = end_state(hands, 0, ((0, BASTONI, 40),))
    assert legal_actions(state, 0).lay_down
    done = apply(state, LayDownAction(0))
    assert done.laid_down.sings == (Sing(2, DENARI, 20),)
    assert done.sings[-1] == Sing(2, DENARI, 20)
    assert hand_result(done).sing_points == (60, 0)


def test_nel_2v2_conta_anche_la_mano_del_compagno():
    # Briscola bastoni. Chi apre ha solo coppe; l'avversario che gioca per ultimo ha il 2 di bastoni.
    # Il compagno gioca prima di lui e, giocando bene, mette ogni volta una briscola più forte
    hands = [
        ["coppe-1", "coppe-3"],
        ["spade-1", "denari-2"],
        ["bastoni-1", "bastoni-3"],
        ["bastoni-2", "denari-4"],
    ]
    assert legal_actions(end_state(hands, 0, ((1, BASTONI, 40),)), 0).lay_down
    # Senza le briscole del compagno il 2 di bastoni prende una presa: non si cala
    hands[2] = ["coppe-4", "coppe-5"]
    assert not legal_actions(end_state(hands, 0, ((1, BASTONI, 40),)), 0).lay_down


def test_la_partita_va_avanti_dopo_la_calata():
    game = new_game(2, 500, rng=random.Random(1))
    game = replace(game, hand=end_state(WINNING, 0, TRUMP_BASTONI))
    after = apply_game(game, LayDownAction(0), rng=random.Random(2))
    assert after.hand_number == 2 and after.last_hand.laid_down is not None
    assert after.scores == hand_result(apply(game.hand, LayDownAction(0))).totals


# --- Vista, mossa automatica e CPU --------------------------------------------------------


def test_vista_prima_e_dopo_la_calata():
    game = new_game(2, 500, rng=random.Random(1))
    game = replace(game, hand=end_state(WINNING, 0, TRUMP_BASTONI))
    view = player_view(game, 0)
    assert view["legal"]["lay_down"] is True
    assert player_view(game, 1)["legal"]["lay_down"] is False
    # Prima della calata le carte dell'avversario non sono da nessuna parte nella vista
    text = json.dumps(view)
    for code in WINNING[1]:
        assert json.dumps(card_to_dict(card(code))) not in text
    after = apply_game(game, LayDownAction(0), rng=random.Random(2))
    for seat in (0, 1):
        laid = player_view(after, seat)["last_hand"]["laid_down"]
        assert laid == {
            "seat": 0,
            "hands": [
                {"seat": 0, "cards": [card_to_dict(card("coppe-1")), card_to_dict(card("bastoni-3"))]},
                {"seat": 1, "cards": [card_to_dict(card("coppe-2")), card_to_dict(card("spade-4"))]},
            ],
            "sings": [],
        }


def test_la_mossa_automatica_non_cala_mai():
    game = new_game(2, 500, rng=random.Random(1))
    game = replace(game, hand=end_state(WINNING, 0, TRUMP_BASTONI))
    assert legal_actions(game.hand, 0).lay_down
    assert isinstance(auto_move(game, random.Random(3)), PlayCardAction)


def test_la_cpu_cala_quando_puo():
    game = new_game(2, 500, rng=random.Random(1))
    game = replace(game, hand=end_state(WINNING, 0, TRUMP_BASTONI))
    assert cpu_move(player_view(game, 0), random.Random(3)) == LayDownAction(0)
    hands = (["denari-10", "denari-9", "bastoni-1"], ["coppe-2", "spade-4", "spade-5"])
    game = replace(game, hand=end_state(hands, 0, TRUMP_BASTONI))
    assert cpu_move(player_view(game, 0), random.Random(3)) == SingAction(0, DENARI)  # prima canta
