"""P15: vista per giocatore e mosse legali.

Comando (finché P6 non aggiunge il runner): python -m pytest tests/engine
"""

import json
import random
from dataclasses import replace
from itertools import pairwise
from pathlib import Path

import pytest

from app.game.engine.actions import LayDownAction, PlayCardAction, SingAction
from app.game.engine.cards import Card, Suit
from app.game.engine.deck import full_deck
from app.game.engine.errors import EngineError, InvalidMoveError
from app.game.engine.game import (
    apply_game,
    game_legal_actions,
    new_game,
    partner_cards_visible,
)
from app.game.engine.singing import Sing
from app.game.engine.state import TrickPlay
from app.game.engine.views import (
    ROOM_FIELDS,
    ROOM_PLAYER_FIELDS,
    ROOM_TURN_FIELDS,
    card_to_dict,
    player_view,
)

EXAMPLES = Path(__file__).resolve().parents[2] / "app" / "static" / "dev"
TWO_V_TWO_ONLY = {"partner_hand", "advice"}  # P92: chiavi che ci sono solo nella vista del 2v2
MODES = (2, 4)


def random_move(game, rng):
    seat = game.hand.turn_seat
    legal = game_legal_actions(game, seat)
    moves = [PlayCardAction(seat, card) for card in legal.play]
    moves += [SingAction(seat, suit) for suit in legal.sing]
    return rng.choice(moves)


def all_states(players, target, seed):
    """Tutte le posizioni di una partita intera giocata a caso, dall'inizio alla fine."""
    rng = random.Random(seed)
    game = new_game(players, target, rng=rng)
    states = [game]
    while not game.finished:
        game = apply_game(game, random_move(game, rng), rng=rng)
        states.append(game)
    return states


def cards_in(value):
    """Ogni carta ({"suit", "rank"}) che compare in un punto qualsiasi della vista."""
    if isinstance(value, dict):
        if set(value) == {"suit", "rank"}:
            yield (value["suit"], value["rank"])
        else:
            for item in value.values():
                yield from cards_in(item)
    elif isinstance(value, list):
        for item in value:
            yield from cards_in(item)


def as_keys(cards):
    return {(card.suit.value, card.rank.value) for card in cards}


# --- Nessuna carta nascosta ---------------------------------------------------------


@pytest.mark.parametrize("seed", range(5))
@pytest.mark.parametrize("players", MODES)
def test_la_vista_non_mostra_mai_carte_nascoste(players, seed):
    for game in all_states(players, 300, seed):
        hand = game.hand
        public = as_keys(play.card for play in hand.trick)
        if hand.last_trick is not None:
            public |= as_keys(play.card for play in hand.last_trick.plays)
        for seat in range(players):
            view = player_view(game, seat)
            own = as_keys(hand.hands[seat])
            # D46 (P92): nel 2v2, con briscola e mazzo finito insieme, le carte del compagno e solo le sue
            partner = (seat + 2) % players
            visible = players == 4 and hand.trump is not None and not hand.deck and not hand.finished
            assert partner_cards_visible(hand) is visible
            if players == 2:
                assert "partner_hand" not in view
            elif visible:
                assert as_keys(Card.from_code(f"{c['suit']}-{c['rank']}") for c in view["partner_hand"])                     == as_keys(hand.hands[partner])
            else:
                assert view["partner_hand"] is None
            shown_partner = as_keys(hand.hands[partner]) if visible else set()
            # last_hand parla della mano prima, con il mazzo mescolato di nuovo: le sue carte
            # possono essere adesso in mano a un altro, quindi si controlla a parte (P58)
            current = {key: value for key, value in view.items() if key != "last_hand"}
            assert set(cards_in(current)) <= own | public | shown_partner
            assert {(c["suit"], c["rank"]) for c in view["hand"]} == own
            # Nessuna carta degli avversari, del mazzo o delle prese chiuse (tranne l'ultima)
            hidden = as_keys(
                card for other in range(players) if other != seat for card in hand.hands[other]
            ) | as_keys(hand.deck)
            hidden -= shown_partner
            assert not set(cards_in(current)) & (hidden - public)
            # In last_hand solo le carte della presa che ha chiuso la mano prima, già viste da tutti
            if game.last_hand is None:
                assert view["last_hand"] is None
            else:
                shown = list(cards_in(view["last_hand"]))
                assert sorted(shown) == sorted(
                    (play.card.suit.value, play.card.rank.value) for play in game.last_hand.last_trick.plays
                )
            assert [p["cards_in_hand"] for p in view["players"]] == [len(h) for h in hand.hands]
            assert view["deck_count"] == len(hand.deck)
            json.dumps(view)  # si può mandare così com'è


