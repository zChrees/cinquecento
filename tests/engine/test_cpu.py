"""P68: mossa della CPU (D43). Vede solo la propria vista e quello che ricorda delle viste di prima.

Prima parte: il "giocatore medio" (heuristic_move, la prima CPU), che la strategia nuova usa
nelle mani immaginate; le situazioni si costruiscono a mano come viste del contratto (3.3).
Seconda parte: la strategia "simulazione" (cpu_move), con partite giocate con il motore vero.
Per andare veloci, quasi tutti i test riducono le mani immaginate (fixture quick).
Le prove di forza (contro il giocatore medio, 1v1 e 2v2) stanno nella suite forza (P122).
"""

import random
from dataclasses import replace

import pytest

from app.game.engine import cpu as cpu_module
from app.game.engine.actions import LayDownAction, PlayCardAction, SingAction
from app.game.engine.auto_move import auto_move
from app.game.engine.cards import Card, Rank, Suit
from app.game.engine.cpu import TRUMP_WORTH, CpuMemory, cpu_move, heuristic_move
from app.game.engine.deck import full_deck
from app.game.engine.errors import EngineError, InvalidMoveError
from app.game.engine.game import (
    apply,
    apply_game,
    game_legal_actions,
    legal_actions,
    new_game,
)
from app.game.engine.singing import Sing
from app.game.engine.state import HandState, LastTrick, TrickPlay
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


def test_mossa_rifiutata_se_la_vista_e_vecchia(quick):
    """La CPU sceglie dalla vista: una vista di un altro momento dà una mossa che il motore rifiuta."""
    rng = random.Random(4)
    game = new_game(2, 150, rng=rng)
    seat = game.hand.turn_seat
    old = player_view(game, seat)
    game = apply_game(game, auto_move(game, rng), rng=rng)
    with pytest.raises(InvalidMoveError):
        apply_game(game, cpu_move(old, random.Random(1)), rng=rng)


# --- Pari merito (P127, D50) ---------------------------------------------------------


def situation(players, seed, step):
    """Vista e memoria del posto 0 dopo `step` mosse di una partita giocata dal giocatore medio."""
    rng = random.Random(seed)
    game = new_game(players, 150, rng=rng)
    memories = {seat: CpuMemory() for seat in range(players)}
    for _ in range(step):
        for seat, memory in memories.items():
            memory.see(player_view(game, seat))
        game = apply_game(game, heuristic_move(player_view(game, game.hand.turn_seat), rng), rng=rng)
    for seat, memory in memories.items():
        memory.see(player_view(game, seat))
    assert game.hand.turn_seat == 0
    return player_view(game, 0), memories[0]


@pytest.mark.parametrize(("players", "seed", "step", "bad"), [
    # 2v2: il Tre di denari finiva agli avversari 16 volte su 20 con la CPU di prima
    (4, 2, 30, {"denari-3"}),
    # 2v2, inizio mano: Tre e Asso regalati o il Re di spade buttato 12 volte su 20
    (4, 0, 1, {"coppe-3", "denari-1", "spade-10"}),
    # 2v2 da ultima: un Cavallo ancora accoppiabile buttato 9 volte su 20
    (4, 1, 11, {"bastoni-9", "denari-9"}),
    # 1v1: Asso regalato o Cavallo buttato 10 volte su 20
    (2, 0, 24, {"coppe-1", "coppe-9", "spade-1"}),
    # 1v1 da ultima: il Cavallo di coppe buttato 5 volte su 20
    (2, 0, 29, {"coppe-9"}),
])
def test_a_pari_merito_non_regala_carichi_ne_butta_re_e_cavalli(quick, players, seed, step, bad):
    """Situazioni vere trovate il 10/10/2026: tra carte che valgono quasi uguale decideva il caso.

    Dipendono dai semi fissi, come la suite forza: se cambia il modo in cui motore o giocatore
    medio usano rng, la situazione cambia (il primo assert lo segnala).
    """
    view, memory = situation(players, seed, step)
    assert bad < {f"{card['suit']}-{card['rank']}" for card in view["legal"]["play"]}
    for attempt in range(20):
        move = cpu_move(view, random.Random(attempt), CpuMemory(memory.hand_number, set(memory.seen)))
        assert played(move) not in bad, (attempt, played(move))


