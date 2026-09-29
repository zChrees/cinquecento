"""P14: partita fino al punteggio scelto (150, 300, 500), pareggio, mazziere (D11).

Comando (finché P6 non aggiunge il runner): python -m pytest tests/engine
"""

import random
from dataclasses import replace

import pytest

from app.game.engine.actions import PlayCardAction, SingAction
from app.game.engine.cards import Card, Suit
from app.game.engine.deck import full_deck
from app.game.engine.errors import EngineError, InvalidMoveError
from app.game.engine.game import apply_game, game_legal_actions, new_game, new_hand
from app.game.engine.rules import MARIANNA
from app.game.engine.singing import singable_suits
from app.game.engine.trick import trick_winner

TARGETS = MARIANNA.target_scores
MODES = (2, 4)


def first_card_move(game):
    """Mossa fissa: la prima carta legale di chi è di turno, senza cantare."""
    seat = game.hand.turn_seat
    return PlayCardAction(seat, game_legal_actions(game, seat).play[0])


def random_move(game, rng):
    """Mossa a caso tra quelle legali, canti compresi."""
    seat = game.hand.turn_seat
    legal = game_legal_actions(game, seat)
    moves = [PlayCardAction(seat, card) for card in legal.play]
    moves += [SingAction(seat, suit) for suit in legal.sing]
    return rng.choice(moves)


def finish_hand(game):
    """Gioca la mano in corso fino alla fine con la mossa fissa."""
    number = game.hand_number
    while not game.finished and game.hand_number == number:
        game = apply_game(game, first_card_move(game), rng=random.Random(0))
    return game


def hand_totals(game):
    """Punti che la mano in corso darà a ogni squadra, giocata con la mossa fissa."""
    return finish_hand(game).last_hand.totals


def game_before_last_hand(target, scores_from_totals):
    """Partita 1v1 con i punteggi scelti in modo che la mano in corso li porti dove serve."""
    game = new_game(2, target, rng=random.Random(3))
    totals = hand_totals(game)
    assert all(points > 0 for points in totals)
    return replace(game, scores=scores_from_totals(totals))


# --- Inizio della partita ----------------------------------------------------------


@pytest.mark.parametrize("players", MODES)
@pytest.mark.parametrize("target", TARGETS)
def test_nuova_partita(players, target):
    game = new_game(players, target, rng=random.Random(1))
    assert game.num_players == players and game.target_score == target
    assert game.hand_number == 1
    assert game.scores == (0, 0)
    assert game.last_hand is None and game.result is None and not game.finished
    assert game.hand.turn_seat == game.hand.leader_seat == game.first_seat
    assert [len(cards) for cards in game.hand.hands] == [5] * players


@pytest.mark.parametrize("target", [0, 100, 149, 151, 499, 501, 1000, -300, "300", 300.0, True, None])
def test_punteggio_fuori_elenco_rifiutato(target):
    with pytest.raises(EngineError, match="Punteggio non valido: si gioca a 150, 300 o 500."):
        new_game(2, target, rng=random.Random(1))


@pytest.mark.parametrize("players", [0, 1, 3, 5, "2", None])
def test_numero_di_giocatori_non_valido(players):
    with pytest.raises(EngineError, match="2 o in 4"):
        new_game(players, 300, rng=random.Random(1))


@pytest.mark.parametrize("players", MODES)
def test_primo_giocatore_a_caso_e_mazziere_alla_sua_sinistra(players):
    firsts = set()
    for seed in range(40):
        game = new_game(players, 300, rng=random.Random(seed))
        # Stesso seme, stessa partita
        assert new_game(players, 300, rng=random.Random(seed)) == game
        firsts.add(game.first_seat)
        # Alla sinistra = il posto prima nell'ordine di gioco (i posti vanno verso destra)
        assert game.dealer_seat == (game.first_seat - 1) % players
    assert firsts == set(range(players))


def test_mazziere_nel_2v2_esempio():
    game = replace(new_game(4, 300, rng=random.Random(1)), first_seat=0)
    assert game.dealer_seat == 3
    assert replace(game, first_seat=2).dealer_seat == 1


