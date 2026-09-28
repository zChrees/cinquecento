"""Mossa automatica allo scadere del turno (P15, D12; regola in docs/REGOLE-GIOCO.md, "Tempo per turno").

Si gioca la carta con meno punti; a parità una non di briscola; a parità la più debole
nella presa; se resta una parità, una a caso. Non canta mai.
"""

import random
import secrets

from app.game.engine.actions import PlayCardAction
from app.game.engine.errors import EngineError
from app.game.engine.game import game_legal_actions
from app.game.engine.rules import MARIANNA, RuleSet
from app.game.engine.state import GameState


def auto_move(game: GameState, rng: random.Random | None = None, rules: RuleSet = MARIANNA) -> PlayCardAction:
    """La mossa per chi è di turno. In gioco rng è None (secrets.SystemRandom); i test passano un seme fisso."""
    if game.finished:
        raise EngineError("La partita è finita.")
    seat = game.hand.turn_seat
    cards = game_legal_actions(game, seat, rules).play
    trump = game.hand.trump

    def key(card):
        return (card.points, card.suit == trump, card.strength)

    best = min(key(card) for card in cards)
    candidates = [card for card in cards if key(card) == best]
    if rng is None:
        rng = secrets.SystemRandom()
    return PlayCardAction(seat, rng.choice(candidates))