def test_pari_merito_entro_due_volte_l_incertezza():
    # La prima mossa vale sempre 10 punti di più: nessun pari merito
    assert cpu_module._ties([[10, 0], [12, 2], [9, -1], [11, 1]]) == [0]
    # Distacco medio di mezzo punto con differenze di ±5: pari merito
    assert cpu_module._ties([[5, 0], [-5, 0], [6, 0], [-4, 0]]) == [0, 1]
    # Una mano sola (calcolo esatto): pari merito solo a valore uguale
    assert cpu_module._ties([[3, 3, 1]]) == [0, 1]


def table_view(hand, plays=(), players=2, trump=None, deck=10, sings=(), partner=None):
    """Vista per gli aiuti del pari merito: plays sono coppie (posto, carta) già sulla presa."""
    view = {
        "you": {"seat": 0},
        "players": [{"seat": seat, "team": seat % 2, "cards_in_hand": 5} for seat in range(players)],
        "hand": [card_to_dict(c(code)) for code in hand],
        "trick": {"leader_seat": plays[0][0] if plays else 0,
                  "cards": [{"seat": seat, "card": card_to_dict(c(code))} for seat, code in plays]},
        "trump": trump,
        "deck_count": deck,
        "sings": [{"seat": 1, "suit": suit, "points": 40} for suit in sings],
    }
    if partner is not None:
        view["partner_hand"] = [card_to_dict(c(code)) for code in partner]
    return view


def test_re_e_cavalli_accoppiabili():
    pairable = cpu_module._pairable
    empty = CpuMemory()
    # Il Cavallo di spade non è uscito e si può ancora pescare
    assert pairable(c("spade-10"), table_view(["spade-10", "denari-2"]), empty)
    # ... non se è uscito, se spade è già cantato o se la carta non si canta
    assert not pairable(c("spade-10"), table_view(["spade-10"]), CpuMemory(None, {c("spade-9")}))
    assert not pairable(c("spade-10"), table_view(["spade-10"], sings=["spade"]), empty)
    assert not pairable(c("spade-1"), table_view(["spade-1"]), empty)
    # Né se il Cavallo è scoperto in mano al compagno (con lui non si canta)
    assert not pairable(c("spade-10"), table_view(["spade-10"], players=4, partner=["spade-9"]), empty)
    # A mazzo finito serve averlo in mano e restare con almeno 3 carte
    assert not pairable(c("spade-10"), table_view(["spade-10", "denari-2", "coppe-4", "bastoni-5"], deck=0), empty)
    hand = ["spade-10", "spade-9", "coppe-4", "bastoni-5"]
    assert pairable(c("spade-10"), table_view(hand, deck=0), empty)
    assert not pairable(c("spade-10"), table_view(hand[:3], deck=0), empty)


def test_carico_al_sicuro_solo_se_nessuna_carta_non_vista_lo_batte():
    safe = cpu_module._safe_load
    view = table_view(["denari-1", "coppe-2"], plays=[(3, "denari-4")], players=4)
    # 2v2, secondo: l'Asso di denari sul 4 senza briscola non lo batte nessuno
    assert safe([(3, c("denari-4"))], c("denari-1"), 0, None, view, CpuMemory())
    # Con la briscola a coppe una coppe non vista lo prende
    assert not safe([(3, c("denari-4"))], c("denari-1"), 0, Suit.COPPE, view, CpuMemory())
    # Il Tre di denari è battuto dall'Asso, finché l'Asso non è uscito
    view = table_view(["denari-3", "coppe-2"], plays=[(3, "denari-4")], players=4)
    assert not safe([(3, c("denari-4"))], c("denari-3"), 0, None, view, CpuMemory())
    assert safe([(3, c("denari-4"))], c("denari-3"), 0, None, view, CpuMemory(None, {c("denari-1")}))
    # Una presa che resta agli avversari non è mai al sicuro
    assert not safe([(3, c("denari-1"))], c("denari-3"), 0, None, view, CpuMemory())