def test_senza_seme_usa_il_caso_vero():
    game = new_game(2, 150)
    assert game.first_seat in (0, 1)


# --- Mano dopo mano ----------------------------------------------------------------


@pytest.mark.parametrize("players", MODES)
def test_seconda_mano_comincia_chi_sta_a_destra(players):
    game = new_game(players, 500, rng=random.Random(5))
    first = game.first_seat
    game = finish_hand(game)
    assert not game.finished
    assert game.hand_number == 2
    assert game.first_seat == (first + 1) % players
    # Il mazziere è chi aveva cominciato la mano prima
    assert game.dealer_seat == first
    assert game.hand.turn_seat == game.hand.leader_seat == game.first_seat
    assert [len(cards) for cards in game.hand.hands] == [5] * players
    assert len(game.hand.deck) == 40 - 5 * players
    assert game.hand.sings == () and game.hand.last_trick is None


def test_punti_della_mano_sommati_al_totale():
    game = new_game(2, 500, rng=random.Random(2))
    game = finish_hand(game)
    assert game.scores == game.last_hand.totals
    assert sum(game.last_hand.card_points) == 120
    before = game.scores
    game = finish_hand(game)
    assert game.scores == tuple(a + b for a, b in zip(before, game.last_hand.totals, strict=True))


def test_mossa_non_valida_lascia_la_partita_com_era():
    game = new_game(2, 150, rng=random.Random(4))
    other = 1 - game.hand.turn_seat
    card = game.hand.hands[other][0]
    with pytest.raises(InvalidMoveError):
        apply_game(game, PlayCardAction(other, card))
    assert game == new_game(2, 150, rng=random.Random(4))


# --- Fine della partita ------------------------------------------------------------


@pytest.mark.parametrize("target", TARGETS)
def test_con_n_esatti_si_vince(target):
    game = game_before_last_hand(target, lambda totals: (target - totals[0], 0))
    game = finish_hand(game)
    assert game.scores[0] == target
    assert game.finished
    assert game.result.winner_team == 0


@pytest.mark.parametrize("target", TARGETS)
def test_con_n_meno_uno_si_continua(target):
    game = game_before_last_hand(target, lambda totals: (target - totals[0] - 1, target - totals[1] - 1))
    game = finish_hand(game)
    assert game.scores == (target - 1, target - 1)
    assert not game.finished and game.result is None
    assert game.hand_number == 2


@pytest.mark.parametrize("target", TARGETS)
def test_se_ci_arrivano_entrambi_vince_il_piu_alto(target):
    game = game_before_last_hand(target, lambda totals: (target - totals[0], target - totals[1] + 10))
    game = finish_hand(game)
    assert game.scores == (target, target + 10)
    assert game.result.winner_team == 1


@pytest.mark.parametrize("target", TARGETS)
def test_a_parita_e_pareggio(target):
    game = game_before_last_hand(target, lambda totals: (target + 5 - totals[0], target + 5 - totals[1]))
    game = finish_hand(game)
    assert game.scores == (target + 5, target + 5)
    assert game.finished
    assert game.result.winner_team is None


@pytest.mark.parametrize("target", TARGETS)
def test_canto_che_porta_a_n_non_chiude_la_partita(target):
    # Mazzo in ordine: il posto 1 ha denari 6-10, cioè Cavallo e Re di denari
    game = new_game(2, target, rng=random.Random(1))
    game = replace(game, first_seat=1, hand=new_hand(2, 1, full_deck()), scores=(0, target - 40))
    # Nella prima presa non si canta (P64): il Fante del posto 1 batte il 2, e il posto 1 apre la seconda
    game = apply_game(game, PlayCardAction(1, Card.from_code("denari-8")))
    game = apply_game(game, PlayCardAction(0, Card.from_code("denari-2")))
    game = apply_game(game, SingAction(1, Suit.DENARI))
    assert game.hand.sings[0].points == 40
    assert game.scores == (0, target - 40)
    assert not game.finished
    assert game_legal_actions(game, 1).play  # si continua a giocare la mano
    game = finish_hand(game)
    assert game.finished
    assert game.result.winner_team == 1
    assert game.scores[1] >= target


