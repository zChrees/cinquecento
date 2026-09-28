"""P15: vista per giocatore e mosse legali.

Comando (finché P6 non aggiunge il runner): python -m pytest tests/engine
"""

import json
import random
from dataclasses import replace
from pathlib import Path

import pytest

from app.game.engine.actions import PlayCardAction, SingAction
from app.game.engine.cards import Suit
from app.game.engine.deck import full_deck
from app.game.engine.errors import EngineError, InvalidMoveError
from app.game.engine.game import apply_game, game_legal_actions, new_game
from app.game.engine.views import (
    ROOM_FIELDS,
    ROOM_PLAYER_FIELDS,
    ROOM_TURN_FIELDS,
    card_to_dict,
    player_view,
)

EXAMPLES = Path(__file__).resolve().parents[2] / "app" / "static" / "dev"
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
            assert set(cards_in(view)) <= own | public
            assert {(c["suit"], c["rank"]) for c in view["hand"]} == own
            # Nessuna carta degli altri, del mazzo o delle prese chiuse (tranne l'ultima)
            hidden = as_keys(
                card for other in range(players) if other != seat for card in hand.hands[other]
            ) | as_keys(hand.deck)
            assert not set(cards_in(view)) & (hidden - public)
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
            if game.finished or seat != game.hand.turn_seat:
                assert legal == {"play": [], "sing": []}


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
    examples = [load_example("vista_1v1.json"), load_example("vista_2v2.json")]
    checked_full = False
    games = (game for seed in range(10) for game in all_states(players, 500, seed))
    for game in games:
        for seat in range(players):
            view = player_view(game, seat)
            for example in examples:
                check_shape(view, example)
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
    assert view["trick"] == {"leader_seat": 0, "cards": []}
    assert view["last_trick"] is None and view["trump"] is None and view["sings"] == []
    assert view["scores"] == [{"team": 0, "total": 0}, {"team": 1, "total": 0}]
    assert view["last_hand"] is None and view["result"] is None
    assert view["turn"] == {"seat": 0}
    assert view["legal"] == {"play": [], "sing": []}  # non è il turno del posto 2
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
    }
    assert view["scores"] == [{"team": team, "total": second.scores[team]} for team in (0, 1)]
    # I punti delle carte prese nella mano in corso non si vedono
    later = next(game for game in states if game.hand_number == 2 and game.hand.last_trick is not None)
    assert player_view(later, 0)["scores"] == view["scores"]


def test_vista_a_partita_finita():
    final = all_states(2, 150, 4)[-1]
    view = player_view(final, 1)
    assert view["status"] == "finished"
    assert view["turn"] is None
    assert view["legal"] == {"play": [], "sing": []}
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
