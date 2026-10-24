"""Svolgimento di una mano (P13) e della partita intera (P14).

Regole in docs/REGOLE-GIOCO.md, "Svolgimento di una mano", "Chi comincia" e
"Punteggio e fine partita".

Mano: apply(stato, azione) -> nuovo stato; legal_actions(stato) -> le mosse di chi è di turno.
Partita: new_game, apply_game e game_legal_actions, che usano quelle della mano.
Una mossa non valida solleva InvalidMoveError (NotYourTurnError fuori turno) e lo stato
di partenza resta com'è, perché è immutabile.

Cosa contiene:
    new_hand(num_players, first_seat, deck)     distribuisce una mano, per esempio new_hand(2, 0, deck)
    LegalActions                                le mosse ammesse: carte, semi da cantare, calata
    partner_cards_visible(state)                si vedono le carte del compagno? (2v2, D46)
    legal_actions(state, seat)                  le mosse ammesse per un posto nella mano
    apply(state, action)                        la mano dopo una mossa, per esempio apply(state, PlayCardAction(0, card))
    hand_result(state)                          i punti di una mano finita
    new_game(num_players, target_score, rng)    una partita nuova, per esempio new_game(2, 300)
    game_legal_actions(game, seat)              come legal_actions, ma per la partita
    apply_game(game, action, rng)               la partita dopo una mossa (con il cambio di mano)

DA DOVE ARRIVANO I DATI: la stanza (app/realtime/room.py) crea la partita con
new_game e a ogni mossa (del giocatore, della mossa automatica o della CPU) chiama
apply_game; views.py usa game_legal_actions, hand_result e partner_cards_visible per
costruire la vista di ogni giocatore.
"""

import random
import secrets
from collections.abc import Sequence