def test_nessun_campo_con_mazzo_o_prese():
    view = player_view(new_game(2, 150, rng=random.Random(1)), 0)
    text = json.dumps(view)
    for word in ("deck\"", "captured", "hands"):
        assert word not in text


# --- Mosse legali -------------------------------------------------------------------


@pytest.mark.parametrize("seed", range(3))
@pytest.mark.parametrize("players", MODES)
def test_legal_coincide_con_le_mosse_accettate(players, seed):
    every_card = full_deck()
    for game in all_states(players, 150, seed):
        for seat in range(players):
            legal = player_view(game, seat)["legal"]
            accepted_cards, accepted_suits = [], []
            for card in every_card:
                try:
                    apply_game(game, PlayCardAction(seat, card), rng=random.Random(0))
                    accepted_cards.append(card_to_dict(card))
                except InvalidMoveError:
                    pass
            for suit in Suit:
                try:
                    apply_game(game, SingAction(seat, suit), rng=random.Random(0))
                    accepted_suits.append(suit.value)
                except InvalidMoveError:
                    pass
            assert sorted(legal["play"], key=json.dumps) == sorted(accepted_cards, key=json.dumps)
            assert sorted(legal["sing"]) == sorted(accepted_suits)
            try:
                apply_game(game, LayDownAction(seat), rng=random.Random(0))
                accepted_lay_down = True
            except InvalidMoveError:
                accepted_lay_down = False
            assert legal["lay_down"] is accepted_lay_down
            if game.finished or seat != game.hand.turn_seat:
                assert legal == {"play": [], "sing": [], "lay_down": False}


# --- Forma della vista (app/static/dev/vista_*.json) -------------------------------


def check_shape(ours, example, path=""):
    """Stesse chiavi e stessi tipi dell'esempio; null va bene da una parte o dall'altra."""
    if ours is None or example is None:
        return
    if isinstance(example, dict):
        assert isinstance(ours, dict), path
        missing = {
            "": {"_nota", *ROOM_FIELDS},
            ".players[]": set(ROOM_PLAYER_FIELDS),
            ".turn": set(ROOM_TURN_FIELDS),
        }.get(path, set())
        assert set(ours) == set(example) - missing, path
        for key, value in ours.items():
            check_shape(value, example[key], f"{path}.{key}")
    elif isinstance(example, list):
        assert isinstance(ours, list), path
        if example:
            for item in ours:
                check_shape(item, example[0], f"{path}[]")
    else:
        assert type(ours) is type(example), path


def load_example(name):
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize("players", MODES)
def test_stessa_forma_degli_esempi(players):
    # Ogni vista ha la forma dell'esempio della sua modalità: i due esempi hanno le stesse
    # chiavi, tranne quelle che ci sono solo nel 2v2 (P92: carte del compagno e consiglio)
    examples = {2: load_example("vista_1v1.json"), 4: load_example("vista_2v2.json")}
    assert set(examples[4]) - set(examples[2]) == TWO_V_TWO_ONLY
    assert set(examples[2]) - set(examples[4]) == set()
    checked_full = False
    games = (game for seed in range(10) for game in all_states(players, 500, seed))
    for game in games:
        for seat in range(players):
            view = player_view(game, seat)
            check_shape(view, examples[players])
        hand = game.hand
        if game.hand_number >= 2 and hand.trump and hand.trick and hand.last_trick and hand.sings:
            checked_full = True  # c'è stata almeno una vista con tutti i campi pieni
    assert checked_full


def test_valori_come_nel_contratto():
    game = new_game(4, 300, rng=random.Random(2))
    game = replace(game, first_seat=0, hand=replace(game.hand, turn_seat=0, leader_seat=0))
    view = player_view(game, 2)
    assert view["mode"] == "2v2" and view["target_score"] == 300
    assert view["status"] == "playing"
    assert view["hand_number"] == 1 and view["dealer_seat"] == 3
    assert view["you"] == {"seat": 2}
    assert [(p["seat"], p["team"]) for p in view["players"]] == [(0, 0), (1, 1), (2, 0), (3, 1)]
    assert view["trick"] == {"leader_seat": 0, "cards": [], "winning_seat": None}
    assert view["last_trick"] is None and view["trump"] is None and view["sings"] == []
    assert view["scores"] == [{"team": 0, "total": 0}, {"team": 1, "total": 0}]
    assert view["hand_points"] == [{"team": 0, "total": 0}, {"team": 1, "total": 0}]
    assert view["last_hand"] is None and view["result"] is None
    assert view["turn"] == {"seat": 0}
    assert view["legal"] == {"play": [], "sing": [], "lay_down": False}  # non è il turno del posto 2
    assert player_view(game, 0)["legal"]["play"] == [card_to_dict(c) for c in game.hand.hands[0]]
    assert player_view(new_game(2, 150, rng=random.Random(2)), 0)["mode"] == "1v1"