@pytest.mark.parametrize("players", MODES)
def test_nella_prima_presa_di_ogni_mano_nessuno_canta(players):
    # P64: vale in ogni mano, non solo nella prima della partita. "blocked" conta le volte in cui,
    # dalla seconda mano in poi, chi è di turno nella prima presa avrebbe potuto cantare senza la regola
    blocked = 0
    for seed in range(40):
        rng = random.Random(seed)
        game = new_game(players, 500, rng=rng)
        while not game.finished and game.hand_number <= 3:
            hand, seat = game.hand, game.hand.turn_seat
            if hand.last_trick is None:
                assert game_legal_actions(game, seat).sing == ()
                blocked += game.hand_number > 1 and bool(singable_suits(
                    hand=hand.hands[seat], sings=hand.sings, played_cards=hand.played_cards,
                    deck_count=len(hand.deck), is_turn=True, first_trick=False))
            game = apply_game(game, random_move(game, rng), rng=rng)
    assert blocked > 0


def test_a_partita_finita_niente_mosse():
    game = finish_hand(game_before_last_hand(150, lambda totals: (150, 0)))
    assert game.finished
    assert game.hand.finished  # resta l'ultima mano, finita
    for seat in range(2):
        legal = game_legal_actions(game, seat)
        assert legal.play == () and legal.sing == ()
    with pytest.raises(InvalidMoveError, match="La partita è finita."):
        apply_game(game, PlayCardAction(0, full_deck()[0]))


# --- Ultima presa della mano (P58) -------------------------------------------------


@pytest.mark.parametrize("seed", range(5))
@pytest.mark.parametrize("players", MODES)
def test_il_riepilogo_tiene_l_ultima_presa_della_mano(players, seed):
    """La mano dopo parte con last_trick None: la presa che ha chiuso la mano resta in last_hand."""
    rng = random.Random(seed)
    game = new_game(players, 500, rng=rng)
    closed = 0
    while not game.finished:
        before = game
        move = random_move(game, rng)
        game = apply_game(game, move, rng=rng)
        if game.hand_number == before.hand_number and not game.finished:
            continue
        # La mossa ha chiuso la mano: l'ultima presa è quella in corso più la carta appena giocata
        last = game.last_hand.last_trick
        assert [(play.seat, play.card) for play in last.plays] == [
            *((play.seat, play.card) for play in before.hand.trick),
            (move.seat, move.card),
        ]
        assert len(last.plays) == players
        winner = trick_winner([play.card for play in last.plays], before.hand.trump)
        assert last.winner_seat == last.plays[winner].seat
        if not game.finished:
            assert game.hand.last_trick is None and game.hand.trick == ()
        else:
            assert game.hand.last_trick == last
        closed += 1
    assert closed == game.hand_number


# --- Partite intere ----------------------------------------------------------------


@pytest.mark.parametrize("seed", range(10))
@pytest.mark.parametrize("players", MODES)
@pytest.mark.parametrize("target", TARGETS)
def test_partita_intera(target, players, seed):
    rng = random.Random(seed)
    game = new_game(players, target, rng=rng)
    first = game.first_seat
    hands = 1
    while not game.finished:
        before = game
        game = apply_game(game, random_move(game, rng), rng=rng)
        if game.hand_number != before.hand_number or game.finished:
            # Qui è finita una mano: solo adesso i punteggi cambiano
            assert game.scores == tuple(
                a + b for a, b in zip(before.scores, game.last_hand.totals, strict=True)
            )
            if not game.finished:
                hands += 1
                assert game.hand_number == hands
                assert max(game.scores) < target
                assert game.first_seat == (first + hands - 1) % players
                assert game.dealer_seat == (game.first_seat - 1) % players
        else:
            assert game.scores == before.scores
    assert max(game.scores) >= target
    leaders = [team for team, score in enumerate(game.scores) if score == max(game.scores)]
    expected = leaders[0] if len(leaders) == 1 else None
    assert game.result.winner_team == expected
    assert game.hand_number == hands