def test_da_ultima_gioca_il_risultato_migliore_nella_presa():
    preferred = cpu_module._preferred
    moves = [PlayCardAction(0, c(code)) for code in ("spade-1", "bastoni-2", "spade-7")]
    # 1v1: sul 4 di spade l'Asso prende 11 punti (P134 vale solo nel 2v2)
    view = table_view(["spade-1", "bastoni-2", "spade-7"], plays=[(1, "spade-4")])
    assert preferred(view, CpuMemory(), moves, [0, 0, 0]) == [moves[0]]
    # Sull'Asso di denari nessuna prende: la carta che dà meno punti, non di briscola, la più debole
    view = table_view(["spade-1", "bastoni-2", "spade-7"], plays=[(1, "denari-1")], trump="coppe")
    assert preferred(view, CpuMemory(), moves, [0, 0, 0]) == [moves[1]]


def test_da_ultima_niente_briscola_alta_su_una_presa_povera():
    """P134 (D51), solo nel 2v2: da ultima conta solo quello che la presa sposta, non i punti della sua carta."""
    preferred = cpu_module._preferred
    # Sul Fante di spade (2 punti) prende con la carta più bassa che basta: il Cavallo, non l'Asso
    moves = [PlayCardAction(0, c(code)) for code in ("spade-1", "spade-9", "bastoni-4")]
    plays = [(1, "spade-8"), (2, "spade-2"), (3, "spade-6")]
    view = table_view(["spade-1", "spade-9", "bastoni-4"], plays=plays, players=4)
    assert preferred(view, CpuMemory(None, {c("spade-10")}), moves, [0, 0, 0]) == [moves[1]]
    # Nel 1v1 resta P127: l'Asso, che con la sua carta "vale" di più
    view = table_view(["spade-1", "spade-9", "bastoni-4"], plays=[(1, "spade-8")])
    assert preferred(view, CpuMemory(None, {c("spade-10")}), moves, [0, 0, 0]) == [moves[0]]
    moves = [PlayCardAction(0, c(code)) for code in ("denari-1", "denari-3", "denari-5", "coppe-2")]
    hand = ["denari-1", "denari-3", "denari-5", "coppe-2"]
    # 2v2 da ultima, briscola denari, presa da 0 punti degli avversari: scarta la cartina
    plays = [(1, "spade-4"), (2, "spade-2"), (3, "spade-6")]
    view = table_view(hand, plays=plays, players=4, trump="denari")
    assert preferred(view, CpuMemory(), moves, [0, 0, 0, 0]) == [moves[3]]
    # Con 3 punti sulla presa prende, con la briscola più bassa
    plays = [(1, "spade-10"), (2, "spade-2"), (3, "spade-6")]
    view = table_view(hand, plays=plays, players=4, trump="denari")
    assert preferred(view, CpuMemory(None, {c("spade-9")}), moves, [0, 0, 0, 0]) == [moves[2]]


def test_costretta_sacrifica_il_re_e_tiene_il_carico():
    # 2v2, secondo dopo un avversario: Asso di coppe che può finire agli avversari o Re di spade
    # ancora accoppiabile: gioca il Re, anche se la stima del carico è un po' più alta
    view = table_view(["coppe-1", "spade-10"], plays=[(3, "denari-4")], players=4, trump="denari")
    moves = [PlayCardAction(0, c("coppe-1")), PlayCardAction(0, c("spade-10"))]
    assert cpu_module._preferred(view, CpuMemory(), moves, [5, 3]) == [moves[1]]


