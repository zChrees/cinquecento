"""P68: mossa della CPU (D43, "giocatore medio"). Vede solo la propria vista.

Le situazioni si costruiscono a mano come viste del contratto (3.3); le partite intere
si giocano con il motore vero.
"""

import random
from dataclasses import replace

import pytest

from app.game.engine.actions import LayDownAction, PlayCardAction, SingAction
from app.game.engine.auto_move import auto_move
from app.game.engine.cards import Card, Rank, Suit
from app.game.engine.cpu import TRUMP_WORTH, cpu_move
from app.game.engine.errors import EngineError, InvalidMoveError
from app.game.engine.game import apply_game, game_legal_actions, new_game
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
    action = cpu_move(view(["coppe-10", "coppe-9", "denari-2"], can_sing=["coppe"]), random.Random(1))
    assert action == SingAction(0, Suit.COPPE)


def test_canta_il_seme_con_piu_carte():
    hand = ["coppe-10", "coppe-9", "spade-10", "spade-9", "spade-1"]
    action = cpu_move(view(hand, can_sing=["coppe", "spade"]), random.Random(1))
    assert action == SingAction(0, Suit.SPADE)


# --- Risposta -----------------------------------------------------------------------


def test_prende_con_la_carta_piu_economica_senza_briscola():
    # Sul 4 di denari: il Fante (2 punti) basta, l'Asso sarebbe sprecato
    hand = ["denari-1", "denari-8", "spade-2"]
    assert played(cpu_move(view(hand, trick=["denari-4"], trump="coppe"), random.Random(1))) == "denari-8"


def test_prende_anche_una_presa_senza_punti_se_non_costa_briscola():
    hand = ["denari-5", "spade-2", "bastoni-4"]
    assert played(cpu_move(view(hand, trick=["denari-4"], trump="coppe"), random.Random(1))) == "denari-5"


def test_briscola_solo_su_una_presa_che_vale():
    hand = ["coppe-2", "spade-4", "bastoni-10"]
    # Sull'Asso di denari (11 punti) prende con la briscola più piccola
    assert played(cpu_move(view(hand, trick=["denari-1"], trump="coppe"), random.Random(1))) == "coppe-2"
    # Sul Re di denari (4 punti) no: scarta la carta che vale meno
    assert played(cpu_move(view(hand, trick=["denari-10"], trump="coppe"), random.Random(1))) == "spade-4"
    assert TRUMP_WORTH == 10


def test_a_mazzo_finito_briscola_su_qualunque_presa_con_punti():
    hand = ["coppe-2", "spade-4"]
    move = cpu_move(view(hand, trick=["denari-8"], trump="coppe", deck=0), random.Random(1))
    assert played(move) == "coppe-2"
    # Su una presa senza punti non spreca la briscola
    move = cpu_move(view(hand, trick=["denari-4"], trump="coppe", deck=0), random.Random(1))
    assert played(move) == "spade-4"


def test_se_non_puo_prendere_scarta_la_carta_che_vale_meno():
    hand = ["spade-1", "bastoni-3", "bastoni-6", "coppe-2"]
    move = cpu_move(view(hand, trick=["denari-1"], trump="coppe"), random.Random(1))
    # coppe-2 prenderebbe l'Asso di denari (briscola); tolto quello, bastoni-6 costa meno
    assert played(move) == "coppe-2"
    move = cpu_move(view(["spade-1", "bastoni-3", "bastoni-6"], trick=["denari-1"], trump="coppe"),
                    random.Random(1))
    assert played(move) == "bastoni-6"


def test_carte_franche_nessuna_briscola():
    hand = ["spade-1", "bastoni-6"]
    move = cpu_move(view(hand, trick=["denari-3"], trump=None), random.Random(1))
    assert played(move) == "bastoni-6"


# --- Apertura -----------------------------------------------------------------------


def test_apre_con_la_carta_che_vale_meno_e_tiene_la_briscola():
    hand = ["denari-1", "coppe-2", "spade-3", "bastoni-7"]
    assert played(cpu_move(view(hand, trump="coppe"), random.Random(1))) == "bastoni-7"


