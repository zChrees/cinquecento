"""Svolgimento di una mano (P13) e della partita intera (P14).

Regole in docs/REGOLE-GIOCO.md, "Svolgimento di una mano", "Chi comincia" e
"Punteggio e fine partita".

Mano: apply(stato, azione) -> nuovo stato; legal_actions(stato) -> le mosse di chi è di turno.
Partita: new_game, apply_game e game_legal_actions, che usano quelle della mano.
Una mossa non valida solleva InvalidMoveError (NotYourTurnError fuori turno) e lo stato
di partenza resta com'è, perché è immutabile.
"""

import random
import secrets
from collections.abc import Sequence
from dataclasses import dataclass, replace

from app.game.engine.actions import Action, LayDownAction, PlayCardAction, SingAction
from app.game.engine.cards import Card, Suit
from app.game.engine.deck import full_deck, shuffled_deck
from app.game.engine.errors import EngineError, InvalidMoveError, NotYourTurnError
from app.game.engine.lay_down import can_lay_down, partner_sings
from app.game.engine.rules import MARIANNA, RuleSet
from app.game.engine.singing import sing, singable_suits
from app.game.engine.state import (
    TEAMS,
    GameResult,
    GameState,
    HandResult,
    HandState,
    LaidDown,
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
    lay_down: bool = False  # "Cala le carte" (P84)


def partner_cards_visible(state: HandState) -> bool:
    """D46 (P92): nel 2v2, con la briscola fissata e il mazzo finito, ognuno vede le carte del compagno.

    Vale da quando ci sono tutti e due, in qualunque ordine arrivino, fino a fine mano;
    senza briscola mai. Nel 1v1 non c'è un compagno.
    """
    return state.num_players == 4 and not state.finished and state.trump is not None and not state.deck


def _in_first_trick(state: HandState) -> bool:
    """Prima presa della mano: nessuna presa chiusa, e last_trick riparte da None a ogni mano (P58)."""
    return state.last_trick is None


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
        first_trick=_in_first_trick(state),
        rules=rules,
    )
    # Non c'è obbligo di rispondere al seme: si può giocare qualsiasi carta
    return LegalActions(play=hand, sing=tuple(suits), lay_down=can_lay_down(state, seat, rules))


def apply(state: HandState, action: Action, rules: RuleSet = MARIANNA) -> HandState:
    if not isinstance(action, PlayCardAction | SingAction | LayDownAction):
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
    if isinstance(action, LayDownAction):
        return _apply_lay_down(state, action, rules)
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
        first_trick=_in_first_trick(state),
        rules=rules,
    )
    # Dopo il canto il turno resta a chi ha cantato: deve ancora giocare la carta
    return replace(state, sings=(*state.sings, done))


def _apply_lay_down(state: HandState, action: LayDownAction, rules: RuleSet) -> HandState:
    """Cala le carte (P84): la mano finisce e la squadra di chi cala prende tutte le carte rimaste."""
    if not can_lay_down(state, action.seat, rules):
        raise InvalidMoveError("Adesso non puoi calare le carte.")
    added = partner_sings(state, action.seat, rules)
    team = team_of(action.seat)
    remaining = tuple(card for hand in state.hands for card in hand)
    captured = tuple(
        (*taken, *remaining) if index == team else taken for index, taken in enumerate(state.captured)
    )
    return replace(
        state,
        hands=((),) * state.num_players,
        turn_seat=None,
        sings=(*state.sings, *added),
        captured=captured,
        laid_down=LaidDown(action.seat, state.hands, added),
    )


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
    # Una mano finita ha sempre almeno una presa chiusa: anche per calare il mazzo deve essere finito
    card_points = [sum(card.points for card in taken) for taken in state.captured]
    # Calando, l'ultima presa sarebbe della squadra di chi cala
    last_winner = state.last_trick.winner_seat if state.laid_down is None else state.laid_down.seat
    card_points[team_of(last_winner)] += rules.last_trick_bonus
    sing_points = [0] * TEAMS
    for done in state.sings:
        sing_points[team_of(done.seat)] += done.points
    return HandResult(
        card_points=tuple(card_points),
        sing_points=tuple(sing_points),
        last_trick=state.last_trick,
        laid_down=state.laid_down,
    )


def new_game(
    num_players: int,
    target_score: int,
    rng: random.Random | None = None,
    rules: RuleSet = MARIANNA,
) -> GameState:
    """Prima mano: chi comincia si sceglie a caso, il mazziere è alla sua sinistra (D11).

    In gioco rng è None (secrets.SystemRandom); i test passano un seme fisso.
    """
    if num_players not in rules.player_counts:
        raise EngineError("Si gioca in 2 o in 4.")
    if (
        isinstance(target_score, bool)
        or not isinstance(target_score, int)
        or target_score not in rules.target_scores
    ):
        allowed = ", ".join(str(score) for score in rules.target_scores[:-1])
        raise EngineError(f"Punteggio non valido: si gioca a {allowed} o {rules.target_scores[-1]}.")
    if rng is None:
        rng = secrets.SystemRandom()
    first_seat = rng.randrange(num_players)
    return GameState(
        num_players=num_players,
        target_score=target_score,
        hand_number=1,
        first_seat=first_seat,
        hand=new_hand(num_players, first_seat, shuffled_deck(rng), rules),
        scores=(0,) * TEAMS,
        last_hand=None,
        result=None,
    )


def game_legal_actions(game: GameState, seat: int, rules: RuleSet = MARIANNA) -> LegalActions:
    if game.finished:
        return LegalActions(play=(), sing=())
    return legal_actions(game.hand, seat, rules)


def apply_game(
    game: GameState,
    action: Action,
    rng: random.Random | None = None,
    rules: RuleSet = MARIANNA,
) -> GameState:
    """Applica la mossa alla mano in corso; a fine mano somma i punti e controlla la fine.

    Il punteggio per vincere si controlla solo a fine mano, anche se un canto lo fa
    raggiungere prima. Se la partita continua comincia la mano dopo, con il mazzo
    mescolato di nuovo (rng serve solo a questo).
    """
    if game.finished:
        raise InvalidMoveError("La partita è finita.")
    hand = apply(game.hand, action, rules)
    if not hand.finished:
        return replace(game, hand=hand)

    done = hand_result(hand, rules)
    scores = tuple(score + points for score, points in zip(game.scores, done.totals, strict=True))
    result = _game_result(scores, game.target_score)
    if result is not None:
        return replace(game, hand=hand, scores=scores, last_hand=done, result=result)

    # Si gira verso destra: comincia chi sta alla destra di chi aveva cominciato (D11)
    first_seat = _next_seat(game.first_seat, game.num_players)
    return replace(
        game,
        hand_number=game.hand_number + 1,
        first_seat=first_seat,
        hand=new_hand(game.num_players, first_seat, shuffled_deck(rng), rules),
        scores=scores,
        last_hand=done,
    )


def _game_result(scores: tuple[int, ...], target_score: int) -> GameResult | None:
    """Vince chi arriva ad almeno N; se ci arrivano entrambi il più alto; a parità è pareggio."""
    if max(scores) < target_score:
        return None
    leaders = [team for team, score in enumerate(scores) if score == max(scores)]
    return GameResult(winner_team=leaders[0] if len(leaders) == 1 else None)


def _next_seat(seat: int, num_players: int, steps: int = 1) -> int:
    return (seat + steps) % num_players


def _with_hand(hands: tuple, seat: int, cards: tuple) -> tuple:
    return tuple(cards if index == seat else hand for index, hand in enumerate(hands))