def test_calcolo_esatto_nel_2v2_a_mazzo_finito_con_poche_carte():
    def players_with(count, cards):
        return [{"seat": seat, "team": seat % 2, "cards_in_hand": cards} for seat in range(count)]
    assert cpu_module._exact_worlds({"players": players_with(4, 3), "deck_count": 0})
    assert not cpu_module._exact_worlds({"players": players_with(4, 4), "deck_count": 0})
    assert not cpu_module._exact_worlds({"players": players_with(4, 3), "deck_count": 4})
    # Nel 1v1 a mazzo finito c'è già una mano sola, calcolata in modo esatto
    assert not cpu_module._exact_worlds({"players": players_with(2, 3), "deck_count": 0})


def test_passo_del_calcolo_esatto_uguale_alla_differenza_dei_punti():
    """_step_gain (P127) conta solo le carte prese e i canti nuovi: deve dare quanto _gain."""
    for players in (2, 4):
        rng = random.Random(players)
        state = new_game(players, 500, rng=rng).hand
        while not state.finished:
            after = apply(state, cpu_module._policy(state, rng))
            for seat in range(players):
                expected = cpu_module._gain(after, seat) - cpu_module._gain(state, seat)
                assert cpu_module._step_gain(state, after, seat) == expected
            state = after


# --- Prese povere (P134, D51) ---------------------------------------------------------

SHORT = {"d": "denari", "c": "coppe", "s": "spade", "b": "bastoni"}


def cards(codes):
    """Carte scritte corte: "d3 b10" = 3 di denari, Re di bastoni."""
    return tuple(c(f"{SHORT[code[0]]}-{code[1:]}") for code in codes.split())


def poor_trick(hands, trick, leader, sings, last, gone):
    """Vista e memoria di chi è di turno, dalla mano salvata (2v2, briscola già cantata).

    gone: le carte delle prese chiuse; il mazzo sono le carte che restano. La CPU non usa i
    posti dell'ultima presa (né la squadra che ha preso le carte uscite), quindi sono di comodo.
    """
    players = len(hands)
    hands = tuple(cards(cards_of) for cards_of in hands)
    on_table, gone = cards(trick), cards(gone)
    used = {*on_table, *gone, *(card for cards_of in hands for card in cards_of)}
    turn = (leader + len(on_table)) % players
    state = HandState(
        num_players=players, hands=hands, deck=tuple(card for card in full_deck() if card not in used),
        trick=tuple(TrickPlay((leader + index) % players, card) for index, card in enumerate(on_table)),
        leader_seat=leader, turn_seat=turn,
        sings=tuple(Sing(int(done[0]), Suit(SHORT[done[1]]), int(done[2:])) for done in sings.split()),
        captured=(gone, ()),
        last_trick=None if last is None else LastTrick(
            leader, tuple(TrickPlay((leader + index) % players, card) for index, card in enumerate(cards(last)))),
    )
    view = player_view(replace(new_game(players, 150, rng=random.Random(0)), hand=state), turn)
    return view, CpuMemory(view["hand_number"], {*gone, *on_table})