def test_riepilogo_dell_ultima_mano():
    states = all_states(2, 500, 3)
    second = next(game for game in states if game.hand_number == 2)
    view = player_view(second, 0)
    done = second.last_hand
    assert view["last_hand"] == {
        "hand_number": 1,
        "teams": [
            {"team": team, "card_points": done.card_points[team], "sing_points": done.sing_points[team],
             "hand_total": done.totals[team]}
            for team in (0, 1)
        ],
        "last_trick": {
            "winner_seat": done.last_trick.winner_seat,
            "cards": [{"seat": play.seat, "card": card_to_dict(play.card)} for play in done.last_trick.plays],
        },
        "laid_down": None,
    }
    # La mano nuova parte senza last_trick: la carta che ha chiuso la mano si vede solo qui (P58)
    assert view["last_trick"] is None
    assert len(view["last_hand"]["last_trick"]["cards"]) == 2
    assert view["scores"] == [{"team": team, "total": second.scores[team]} for team in (0, 1)]
    # Il tabellone resta fermo durante la mano: i punti della mano in corso stanno in hand_points (P67)
    later = next(game for game in states if game.hand_number == 2 and game.hand.last_trick is not None)
    assert player_view(later, 0)["scores"] == view["scores"]


# --- Punti della mano in corso (P67, D44) -------------------------------------------


def expected_hand_points(hand):
    points = [sum(card.points for card in taken) for taken in hand.captured]
    for done in hand.sings:
        points[done.seat % 2] += done.points
    return [{"team": team, "total": points[team]} for team in (0, 1)]


@pytest.mark.parametrize("seed", range(5))
@pytest.mark.parametrize("players", MODES)
def test_punti_della_mano_in_corso(players, seed):
    """Carte prese più canti di tutte e due le squadre, uguali per tutti i posti."""
    for game in all_states(players, 300, seed):
        views = [player_view(game, seat) for seat in range(players)]
        assert views[0]["hand_points"] == expected_hand_points(game.hand)
        # Tutti vedono i punti di tutte e due le squadre (D44)
        assert all(view["hand_points"] == views[0]["hand_points"] for view in views)


@pytest.mark.parametrize("players", MODES)
def test_punti_della_mano_ripartono_da_zero(players):
    states = all_states(players, 500, 5)
    for before, after in pairwise(states):
        view = player_view(after, 0)
        if after.hand_number != before.hand_number:
            # Mano nuova: da zero, e i punti della mano finita passano in last_hand e nel tabellone
            assert view["hand_points"] == [{"team": 0, "total": 0}, {"team": 1, "total": 0}]
            assert [team["hand_total"] for team in view["last_hand"]["teams"]] == list(after.last_hand.totals)
        elif not after.finished:
            # Durante la mano i punti salgono (una presa o un canto) o restano uguali (una carta)
            old = player_view(before, 0)["hand_points"]
            assert all(new["total"] >= prev["total"] for new, prev in zip(view["hand_points"], old, strict=True))


@pytest.mark.parametrize("players", MODES)
def test_punti_della_mano_dopo_presa_e_canto(players):
    states = all_states(players, 500, 6)
    # Prima presa chiusa della partita: i suoi punti vanno solo a chi l'ha vinta
    closed = next(game for game in states if game.hand.last_trick is not None)
    winner = closed.hand.last_trick.winner_seat % 2
    points = [0, 0]
    points[winner] = sum(play.card.points for play in closed.hand.last_trick.plays)
    assert player_view(closed, 0)["hand_points"] == [{"team": 0, "total": points[0]}, {"team": 1, "total": points[1]}]
    # Un canto aggiunge subito i suoi punti alla squadra di chi canta, e niente all'altra
    before, after = next(
        (a, b)
        for seed in range(6, 20)
        for game_states in [all_states(players, 500, seed)]
        for a, b in pairwise(game_states)
        if b.hand_number == a.hand_number and len(b.hand.sings) > len(a.hand.sings)
    )
    sing = after.hand.sings[-1]
    old = player_view(before, 0)["hand_points"]
    new = player_view(after, 0)["hand_points"]
    assert new[sing.seat % 2]["total"] == old[sing.seat % 2]["total"] + sing.points
    assert new[1 - sing.seat % 2] == old[1 - sing.seat % 2]


