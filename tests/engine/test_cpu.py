"""P68: mossa della CPU (D43). Vede solo la propria vista e quello che ricorda delle viste di prima.

Prima parte: il "giocatore medio" (heuristic_move, la prima CPU), che la strategia nuova usa
nelle mani immaginate; le situazioni si costruiscono a mano come viste del contratto (3.3).
Seconda parte: la strategia "simulazione" (cpu_move), con partite giocate con il motore vero.
Per andare veloci, quasi tutti i test riducono le mani immaginate (fixture quick).
"""

import random
from dataclasses import replace

import pytest

from app.game.engine import cpu as cpu_module
from app.game.engine.actions import LayDownAction, PlayCardAction, SingAction
from app.game.engine.auto_move import auto_move
from app.game.engine.cards import Card, Rank, Suit
from app.game.engine.cpu import TRUMP_WORTH, CpuMemory, cpu_move, heuristic_move
from app.game.engine.errors import EngineError, InvalidMoveError
from app.game.engine.game import (
    apply,
    apply_game,
    game_legal_actions,
    legal_actions,
    new_game,
)
from app.game.engine.views import card_to_dict, player_view


def c(code):
    suit, rank = code.split("-")
    return Card(Suit(suit), Rank(int(rank)))


def view(hand, trick=(), trump=None, deck=10, sings=(), can_sing=(), seat=0):
    """Vista minima del contratto per la CPU al posto `seat`, di turno: gioca tutto quello che ha."""
    cards = [card_to_dict(c(code)) for code in hand]
    plays = [{"seat": 1 - seat, "card": card_to_dict(c(code))} for code in trick]
    return {
        "you": {"seat": seat},
        "hand": cards,
        "trick": {"leader_seat": 1 - seat if trick else seat, "cards": plays},
        "trump": trump,
        "deck_count": deck,
        "sings": [{"seat": 1, "suit": suit, "points": 40} for suit in sings],
        "legal": {"play": cards, "sing": list(can_sing), "lay_down": False},
    }


def played(action):
    assert isinstance(action, PlayCardAction)
    return action.card.code


# --- Canti --------------------------------------------------------------------------


def test_canta_appena_puo():
    action = heuristic_move(view(["coppe-10", "coppe-9", "denari-2"], can_sing=["coppe"]), random.Random(1))
    assert action == SingAction(0, Suit.COPPE)


def test_canta_il_seme_con_piu_carte():
    hand = ["coppe-10", "coppe-9", "spade-10", "spade-9", "spade-1"]
    action = heuristic_move(view(hand, can_sing=["coppe", "spade"]), random.Random(1))
    assert action == SingAction(0, Suit.SPADE)


# --- Risposta -----------------------------------------------------------------------


def test_prende_con_la_carta_piu_economica_senza_briscola():
    # Sul 4 di denari: il Fante (2 punti) basta, l'Asso sarebbe sprecato
    hand = ["denari-1", "denari-8", "spade-2"]
    assert played(heuristic_move(view(hand, trick=["denari-4"], trump="coppe"), random.Random(1))) == "denari-8"


def test_prende_anche_una_presa_senza_punti_se_non_costa_briscola():
    hand = ["denari-5", "spade-2", "bastoni-4"]
    assert played(heuristic_move(view(hand, trick=["denari-4"], trump="coppe"), random.Random(1))) == "denari-5"


def test_briscola_solo_su_una_presa_che_vale():
    hand = ["coppe-2", "spade-4", "bastoni-10"]
    # Sull'Asso di denari (11 punti) prende con la briscola più piccola
    assert played(heuristic_move(view(hand, trick=["denari-1"], trump="coppe"), random.Random(1))) == "coppe-2"
    # Sul Re di denari (4 punti) no: scarta la carta che vale meno
    assert played(heuristic_move(view(hand, trick=["denari-10"], trump="coppe"), random.Random(1))) == "spade-4"
    assert TRUMP_WORTH == 10


def test_a_mazzo_finito_briscola_su_qualunque_presa_con_punti():
    hand = ["coppe-2", "spade-4"]
    move = heuristic_move(view(hand, trick=["denari-8"], trump="coppe", deck=0), random.Random(1))
    assert played(move) == "coppe-2"
    # Su una presa senza punti non spreca la briscola
    move = heuristic_move(view(hand, trick=["denari-4"], trump="coppe", deck=0), random.Random(1))
    assert played(move) == "spade-4"


def test_se_non_puo_prendere_scarta_la_carta_che_vale_meno():
    hand = ["spade-1", "bastoni-3", "bastoni-6", "coppe-2"]
    move = heuristic_move(view(hand, trick=["denari-1"], trump="coppe"), random.Random(1))
    # coppe-2 prenderebbe l'Asso di denari (briscola); tolto quello, bastoni-6 costa meno
    assert played(move) == "coppe-2"
    move = heuristic_move(view(["spade-1", "bastoni-3", "bastoni-6"], trick=["denari-1"], trump="coppe"),
                    random.Random(1))
    assert played(move) == "bastoni-6"