# Situazioni vere delle prove del 10/10/2026 (riepilogo di christian.md): 140 partite 2v2 con
# il posto 0 giocatore medio e i posti 1-3 CPU con il calcolo vero, rigiocate con il cpu.py
# di P127 e salvate nel momento in cui la CPU giocava la carta sbagliata (ultimo campo):
# Asso o Tre di briscola su una presa povera, o la briscola più alta. Rigiocarle con il seme
# non basta: con il cpu.py nuovo la partita prende un'altra strada prima di arrivarci.
# Fuori il caso del seme 3, posto 3, 3° nella presa: presa da 13 punti, sbaglia la stima.
POOR_TRICKS = [
    # seme 0, posto 3, 4° nella presa, 16 carte nel mazzo, presa da 4 punti
    ('seme0-posto3', ('s1 c6 c8 d7', 'b10 s7 d9 s10', 'd5 s9 s5 s2', 'b7 c7 b5 b6 d3'),
     'c2 d10 c5', 0, '1d40', 'd2 s6 s4 b4',
     'd2 s6 s4 b4', 'd3'),
    # seme 7, posto 1, 4° nella presa, 16 carte nel mazzo, presa da 4 punti
    ('seme7-posto1-4a', ('d6 s3 s1 s8', 'c7 c1 c6 b6 c8', 's5 d9 c10 c9', 'c3 b9 b3 b1'),
     'b7 b4 b10', 2, '2c40', 'd1 s2 c5 c2',
     'd1 s2 c5 c2', 'c1'),
    # seme 19, posto 1, 3° nella presa, 8 carte nel mazzo, presa da 3 punti
    ('seme19-posto1', ('c8 d1 s8 d9', 'd5 s7 s1 b7 c10', 'c7 b9 b6 c4 d10', 'b1 d3 b8 d4'),
     's9 d6', 3, '3s40', 'c6 c1 s5 s10',
     's2 b5 d2 d7 c5 b2 c2 s4 c6 c1 s5 s10', 's1'),
    # seme 20, posto 1, 4° nella presa, 12 carte nel mazzo, presa da 3 punti
    ('seme20-posto1', ('d9 s10 b10 b9', 'd8 c2 b3 d1 c6', 'c3 d10 s3 s9', 'd3 c10 s4 c5'),
     'c4 s2 c9', 2, '0b40', 'b8 b1 s5 s6',
     'b8 b1 s5 s6 c8 b5 s8 d6', 'b3'),
    # seme 22, posto 2, 4° nella presa, 16 carte nel mazzo, presa da 2 punti
    ('seme22-posto2', ('d7 b3 c3 s10', 'b10 s8 b7 c4', 's6 s5 d3 d4 s4', 'd10 d9 s1 c9'),
     'b5 b8 s7', 3, '3d40', 'd5 c7 d1 b6',
     'd5 c7 d1 b6', 'd3'),
    # seme 24, posto 2, 3° nella presa, 16 carte nel mazzo, presa da 0 punti
    ('seme24-posto2', ('b5 d3 b8 s6', 'c9 c2 c10 c7', 'b10 b1 s3 c6 c1', 'd8 b3 s10 d10 s9'),
     's2 d2', 0, '1c40', 'c4 b9 s7 s8',
     'c4 b9 s7 s8', 'c1'),
    # seme 25, posto 3, 4° nella presa, 8 carte nel mazzo, presa da 2 punti
    ('seme25-posto3', ('c9 d8 c3 s10', 'c10 b7 b10 b6', 'd9 d7 c5 b1', 's1 d1 d3 b3 c4'),
     'c8 s7 d4', 0, '1b40 2d20', 's8 d10 s2 b2',
     's8 d10 s2 b2 c1 d2 c7 d6 b9 d5 b8 s6', 'b3'),
    # seme 25, posto 2, 4° nella presa, 4 carte nel mazzo, presa da 3 punti
    ('seme25-posto2', ('d8 c3 s10 s5', 'c10 b7 b10 b6', 'd9 d7 c5 b1 s3', 's1 d1 d3 s4'),
     'c4 c9 c2', 3, '1b40 2d20', 'c8 s7 d4 b3',
     's8 d10 s2 b2 c1 d2 c7 d6 b9 d5 b8 s6 c8 s7 d4 b3', 'b1'),
    # seme 40, posto 3, 4° nella presa, 16 carte nel mazzo, presa da 0 punti
    ('seme40-posto3-4a', ('b5 d10 c3 d7', 's8 s2 b7 s1', 'b9 b10 s5 d2', 'c1 b3 b1 c10 d5'),
     'd4 c2 s6', 0, '2b40', 'd6 d8 b6 b2',
     'd6 d8 b6 b2', 'b1'),
    # seme 40, posto 3, 3° nella presa, 8 carte nel mazzo, presa da 0 punti
    ('seme40-posto3-3a', ('b5 d10 c3 c7 c8', 's8 s1 d1 c5', 'b9 b10 s5 s4', 'c1 b3 c10 s10 s9'),
     's2 s7', 1, '2b40 3s20', 'd5 d7 b7 d2',
     'd6 d8 b6 b2 d4 c2 s6 b1 d5 d7 b7 d2', 'b3'),
    # seme 43, posto 2, 4° nella presa, 16 carte nel mazzo, presa da 0 punti
    ('seme43-posto2', ('b8 b5 b7 d1', 's9 c7 c9 b3', 'c3 s3 d2 b1 b6', 'b9 c1 s7 b10'),
     'b2 s4 d6', 3, '3b40', 'c2 c4 c6 d4',
     'c2 c4 c6 d4', 'b1'),
    # seme 43, posto 1, 4° nella presa, 12 carte nel mazzo, presa da 0 punti
    ('seme43-posto1', ('b8 b7 d1 s10', 's9 c7 c9 b3 b4', 'c3 s3 d2 d10', 'b9 c1 b10 d7'),
     'b6 s7 b5', 2, '3b40', 'b2 s4 d6 b1',
     'b2 s4 d6 b1 c2 c4 c6 d4', 'b3'),
    # seme 44, posto 3, 4° nella presa, 12 carte nel mazzo, presa da 0 punti
    ('seme44-posto3', ('s8 b8 c8 s1', 's9 c10 d9 d10', 'c6 d5 s7 d6', 'd3 b7 s2 s10 b1'),
     'c7 b6 s4', 0, '1d40', 'c3 d7 s6 s3',
     'c3 d7 s6 s3 c1 b2 b3 c4', 'd3'),
    # seme 29, posto 1, 4° nella presa, 16 carte nel mazzo, presa da 0 punti
    ('seme29-posto1', ('s5 d1 b1 c6', 'b5 d5 d9 d10 d3', 'c3 b6 s10 c10', 'b7 s9 c8 c1'),
     's2 d7 s4', 2, '1d40', 'b4 c7 b8 c4',
     'b4 c7 b8 c4', 'd3'),
    # seme 1, posto 1, 4° nella presa, 8 carte nel mazzo, presa da 0 punti
    ('seme1-posto1', ('s6 d6 c6 d9', 's9 b10 s10 c4 b3', 'b7 b1 d7 c10', 's3 c3 d3 s4'),
     's5 c7 b4', 2, '1s40', 'b5 b2 s7 s8',
     'd4 d5 d10 c5 b5 b2 s7 s8 c2 b6 d2 c1', 's10'),
    # seme 2, posto 1, 4° nella presa, 0 carte nel mazzo, presa da 14 punti
    ('seme2-posto1', ('s3 s10 s1', 'b8 c5 d3 d1', 'd4 b4 d2', 'b3 d10 d9'),
     's7 b1 s9', 2, '3d40 3b20 0s20', 's4 d8 b9 b7',
     'c2 c6 b5 c3 s4 d8 b9 b7 d7 c4 s8 s2 d5 s5 d6 b2 c7 c8 c9 c1 c10 s6 b10 b6', 'd1'),
    # seme 3, posto 3, 4° nella presa, 4 carte nel mazzo, presa da 13 punti
    ('seme3-posto3', ('c10 d8 b3 b10', 's10 c7 s3 c2', 's2 c1 b5 s9', 'd1 d7 d10 b1 d9'),
     's6 s8 s1', 0, '3d40', 'd5 c4 d6 b7',
     'c8 d4 c9 b4 b6 c6 s5 b8 d5 c4 d6 b7 c5 s7 d2 c3', 'd1'),
    # seme 4, posto 1, 4° nella presa, 0 carte nel mazzo, presa da 5 punti
    ('seme4-posto1', ('s9', 'd3 d7', 'c10', 'b1'),
     'b2 b9 s8', 2, '0d40', 's6 s3 d5 b8',
     'c5 c4 d4 c6 b5 b3 s5 c1 d8 d9 c9 c3 d10 s10 b4 c7 s6 s3 d5 b8 s4 c2 b7 s1 b6 b10 s2 d1 d2 c8 d6 s7', 'd3'),
    # seme 7, posto 2, 4° nella presa, 8 carte nel mazzo, presa da 5 punti
    ('seme7-posto2-4a', ('s3 s1 s9 d3', 'c7 c6 c8 d2', 's5 d9 c10 c9 c4', 'b3 b1 s10 b2'),
     'b9 s8 b6', 3, '2c40', 's7 d8 c3 d6',
     'd1 s2 c5 c2 b7 b4 b10 c1 s7 d8 c3 d6', 'c10'),
    # seme 7, posto 1, 3° nella presa, 0 carte nel mazzo, presa da 0 punti
    ('seme7-posto1-3a', ('s3 s1 d3', 'c7 c6 c8 b5', 'd9 c9 c4 s6', 'b3 b1 s10'),
     'b2 d7', 3, '2c40', 'd5 d4 b8 d10',
     'd1 s2 c5 c2 b9 s8 b6 c10 s5 s4 s9 d2 b7 b4 b10 c1 s7 d8 c3 d6 d5 d4 b8 d10', 'c8'),
    # seme 7, posto 2, 2° nella presa, 0 carte nel mazzo, presa da 0 punti
    ('seme7-posto2-2a', ('c3 c10 b3 s3', 'c1 c9 d1', 's10 s4 s1 s9', 's5 d3 b7 b5'),
     's6', 1, '2s40', 'd6 c7 d10 c6',
     'd7 d9 c4 d8 d4 c8 s7 d5 s2 b4 c5 s8 b8 b9 b10 d2 b2 c2 b6 b1 d6 c7 d10 c6', 's1'),
]


