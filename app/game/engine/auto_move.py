"""Mossa automatica allo scadere del turno (P15, D12; regola in docs/REGOLE-GIOCO.md, "Tempo per turno").

Si gioca la carta con meno punti; a parità una non di briscola; a parità la più debole
nella presa; se resta una parità, una a caso. Non canta mai.

Cosa contiene:
    auto_move(game, rng)   la carta da giocare per chi è di turno, per esempio
                           PlayCardAction(1, Card(Suit.DENARI, Rank.SIX))

DA DOVE ARRIVANO I DATI: la stanza (app/realtime/room.py) chiama auto_move quando il
timer del turno scade, con la partita in corso (self.game) e il suo generatore di
numeri a caso (self._rng); poi applica la mossa come se l'avesse fatta il giocatore.
"""

import random
import secrets

from app.game.engine.actions import PlayCardAction
from app.game.engine.errors import EngineError
from app.game.engine.game import game_legal_actions
from app.game.engine.rules import MARIANNA, RuleSet
from app.game.engine.state import GameState


def auto_move(game: GameState, rng: random.Random | None = None, rules: RuleSet = MARIANNA) -> PlayCardAction:
    """La mossa per chi è di turno. In gioco rng è None (secrets.SystemRandom); i test passano un seme fisso.

    In parole semplici:
        auto_move(game, rng)
        Sceglie la carta "che costa meno" tra quelle che si possono giocare e la
        restituisce come azione, senza applicarla.

        game:  la partita in corso (GameState di state.py); dentro ci sono la mano,
               chi è di turno e la briscola. Arriva dalla stanza.
        rng:   facoltativo (se manca vale None). Il generatore di numeri a caso che
               sceglie tra carte ugualmente buone: la stanza passa il suo, i test un
               random.Random con un seme fisso. Con None si usa secrets.SystemRandom.
        rules: facoltativo, le regole del gioco; se manca vale MARIANNA.

        Restituisce: PlayCardAction(posto di chi è di turno, carta scelta).
        Se la partita è finita lancia EngineError.
    """
    if game.finished:
        raise EngineError("La partita è finita.")
    seat = game.hand.turn_seat
    # cards: le carte che chi è di turno può giocare adesso (le decide game.py)
    cards = game_legal_actions(game, seat, rules).play
    trump = game.hand.trump

    def key(card):
        """Il "costo" di una carta: più è piccolo, più la carta conviene buttarla.

        In parole semplici:
            key(card)
            Una funzione scritta dentro auto_move, che legge trump da lei.
            Restituisce tre valori, confrontati uno dopo l'altro (prima il primo, a
            parità il secondo, poi il terzo):
              1. i punti della carta              (meno punti si regalano, meglio è)
              2. se è di briscola (True o False)  (False viene prima: si tiene la briscola)
              3. la forza nella presa             (si butta la più debole)
            Per esempio (0, False, 1) per un 2 non di briscola.
        """
        return (card.points, card.suit == trump, card.strength)

    # best: il costo più basso tra le carte giocabili (ricerca del minimo, come in C);
    # min(a, b) restituisce il più piccolo dei due
    best = key(cards[0])
    for card in cards:
        best = min(best, key(card))

    # candidates: tutte le carte con quel costo, nell'ordine in cui le dà game.py.
    # L'ordine conta: con un seme fisso i test si aspettano sempre la stessa scelta.
    candidates = []
    for card in cards:
        if key(card) == best:
            candidates.append(card)

    if rng is None:
        rng = secrets.SystemRandom()
    # choice: una a caso tra le candidate (quasi sempre ce n'è una sola)
    return PlayCardAction(seat, rng.choice(candidates))