def test_carte_franche_nessuna_briscola():
    hand = ["spade-1", "bastoni-6"]
    move = heuristic_move(view(hand, trick=["denari-3"], trump=None), random.Random(1))
    assert played(move) == "bastoni-6"


# --- Apertura -----------------------------------------------------------------------


def test_apre_con_la_carta_che_vale_meno_e_tiene_la_briscola():
    hand = ["denari-1", "coppe-2", "spade-3", "bastoni-7"]
    assert played(heuristic_move(view(hand, trump="coppe"), random.Random(1))) == "bastoni-7"


def test_a_mazzo_finito_apre_con_la_briscola_piu_forte():
    hand = ["coppe-2", "coppe-1", "spade-6"]
    assert played(heuristic_move(view(hand, trump="coppe", deck=0), random.Random(1))) == "coppe-1"


def test_non_rompe_una_coppia_da_cantare():
    # Re e Cavallo di spade non ancora cantati: apre con il Fante di bastoni (2 punti)
    hand = ["spade-10", "spade-9", "bastoni-8"]
    assert played(heuristic_move(view(hand, trump="coppe"), random.Random(1))) == "bastoni-8"
    # Se spade è già stato cantato la coppia non conta più: gioca il Cavallo (3 punti) prima del Re
    hand = ["spade-10", "spade-9", "bastoni-1"]
    assert played(heuristic_move(view(hand, trump="coppe", sings=["spade"]), random.Random(1))) == "spade-9"


def test_non_e_il_suo_turno():
    empty = view(["spade-1"])
    empty["legal"] = {"play": [], "sing": [], "lay_down": False}
    with pytest.raises(EngineError, match="Non è il turno della CPU."):
        heuristic_move(empty)


# --- Strategia "simulazione" (D43) ------------------------------------------------


@pytest.fixture
def quick(monkeypatch):
    """Meno mani immaginate: la CPU pensa in pochi millesimi invece di 0,2 s."""
    monkeypatch.setattr(cpu_module, "SIMULATED_PLAYS", 600)
    monkeypatch.setattr(cpu_module, "MIN_WORLDS", 4)


def play_game(players, seed, chooser, target=150):
    """Partita intera: chooser(game, seat, rng, memories) dà la mossa; restituisce la partita finita.

    memories: posto -> CpuMemory, che vede ogni vista nuova del suo posto, come fa la stanza.
    """
    rng = random.Random(seed)
    game = new_game(players, target, rng=rng)
    memories = {seat: CpuMemory() for seat in range(players)}
    while not game.finished:
        for seat, memory in memories.items():
            memory.see(player_view(game, seat))
        game = apply_game(game, chooser(game, game.hand.turn_seat, rng, memories), rng=rng)
    return game


def cpu(game, seat, rng, memories):
    return cpu_move(player_view(game, seat), rng, memories[seat])


@pytest.mark.parametrize("seed", range(4))
@pytest.mark.parametrize("players", (2, 4))
def test_la_cpu_gioca_solo_mosse_legali_fino_alla_fine(quick, players, seed):
    """Ogni mossa della CPU è tra quelle legali e la partita finisce."""
    def checked(game, seat, rng, memories):
        action = cpu(game, seat, rng, memories)
        legal = game_legal_actions(game, seat)
        if isinstance(action, SingAction):
            assert action.suit in legal.sing
        elif isinstance(action, LayDownAction):
            assert legal.lay_down
        else:
            assert action.card in legal.play and not legal.sing  # se può cantare, canta
        return action

    assert play_game(players, seed, checked).finished


@pytest.mark.parametrize("players", (2, 4))
def test_la_memoria_ha_tutte_le_carte_uscite(quick, players):
    """Dalle sole viste la CPU ricorda esattamente le carte già giocate nella mano."""
    checked = 0

    def checking(game, seat, rng, memories):
        nonlocal checked
        assert memories[seat].seen == set(game.hand.played_cards)
        checked += 1
        return cpu(game, seat, rng, memories)

    play_game(players, 3, checking)
    assert checked > 40


