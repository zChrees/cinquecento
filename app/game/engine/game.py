"""Svolgimento di una mano (P13, regole in docs/REGOLE-GIOCO.md, "Svolgimento di una mano").

apply(stato, azione) -> nuovo stato; legal_actions(stato) -> le mosse di chi è di turno.
Una mossa non valida solleva InvalidMoveError (NotYourTurnError fuori turno) e lo stato
di partenza resta com'è, perché è immutabile.
"""

from collections.abc import Sequence
from dataclasses import dataclass, replace

from app.game.engine.actions import Action, PlayCardAction, SingAction
from app.game.engine.cards import Card, Suit
from app.game.engine.deck import full_deck
from app.game.engine.errors import EngineError, InvalidMoveError, NotYourTurnError
from app.game.engine.rules import MARIANNA, RuleSet
from app.game.engine.singing import sing, singable_suits
from app.game.engine.state import (
    TEAMS,
    HandResult,
    HandState,
    LastTrick,
    TrickPlay,
    team_of,
)
from app.game.engine.trick import trick_winner


def new_hand(
    num_players: int,
    first_seat: int,
    deck: Sequence[Card],
    rules: RuleSet = MARIANNA,
) -> HandState:
    """Distribuisce 5 carte a testa da un mazzo già mescolato; il resto è il mazzo da pescare.

    first_seat è chi gioca per primo (lo decide la partita, P14).
    """
    if num_players not in rules.player_counts:
        raise EngineError("Si gioca in 2 o in 4.")
    if not 0 <= first_seat < num_players:
        raise EngineError("Posto di partenza non valido.")
    if len(deck) != len(full_deck()) or set(deck) != set(full_deck()):
        raise EngineError("Il mazzo deve avere le 40 carte, ognuna una volta.")
    size = rules.hand_size
    hands = tuple(tuple(deck[seat * size:(seat + 1) * size]) for seat in range(num_players))
    return HandState(
        num_players=num_players,
        hands=hands,
        deck=tuple(deck[num_players * size:]),
        trick=(),
        leader_seat=first_seat,
        turn_seat=first_seat,
        sings=(),
        captured=((),) * TEAMS,
        last_trick=None,
    )


@dataclass(frozen=True)
class LegalActions:
    play: tuple[Card, ...]
    sing: tuple[Suit, ...]  # nell'ordine fisso di Suit


def legal_actions(state: HandState, seat: int, rules: RuleSet = MARIANNA) -> LegalActions:
    """Le mosse ammesse per quel posto adesso: vuote se non è il suo turno."""
    if state.finished or seat != state.turn_seat:
        return LegalActions(play=(), sing=())
    hand = state.hands[seat]
    suits = singable_suits(
        hand=hand,
        sings=state.sings,
        played_cards=state.played_cards,
        deck_count=len(state.deck),
        is_turn=True,
        rules=rules,
    )
    # Non c'è obbligo di rispondere al seme: si può giocare qualsiasi carta
    return LegalActions(play=hand, sing=tuple(suits))


def apply(state: HandState, action: Action, rules: RuleSet = MARIANNA) -> HandState:
    if not isinstance(action, PlayCardAction | SingAction):
        raise InvalidMoveError("Mossa non valida.")
    seat = action.seat
    if isinstance(seat, bool) or not isinstance(seat, int) or not 0 <= seat < state.num_players:
        raise InvalidMoveError("Posto non valido.")
    if state.finished:
        raise InvalidMoveError("La mano è finita.")
    if seat != state.turn_seat:
        raise NotYourTurnError("Non è il tuo turno.")
    if isinstance(action, SingAction):
        return _apply_sing(state, action, rules)
    return _apply_play(state, action)


def _apply_sing(state: HandState, action: SingAction, rules: RuleSet) -> HandState:
    done = sing(
        action.suit,
        seat=action.seat,
        hand=state.hands[action.seat],
        sings=state.sings,
        played_cards=state.played_cards,
        deck_count=len(state.deck),
        is_turn=True,
        rules=rules,
    )
    # Dopo il canto il turno resta a chi ha cantato: deve ancora giocare la carta
    return replace(state, sings=(*state.sings, done))


def _apply_play(state: HandState, action: PlayCardAction) -> HandState:
    seat, card = action.seat, action.card
    hand = state.hands[seat]
    if not isinstance(card, Card) or card not in hand:
        raise InvalidMoveError("Non hai questa carta in mano.")
    hands = _with_hand(state.hands, seat, tuple(c for c in hand if c != card))
    trick = (*state.trick, TrickPlay(seat, card))
    if len(trick) < state.num_players:
        return replace(state, hands=hands, trick=trick, turn_seat=_next_seat(seat, state.num_players))
    return _close_trick(replace(state, hands=hands, trick=trick))


def _close_trick(state: HandState) -> HandState:
    """Presa completa: la vince chi deve, poi si pesca e chi ha preso apre la presa dopo."""
    position = trick_winner([play.card for play in state.trick], state.trump)
    winner = state.trick[position].seat
    team = team_of(winner)
    captured = tuple(
        (*taken, *(play.card for play in state.trick)) if index == team else taken
        for index, taken in enumerate(state.captured)
    )

    # Pesca: prima chi ha vinto la presa, poi gli altri in ordine di turno.
    # Il mazzo (30 carte nel 1v1, 20 nel 2v2) finisce sempre a fine giro.
    hands, deck = state.hands, state.deck
    if deck:
        for step in range(state.num_players):
            drawer = _next_seat(winner, state.num_players, step)
            hands = _with_hand(hands, drawer, (*hands[drawer], deck[0]))
            deck = deck[1:]

    finished = not any(hands)
    return replace(
        state,
        hands=hands,
        deck=deck,
        trick=(),
        leader_seat=winner,
        turn_seat=None if finished else winner,
        captured=captured,
        last_trick=LastTrick(winner, state.trick),
    )


def hand_result(state: HandState, rules: RuleSet = MARIANNA) -> HandResult:
    """Punti della mano per squadra: carte prese più canti. L'ultima presa non dà bonus."""
    if not state.finished:
        raise EngineError("La mano non è ancora finita.")
    card_points = [sum(card.points for card in taken) for taken in state.captured]
    if state.last_trick is not None:
        card_points[team_of(state.last_trick.winner_seat)] += rules.last_trick_bonus
    sing_points = [0] * TEAMS
    for done in state.sings:
        sing_points[team_of(done.seat)] += done.points
    return HandResult(card_points=tuple(card_points), sing_points=tuple(sing_points))


def _next_seat(seat: int, num_players: int, steps: int = 1) -> int:
    return (seat + steps) % num_players


def _with_hand(hands: tuple, seat: int, cards: tuple) -> tuple:
    return tuple(cards if index == seat else hand for index, hand in enumerate(hands))