@pytest.mark.parametrize(("hands", "trick", "leader", "sings", "last", "gone", "bad"),
                         [case[1:] for case in POOR_TRICKS], ids=[case[0] for case in POOR_TRICKS])
def test_a_pari_merito_niente_carichi_ne_briscole_alte_su_prese_povere(hands, trick, leader, sings, last, gone, bad):
    """Con tutte le carte a pari merito la CPU non sceglie più la carta sbagliata (P127 la sceglieva)."""
    view, memory = poor_trick(hands, trick, leader, sings, last, gone)
    seat = view["you"]["seat"]
    moves = [PlayCardAction(seat, cpu_module._card(card)) for card in view["legal"]["play"]]
    assert cards(bad)[0] in {move.card for move in moves}
    chosen = cpu_module._preferred(view, memory, moves, [0] * len(moves))
    assert cards(bad)[0] not in {move.card for move in chosen}, [str(move.card) for move in chosen]


@pytest.mark.parametrize("ident", ["seme2-posto1", "seme4-posto1", "seme7-posto1-4a", "seme40-posto3-4a"])
def test_con_il_calcolo_vero_niente_carichi_ne_briscole_alte_su_prese_povere(ident):
    """La mossa intera, con il calcolo vero (circa 0,3 s): casi in cui P127 sbagliava 10 volte su 10."""
    case = next(case for case in POOR_TRICKS if case[0] == ident)
    view, memory = poor_trick(*case[1:-1])
    for attempt in range(3):
        move = cpu_move(view, random.Random(attempt), CpuMemory(memory.hand_number, set(memory.seen)))
        assert move.card != cards(case[-1])[0], (attempt, str(move.card))


def test_non_da_ultima_la_briscola_piu_bassa_su_una_presa_povera():
    """P134 (D51): secondo nel 2v2, briscola denari, presa da meno di TRUMP_WORTH punti."""
    preferred = cpu_module._preferred
    hand = ["denari-1", "denari-7", "denari-5", "coppe-2"]
    moves = [PlayCardAction(0, c(code)) for code in hand]
    view = table_view(hand, plays=[(3, "coppe-4")], players=4, trump="denari")
    # L'Asso di briscola non lo batte nessuno, ma su una presa da 0 è sprecato; il 7 è più del necessario
    assert preferred(view, CpuMemory(), moves, [9, 7, 5, 5]) == [moves[2], moves[3]]
    # Su una presa che vale (Asso di coppe, 11 punti) l'Asso di briscola al sicuro va bene
    view = table_view(hand, plays=[(3, "coppe-1")], players=4, trump="denari")
    assert preferred(view, CpuMemory(), moves, [9, 7, 5, 5]) == [moves[0]]