def test_a_mazzo_finito_apre_con_la_briscola_piu_forte():
    hand = ["coppe-2", "coppe-1", "spade-6"]
    assert played(cpu_move(view(hand, trump="coppe", deck=0), random.Random(1))) == "coppe-1"


def test_non_rompe_una_coppia_da_cantare():
    # Re e Cavallo di spade non ancora cantati: apre con il Fante di bastoni (2 punti)
    hand = ["spade-10", "spade-9", "bastoni-8"]
    assert played(cpu_move(view(hand, trump="coppe"), random.Random(1))) == "bastoni-8"
    # Se spade è già stato cantato la coppia non conta più: gioca il Cavallo (3 punti) prima del Re
    hand = ["spade-10", "spade-9", "bastoni-1"]
    assert played(cpu_move(view(hand, trump="coppe", sings=["spade"]), random.Random(1))) == "spade-9"


def test_non_e_il_suo_turno():
    empty = view(["spade-1"])
    empty["legal"] = {"play": [], "sing": [], "lay_down": False}
    with pytest.raises(EngineError, match="Non è il turno della CPU."):
        cpu_move(empty)


# --- Partite intere con il motore vero ----------------------------------------------


def play_game(players, seed, chooser):
    """Partita intera: chooser(game, seat, rng) dà la mossa; restituisce la partita finita."""
    rng = random.Random(seed)
    game = new_game(players, 150, rng=rng)
    while not game.finished:
        game = apply_game(game, chooser(game, game.hand.turn_seat, rng), rng=rng)
    return game


def cpu(game, seat, rng):
    return cpu_move(player_view(game, seat), rng)


@pytest.mark.parametrize("seed", range(20))
@pytest.mark.parametrize("players", (2, 4))
def test_la_cpu_gioca_solo_mosse_legali_fino_alla_fine(players, seed):
    """Ogni mossa della CPU è tra quelle legali (apply_game la accetterebbe) e la partita finisce."""
    def checked(game, seat, rng):
        action = cpu(game, seat, rng)
        legal = game_legal_actions(game, seat)
        if isinstance(action, SingAction):
            assert action.suit in legal.sing
        elif isinstance(action, LayDownAction):
            assert legal.lay_down
        else:
            assert action.card in legal.play
        return action

    assert play_game(players, seed, checked).finished


def test_la_cpu_non_vede_le_carte_nascoste():
    """Stessa vista, carte nascoste diverse (mano dell'avversario e mazzo scambiati): stessa mossa."""
    rng = random.Random(3)
    game = new_game(2, 150, rng=rng)
    while game.hand.turn_seat != 0 or not game.hand.trick:
        game = apply_game(game, auto_move(game, rng), rng=rng)
    hand = game.hand
    other = list(hand.hands[1])
    deck = list(hand.deck)
    other[0], deck[0] = deck[0], other[0]
    hidden = replace(game, hand=replace(hand, hands=(hand.hands[0], tuple(other)), deck=tuple(deck)))
    assert player_view(hidden, 0) == player_view(game, 0)
    assert cpu_move(player_view(hidden, 0), random.Random(9)) == cpu_move(player_view(game, 0), random.Random(9))


def test_la_cpu_batte_la_mossa_automatica():
    """Non gioca a caso: contro chi scarta sempre la carta che vale meno vince molto più spesso."""
    def mixed(game, seat, rng):
        return cpu(game, seat, rng) if seat == 0 else auto_move(game, rng)

    games = [play_game(2, seed, mixed) for seed in range(100)]
    wins = sum(game.result.winner_team == 0 for game in games)
    assert wins >= 75, wins


def test_mossa_rifiutata_se_la_vista_e_vecchia():
    """La CPU sceglie dalla vista: una vista di un altro momento dà una mossa che il motore rifiuta."""
    rng = random.Random(4)
    game = new_game(2, 150, rng=rng)
    seat = game.hand.turn_seat
    old = player_view(game, seat)
    game = apply_game(game, auto_move(game, rng), rng=rng)
    with pytest.raises(InvalidMoveError):
        apply_game(game, cpu_move(old, random.Random(1)), rng=rng)