def test_punti_della_mano_a_partita_finita():
    final = all_states(4, 150, 7)[-1]
    view = player_view(final, 0)
    # A partita finita la mano in corso è l'ultima: i suoi punti sono quelli del riepilogo
    assert [team["total"] for team in view["hand_points"]] == [
        team["hand_total"] for team in view["last_hand"]["teams"]
    ]


# --- Carta che sta vincendo la presa (P75) -------------------------------------------


def expected_winning_seat(plays, trump):
    """La regola scritta di nuovo, senza il motore: la briscola più forte, se c'è, sennò la più forte del seme di uscita."""
    lead = plays[0].card.suit
    pool = [play for play in plays if play.card.suit == trump] or [play for play in plays if play.card.suit == lead]
    return max(pool, key=lambda play: play.card.strength).seat


@pytest.mark.parametrize("seed", range(5))
@pytest.mark.parametrize("players", MODES)
def test_carta_che_sta_vincendo_la_presa(players, seed):
    seen = set()
    for game in all_states(players, 300, seed):
        hand = game.hand
        views = [player_view(game, seat) for seat in range(players)]
        expected = expected_winning_seat(hand.trick, hand.trump) if hand.trick else None
        # Uguale per tutti i posti, null senza carte sul tavolo
        assert all(view["trick"]["winning_seat"] == expected for view in views)
        seen.add(len(hand.trick))
    assert seen == set(range(players))  # provate tutte le prese a metà, da 0 a players - 1 carte


@pytest.mark.parametrize("players", MODES)
def test_carta_che_sta_vincendo_coincide_con_chi_prende(players):
    """Prima dell'ultima carta, chi sta vincendo più l'ultima carta dà proprio chi prende la presa."""
    checked = 0
    for before, after in pairwise(all_states(players, 300, 8)):
        if after.hand_number != before.hand_number or len(before.hand.trick) != players - 1:
            continue
        last = after.hand.last_trick
        assert last is not None and last.plays[:-1] == before.hand.trick
        leading = player_view(before, 0)["trick"]["winning_seat"]
        final = last.plays[-1]
        overtakes = expected_winning_seat(last.plays, before.hand.trump) == final.seat
        assert last.winner_seat == (final.seat if overtakes else leading)
        checked += 1
    assert checked > 10


def test_la_briscola_giocata_dopo_passa_avanti():
    game = new_game(4, 300, rng=random.Random(2))
    plays = (
        TrickPlay(0, Card.from_code("coppe-1")),
        TrickPlay(1, Card.from_code("coppe-3")),
    )
    game = replace(game, hand=replace(game.hand, sings=(Sing(1, Suit("spade"), 40),), leader_seat=0, turn_seat=2, trick=plays[:1]))
    assert player_view(game, 3)["trick"]["winning_seat"] == 0  # una carta sola vince sempre
    game = replace(game, hand=replace(game.hand, trick=plays))
    assert player_view(game, 3)["trick"]["winning_seat"] == 0  # l'Asso batte il Tre
    game = replace(game, hand=replace(game.hand, trick=(*plays, TrickPlay(2, Card.from_code("spade-2")))))
    assert player_view(game, 3)["trick"]["winning_seat"] == 2  # il 2 di briscola batte l'Asso
    game = replace(game, hand=replace(game.hand, sings=()))
    assert player_view(game, 3)["trick"]["winning_seat"] == 0  # a carte franche no


def test_vista_a_partita_finita():
    final = all_states(2, 150, 4)[-1]
    view = player_view(final, 1)
    assert view["status"] == "finished"
    assert view["turn"] is None
    assert view["legal"] == {"play": [], "sing": [], "lay_down": False}
    assert view["last_hand"]["hand_number"] == final.hand_number
    assert view["result"] == {
        "reason": "score",
        "winner_team": final.result.winner_team,
        "abandoned_seats": [],
        "scores": [{"team": team, "total": final.scores[team]} for team in (0, 1)],
    }


@pytest.mark.parametrize("seat", [-1, 2, 4, "0", None, True, 0.0])
def test_posto_non_valido(seat):
    with pytest.raises(EngineError, match="Posto non valido."):
        player_view(new_game(2, 150, rng=random.Random(1)), seat)