def test_la_cpu_non_vede_le_carte_nascoste(quick):
    """Stessa vista e stessa memoria, carte nascoste diverse (mano dell'avversario e mazzo scambiati): stessa mossa."""
    rng = random.Random(3)
    game = new_game(2, 150, rng=rng)
    memory = CpuMemory()
    while game.hand.turn_seat != 0 or not game.hand.trick or game.hand.last_trick is None:
        memory.see(player_view(game, 0))
        game = apply_game(game, auto_move(game, rng), rng=rng)
    memory.see(player_view(game, 0))
    hand = game.hand
    other, deck = list(hand.hands[1]), list(hand.deck)
    other[0], deck[0] = deck[0], other[0]
    hidden = replace(game, hand=replace(hand, hands=(hand.hands[0], tuple(other)), deck=tuple(deck)))
    assert player_view(hidden, 0) == player_view(game, 0)

    def move(state):
        return cpu_move(player_view(state, 0), random.Random(9), CpuMemory(memory.hand_number, set(memory.seen)))

    assert move(hidden) == move(game)


def test_senza_memoria_gioca_da_giocatore_medio():
    """Se la memoria non torna con la vista (la CPU non ha visto l'inizio della mano), gioca da giocatore medio."""
    rng = random.Random(5)
    game = new_game(2, 150, rng=rng)
    for _ in range(9):
        game = apply_game(game, auto_move(game, rng), rng=rng)
    view = player_view(game, game.hand.turn_seat)
    if view["legal"]["sing"]:
        pytest.skip("qui canta: la scelta del seme non passa dal giocatore medio")
    assert cpu_move(view, random.Random(1), CpuMemory()) == heuristic_move(view, random.Random(1))


def best_by_brute_force(hand_state, seat):
    """Lento e sicuro: il miglior guadagno della squadra della CPU giocando ogni sequenza con il motore.

    Come il calcolo esatto della CPU, chi può cantare canta (un seme alla volta, in ogni ordine).
    """
    def points(state):
        values = [sum(c.points for c in taken) for taken in state.captured]
        for done in state.sings:
            values[done.seat % 2] += done.points
        return values[seat % 2] - values[1 - seat % 2]

    def value(state):
        if state.finished:
            return points(state)
        turn = state.turn_seat
        legal = legal_actions(state, turn)
        moves = [SingAction(turn, s) for s in legal.sing] or [PlayCardAction(turn, c) for c in legal.play]
        results = [value(apply(state, m)) for m in moves]
        return max(results) if turn % 2 == seat % 2 else min(results)

    return value(hand_state)


@pytest.mark.parametrize("seed", range(2))
def test_a_mazzo_finito_sceglie_la_mossa_migliore(seed):
    """1v1 a mazzo finito: tutte le carte sono note e la mossa scelta vale quanto la migliore."""
    rng = random.Random(seed)
    game = new_game(2, 500, rng=rng)
    memories = {0: CpuMemory(), 1: CpuMemory()}
    while game.hand.deck or game.hand.trick:
        for s, memory in memories.items():
            memory.see(player_view(game, s))
        game = apply_game(game, auto_move(game, rng), rng=rng)
    for s, memory in memories.items():
        memory.see(player_view(game, s))
    seat = game.hand.turn_seat
    view = player_view(game, seat)
    if view["legal"]["lay_down"]:
        pytest.skip("qui la CPU cala: non c'è una carta da scegliere")
    action = cpu_move(view, random.Random(1), memories[seat])
    best = best_by_brute_force(game.hand, seat)
    assert best_by_brute_force(apply(game.hand, action), seat) == best


def test_la_cpu_batte_il_giocatore_medio(monkeypatch):
    """D43, "Fatto quando": batte la prima CPU in gran parte delle partite.

    Qui pensa un terzo del vero, per stare nei tempi della suite: il 04/10/2026 con un terzo
    ha vinto 28 partite su 40, con il budget vero 81 su 100. Qui 12 partite, per i tempi della suite. Con meno ancora (600, minimo 4
    mani) perdeva: le mani immaginate sono troppo poche.
    """
    monkeypatch.setattr(cpu_module, "SIMULATED_PLAYS", 1500)
    monkeypatch.setattr(cpu_module, "MIN_WORLDS", 8)
    wins = 0
    for seed in range(12):
        mine = seed % 2  # metà delle partite da un posto, metà dall'altro

        def mixed(game, seat, rng, memories, mine=mine):
            if seat == mine:
                return cpu(game, seat, rng, memories)
            return heuristic_move(player_view(game, seat), rng)

        game = play_game(2, seed, mixed)
        wins += game.result.winner_team == mine
    assert wins >= 8, wins


def test_mossa_rifiutata_se_la_vista_e_vecchia(quick):
    """La CPU sceglie dalla vista: una vista di un altro momento dà una mossa che il motore rifiuta."""
    rng = random.Random(4)
    game = new_game(2, 150, rng=rng)
    seat = game.hand.turn_seat
    old = player_view(game, seat)
    game = apply_game(game, auto_move(game, rng), rng=rng)
    with pytest.raises(InvalidMoveError):
        apply_game(game, cpu_move(old, random.Random(1)), rng=rng)