# replace: crea una copia di una dataclass "congelata" (frozen) con alcuni campi
# cambiati, per esempio replace(state, turn_seat=1). È il modo di "modificare" uno
# stato immutabile: l'originale resta com'è, si ottiene uno stato nuovo.
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

    In parole semplici:
        new_hand(num_players, first_seat, deck)
        Le prime 5 carte del mazzo vanno al posto 0, le 5 dopo al posto 1, e così via;
        quelle che restano sono il mazzo da cui si pesca.

        num_players: 2 o 4. Arriva da new_game o apply_game, qui sotto.
        first_seat:  il posto di chi gioca per primo, da 0 a num_players - 1.
        deck:        le 40 carte già mescolate (shuffled_deck di deck.py); i test
                     possono passarne un ordine scelto da loro.
        rules:       facoltativo, se manca vale MARIANNA.

        Restituisce: lo stato della mano appena distribuita (HandState di state.py).
    """
    if num_players not in rules.player_counts:
        raise EngineError("Si gioca in 2 o in 4.")
    if first_seat < 0 or first_seat >= num_players:
        raise EngineError("Posto di partenza non valido.")
    # Il mazzo deve avere esattamente le 40 carte: stessa lunghezza e stesse carte
    # (confrontate come insiemi, cioè senza guardare l'ordine)
    if len(deck) != len(full_deck()) or set(deck) != set(full_deck()):
        raise EngineError("Il mazzo deve avere le 40 carte, ognuna una volta.")

    # hands: le carte di ogni posto. deck[a:b] è una "fetta" del mazzo, dalle carte
    # in posizione a fino a b esclusa: per il posto 1 con 5 carte, deck[5:10]
    size = rules.hand_size
    hands = []
    for seat in range(num_players):
        hands.append(tuple(deck[seat * size:(seat + 1) * size]))

    return HandState(
        num_players=num_players,
        hands=tuple(hands),
        # il resto del mazzo, dopo le carte distribuite
        deck=tuple(deck[num_players * size:]),
        trick=(),
        leader_seat=first_seat,
        turn_seat=first_seat,
        sings=(),
        # ((),) * TEAMS: una tupla con dentro una tupla vuota per ogni squadra, cioè
        # ((), ()): nessuna carta presa
        captured=((),) * TEAMS,
        last_trick=None,
    )


# @dataclass(frozen=True): costruttore automatico e campi che non si cambiano più
# (vedi il commento in cards.py)
@dataclass(frozen=True)
class LegalActions:
    """Le mosse che un posto può fare adesso: diventano legal nella vista.

    In parole semplici:
        LegalActions(play=(carta1, carta2), sing=(Suit.SPADE,), lay_down=False)
        play:     le carte che si possono giocare
        sing:     i semi che si possono cantare, nell'ordine fisso di Suit
        lay_down: True se si possono calare le carte (P84); se non si passa vale False
    """

    play: tuple[Card, ...]
    sing: tuple[Suit, ...]  # nell'ordine fisso di Suit
    lay_down: bool = False  # "Cala le carte" (P84)


def partner_cards_visible(state: HandState) -> bool:
    """D46 (P92): nel 2v2, con la briscola fissata e il mazzo finito, ognuno vede le carte del compagno.

    Vale da quando ci sono tutti e due, in qualunque ordine arrivino, fino a fine mano;
    senza briscola mai. Nel 1v1 non c'è un compagno.

    In parole semplici:
        partner_cards_visible(state)
        state: lo stato della mano. Arriva da views.py e dalla stanza.
        Restituisce True solo se valgono tutte e quattro le condizioni: 2v2, mano non
        finita, briscola fissata, mazzo vuoto. È l'unica eccezione a "mai le carte
        degli altri" (P15): decide solo questa funzione.
    """
    if state.num_players != 4:
        return False
    if state.finished:
        return False
    if state.trump is None:
        return False
    return len(state.deck) == 0


def _in_first_trick(state: HandState) -> bool:
    """Prima presa della mano: nessuna presa chiusa, e last_trick riparte da None a ogni mano (P58).

    In parole semplici:
        _in_first_trick(state)
        True finché nella mano non si è chiusa nessuna presa: lì nessuno canta (P64).
        La usano legal_actions e _apply_sing.
    """
    return state.last_trick is None


def legal_actions(state: HandState, seat: int, rules: RuleSet = MARIANNA) -> LegalActions:
    """Le mosse ammesse per quel posto adesso: vuote se non è il suo turno.

    In parole semplici:
        legal_actions(state, seat)
        state: lo stato della mano.
        seat:  il posto di cui si vogliono le mosse, da 0 a 3. Arriva da
               game_legal_actions, quindi dalla vista (views.py) o dalla stanza.
        rules: facoltativo, se manca vale MARIANNA.

        Restituisce: LegalActions con le carte giocabili (tutte quelle in mano,
        perché non c'è obbligo di rispondere al seme), i semi da cantare e se si può
        calare. Un test controlla che siano esattamente le mosse accettate da apply.
    """
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
    """La mano dopo una mossa: il cuore del motore.

    In parole semplici:
        apply(state, action)
        Controlla che la mossa sia fatta bene e da chi è di turno, poi la passa alla
        funzione giusta per il suo tipo: _apply_sing, _apply_lay_down o _apply_play.

        state:  lo stato della mano prima della mossa. Arriva da apply_game.
        action: la mossa, una delle tre azioni di actions.py, per esempio
                PlayCardAction(0, Card(Suit.COPPE, Rank.ACE)).
        rules:  facoltativo, se manca vale MARIANNA.

        Restituisce: lo stato nuovo. Quello di partenza non cambia mai; se la mossa
        non è valida lancia InvalidMoveError (o NotYourTurnError).
    """
    # isinstance con la barra |: "è una di queste tre classi?"
    if not isinstance(action, PlayCardAction | SingAction | LayDownAction):
        raise InvalidMoveError("Mossa non valida.")
    seat = action.seat
    # In Python True e False sono anche numeri (1 e 0): un posto True si rifiuta a parte
    if isinstance(seat, bool) or not isinstance(seat, int) or seat < 0 or seat >= state.num_players:
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
    """La mano dopo un canto.

    In parole semplici:
        _apply_sing(state, action, rules)
        Chiede a sing di singing.py se il canto si può fare (se no, lancia l'errore
        con il motivo) e aggiunge il canto in fondo a state.sings.
        Arriva da apply, che ha già controllato posto e turno.
    """
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
    # Dopo il canto il turno resta a chi ha cantato: deve ancora giocare la carta.
    # state.sings + (done,): una tupla nuova con il canto in fondo; (done,) è una
    # tupla di un elemento solo (la virgola serve: (done) sarebbe solo done)
    return replace(state, sings=state.sings + (done,))


def _apply_lay_down(state: HandState, action: LayDownAction, rules: RuleSet) -> HandState:
    """Cala le carte (P84): la mano finisce e la squadra di chi cala prende tutte le carte rimaste.

    In parole semplici:
        _apply_lay_down(state, action, rules)
        Se calare non è permesso adesso (can_lay_down di lay_down.py) rifiuta la
        mossa. Altrimenti: il compagno canta i semi che poteva (partner_sings), tutte
        le carte in mano finiscono tra le prese della squadra di chi cala, le mani
        si svuotano e la mano finisce (turn_seat None). Arriva da apply.
    """
    if not can_lay_down(state, action.seat, rules):
        raise InvalidMoveError("Adesso non puoi calare le carte.")
    # added: i canti fatti dal server per il compagno (D45), una tupla di Sing
    added = partner_sings(state, action.seat, rules)
    team = team_of(action.seat)

    # remaining: tutte le carte ancora in mano, di tutti i posti
    remaining = []
    for hand in state.hands:
        remaining.extend(hand)

    # captured: le prese delle squadre; quella di chi cala riceve in fondo le carte rimaste
    captured = []
    for index in range(len(state.captured)):
        taken = state.captured[index]
        if index == team:
            captured.append(taken + tuple(remaining))
        else:
            captured.append(taken)

    return replace(
        state,
        # ((),) * state.num_players: una tupla vuota per ogni posto (mani vuote)
        hands=((),) * state.num_players,
        turn_seat=None,
        sings=state.sings + added,
        captured=tuple(captured),
        # si ricordano le mani com'erano, per mostrarle scoperte al tavolo (P85)
        laid_down=LaidDown(action.seat, state.hands, added),
    )


def _apply_play(state: HandState, action: PlayCardAction) -> HandState:
    """La mano dopo una carta giocata.

    In parole semplici:
        _apply_play(state, action)
        Toglie la carta dalla mano di chi la gioca e la mette nella presa. Se la
        presa non è completa passa il turno al posto dopo; se è completa la chiude
        (_close_trick). Arriva da apply.
    """
    seat = action.seat
    card = action.card
    hand = state.hands[seat]
    if not isinstance(card, Card) or card not in hand:
        raise InvalidMoveError("Non hai questa carta in mano.")

    # new_hand_cards: la mano di chi gioca senza quella carta (le altre nello stesso ordine)
    new_hand_cards = []
    for other in hand:
        if other != card:
            new_hand_cards.append(other)
    hands = _with_hand(state.hands, seat, tuple(new_hand_cards))

    # trick: la presa in corso con la carta nuova in fondo
    trick = state.trick + (TrickPlay(seat, card),)
    if len(trick) < state.num_players:
        return replace(state, hands=hands, trick=trick, turn_seat=_next_seat(seat, state.num_players))
    return _close_trick(replace(state, hands=hands, trick=trick))


def _close_trick(state: HandState) -> HandState:
    """Presa completa: la vince chi deve, poi si pesca e chi ha preso apre la presa dopo.

    In parole semplici:
        _close_trick(state)
        state: la mano con la presa appena completata (tutte le carte sul tavolo).
               Arriva da _apply_play.
        1. trick_winner di trick.py dice chi vince;
        2. le carte della presa vanno IN FONDO alle prese della sua squadra (la CPU
           conta su quest'ordine, _step_gain di cpu.py);
        3. se il mazzo non è finito, ognuno pesca una carta, cominciando da chi ha vinto;
        4. chi ha vinto apre la presa dopo; se nessuno ha più carte la mano è finita.

        Restituisce: lo stato nuovo, con last_trick = la presa appena chiusa.
    """
    # trick_cards: solo le carte della presa, nell'ordine di gioco
    trick_cards = []
    for play in state.trick:
        trick_cards.append(play.card)
    position = trick_winner(trick_cards, state.trump)
    winner = state.trick[position].seat
    team = team_of(winner)

    # captured: alla squadra di chi vince si aggiungono le carte della presa, in fondo
    captured = []
    for index in range(len(state.captured)):
        taken = state.captured[index]
        if index == team:
            captured.append(taken + tuple(trick_cards))
        else:
            captured.append(taken)

    # Pesca: prima chi ha vinto la presa, poi gli altri in ordine di turno.
    # Il mazzo (30 carte nel 1v1, 20 nel 2v2) finisce sempre a fine giro.
    hands = state.hands
    deck = state.deck
    if len(deck) > 0:
        for step in range(state.num_players):
            drawer = _next_seat(winner, state.num_players, step)
            # la prima carta del mazzo va in fondo alla mano di chi pesca
            hands = _with_hand(hands, drawer, hands[drawer] + (deck[0],))
            # deck[1:]: il mazzo senza la prima carta
            deck = deck[1:]

    # finished: True se tutte le mani sono vuote (la mano è finita)
    finished = True
    for cards in hands:
        if len(cards) > 0:
            finished = False

    # turn_seat: chi apre la presa dopo; None se la mano è finita
    if finished:
        turn_seat = None
    else:
        turn_seat = winner

    return replace(
        state,
        hands=hands,
        deck=deck,
        trick=(),
        leader_seat=winner,
        turn_seat=turn_seat,
        captured=tuple(captured),
        last_trick=LastTrick(winner, state.trick),
    )


def hand_result(state: HandState, rules: RuleSet = MARIANNA) -> HandResult:
    """Punti della mano per squadra: carte prese più canti. L'ultima presa non dà bonus.

    In parole semplici:
        hand_result(state)
        state: una mano finita. Arriva da apply_game e da views.py (P67).
        rules: facoltativo, se manca vale MARIANNA.

        Restituisce: HandResult con i punti delle carte e dei canti di ogni squadra,
        per esempio card_points (55, 65) e sing_points (40, 0). Se la mano non è
        finita lancia EngineError.
    """
    if not state.finished:
        raise EngineError("La mano non è ancora finita.")

    # card_points: per ogni squadra, la somma dei punti delle carte che ha preso.
    # Una mano finita ha sempre almeno una presa chiusa: anche per calare il mazzo deve essere finito
    card_points = []
    for taken in state.captured:
        total = 0
        for card in taken:
            total = total + card.points
        card_points.append(total)

    # Calando, l'ultima presa sarebbe della squadra di chi cala
    if state.laid_down is None:
        last_winner = state.last_trick.winner_seat
    else:
        last_winner = state.laid_down.seat
    card_points[team_of(last_winner)] += rules.last_trick_bonus

    # sing_points: per ogni squadra, la somma dei suoi canti ([0] * TEAMS = [0, 0])
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

    In parole semplici:
        new_game(num_players, target_score, rng)
        num_players:  2 (1v1) o 4 (2v2). Arriva dalla stanza (app/realtime/room.py),
                      che lo prende dalla modalità scelta nella home.
        target_score: i punti per vincere, 150, 300 o 500; altri valori si rifiutano.
        rng:          facoltativo (None in gioco). Il generatore di numeri a caso per
                      chi comincia e per il mazzo; i test passano random.Random(seme).
        rules:        facoltativo, se manca vale MARIANNA.

        Restituisce: la partita con la prima mano già distribuita (GameState).
    """
    if num_players not in rules.player_counts:
        raise EngineError("Si gioca in 2 o in 4.")
    if (
        isinstance(target_score, bool)
        or not isinstance(target_score, int)
        or target_score not in rules.target_scores
    ):
        # allowed: i punteggi tranne l'ultimo, separati da una virgola, per esempio
        # "150, 300"; [:-1] è la tupla senza l'ultimo elemento, [-1] è l'ultimo
        allowed_list = []
        for score in rules.target_scores[:-1]:
            allowed_list.append(str(score))
        allowed = ", ".join(allowed_list)
        raise EngineError(f"Punteggio non valido: si gioca a {allowed} o {rules.target_scores[-1]}.")
    if rng is None:
        rng = secrets.SystemRandom()
    # first_seat: un posto a caso tra 0 e num_players - 1
    first_seat = rng.randrange(num_players)
    return GameState(
        num_players=num_players,
        target_score=target_score,
        hand_number=1,
        first_seat=first_seat,
        hand=new_hand(num_players, first_seat, shuffled_deck(rng), rules),
        # (0,) * TEAMS: (0, 0), nessun punto
        scores=(0,) * TEAMS,
        last_hand=None,
        result=None,
    )


def game_legal_actions(game: GameState, seat: int, rules: RuleSet = MARIANNA) -> LegalActions:
    """Le mosse ammesse per un posto nella partita: nessuna a partita finita.

    In parole semplici:
        game_legal_actions(game, seat)
        Come legal_actions, ma riceve la partita intera. La usano views.py (legal
        nella vista), auto_move.py e la CPU.
    """
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

    In parole semplici:
        apply_game(game, action, rng)
        game:   la partita prima della mossa. Arriva dalla stanza (self.game).
        action: la mossa (vedi apply).
        rng:    facoltativo; serve solo a mescolare il mazzo della mano dopo.
        rules:  facoltativo, se manca vale MARIANNA.

        Restituisce: la partita nuova. Tre casi:
          1. la mano continua: cambia solo la mano;
          2. la mano finisce e qualcuno arriva al punteggio: la partita finisce (result);
          3. la mano finisce e nessuno ci arriva: si distribuisce la mano dopo.
    """
    if game.finished:
        raise InvalidMoveError("La partita è finita.")
    hand = apply(game.hand, action, rules)
    if not hand.finished:
        return replace(game, hand=hand)

    # scores: i punteggi di prima più i punti di questa mano, squadra per squadra.
    # zip prende un valore da ciascuna tupla alla volta; strict=True dà errore se le
    # due tuple non sono lunghe uguali
    done = hand_result(hand, rules)
    scores_list = []
    for score, points in zip(game.scores, done.totals, strict=True):
        scores_list.append(score + points)
    scores = tuple(scores_list)

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
    """Vince chi arriva ad almeno N; se ci arrivano entrambi il più alto; a parità è pareggio.

    In parole semplici:
        _game_result(scores, target_score)
        scores:       i punteggi delle due squadre, per esempio (310, 280).
        target_score: i punti per vincere, per esempio 300. Arrivano da apply_game.

        Restituisce: None se nessuno è arrivato al punteggio (la partita continua);
        GameResult(winner_team=0) nell'esempio; GameResult(winner_team=None) se le
        due squadre sono pari sopra il punteggio.
    """
    top = max(scores)
    if top < target_score:
        return None
    # leaders: le squadre con il punteggio più alto (una sola, o due se sono pari)
    leaders = []
    for team in range(len(scores)):
        if scores[team] == top:
            leaders.append(team)
    if len(leaders) == 1:
        return GameResult(winner_team=leaders[0])
    return GameResult(winner_team=None)


def _next_seat(seat: int, num_players: int, steps: int = 1) -> int:
    """Il posto che gioca dopo, girando verso destra.

    In parole semplici:
        _next_seat(seat, num_players, steps)
        Per esempio _next_seat(3, 4) = 0: dopo l'ultimo posto si torna al primo (%).
        steps: facoltativo, quanti posti avanti (se manca vale 1); lo usa la pesca
        di _close_trick, che parte da chi ha vinto (steps 0) e gira.
    """
    return (seat + steps) % num_players


def _with_hand(hands: tuple, seat: int, cards: tuple) -> tuple:
    """Le mani di tutti, con quella di un posto sostituita.

    In parole semplici:
        _with_hand(hands, seat, cards)
        hands: le mani di tutti i posti, una tupla di tuple.
        seat:  il posto di cui cambia la mano.
        cards: la mano nuova di quel posto.
        Restituisce una tupla nuova: le mani degli altri restano le stesse, perché le
        tuple non si cambiano. La usano _apply_play e la pesca di _close_trick.
    """
    new_hands = []
    for index in range(len(hands)):
        if index == seat:
            new_hands.append(cards)
        else:
            new_hands.append(hands[index])
    return tuple(new_hands)
