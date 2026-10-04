"""Mossa della CPU (P68, D43): strategia "simulazione".

La CPU sceglie guardando **solo la propria vista** (player_view, contratto 3.3) e quello
che ricorda delle viste di prima nella stessa mano (CpuMemory: le carte uscite, che ogni
giocatore al tavolo ha visto). Non vede mai le carte degli altri né il mazzo.

Strategia (D43, decisa il 04/10/2026):
- cala le carte appena può (P84, D45);
- canta sempre quando può: se può cantare più semi, sceglie quale cantare prima come sceglie
  le carte (qui sotto);
- altrimenti immagina molte distribuzioni possibili delle carte che non vede (le carte non
  ancora uscite; Re e Cavallo cantati dall'avversario e non giocati sono per forza in mano
  a lui), gioca ogni mano immaginata fino in fondo per ogni sua mossa possibile e sceglie la
  mossa che in media le fa guadagnare più punti dell'avversario. Nelle mani immaginate
  tutti giocano come il "giocatore medio" (heuristic_move, la prima CPU del 30/09/2026);
- quando le carte nascoste sono tutte note (1v1 a mazzo finito: sono quelle in mano
  all'avversario) calcola la mossa migliore in modo esatto, supponendo che anche
  l'avversario giochi al meglio. Nel calcolo esatto chi può cantare canta sempre.
A parità sceglie a caso.

Il numero di mani immaginate si ricava dalle carte che restano (SIMULATED_PLAYS), non dal
tempo: nella stessa situazione e con lo stesso rng la mossa è sempre la stessa.
"""

import random
import secrets
from dataclasses import dataclass, field

from app.game.engine.actions import Action, LayDownAction, PlayCardAction, SingAction
from app.game.engine.cards import Card, Rank, Suit
from app.game.engine.deck import full_deck
from app.game.engine.errors import EngineError
from app.game.engine.game import apply
from app.game.engine.singing import Sing, singable_suits
from app.game.engine.state import TEAMS, HandState, LastTrick, TrickPlay, team_of

TRUMP_WORTH = 10  # giocatore medio: punti della presa per cui vale la pena usare una briscola
SIMULATED_PLAYS = 6000  # carte giocate in tutto nelle mani immaginate per una mossa (circa 0,2 s)
MIN_WORLDS = 20
MAX_WORLDS = 200


@dataclass
class CpuMemory:
    """Quello che la CPU ricorda della mano in corso: le carte uscite, prese dalle sue viste.

    La stanza le fa vedere ogni vista nuova (see): nella presa in corso e nell'ultima presa
    chiusa passano tutte le carte giocate, quindi la memoria è quella di un giocatore attento.
    """

    hand_number: int | None = None
    seen: set[Card] = field(default_factory=set)

    def see(self, view: dict) -> None:
        if view["hand_number"] != self.hand_number:
            self.hand_number = view["hand_number"]
            self.seen = set()
        for play in view["trick"]["cards"]:
            self.seen.add(_card(play["card"]))
        if view["last_trick"] is not None:
            self.seen.update(_card(play["card"]) for play in view["last_trick"]["cards"])


def cpu_move(view: dict, rng: random.Random | None = None, memory: CpuMemory | None = None) -> Action:
    """La mossa della CPU dalla sua vista. In gioco rng è None; i test passano un seme fisso."""
    seat = view["you"]["seat"]
    legal = view["legal"]
    if not legal["play"]:
        raise EngineError("Non è il turno della CPU.")
    if rng is None:
        rng = secrets.SystemRandom()
    if legal["lay_down"]:
        return LayDownAction(seat)  # P84: prende tutte le prese rimaste, meglio di così non si fa
    if memory is None:
        memory = CpuMemory()
    memory.see(view)
    if legal["sing"]:
        moves = [SingAction(seat, Suit(suit)) for suit in legal["sing"]]
    else:
        moves = [PlayCardAction(seat, _card(card)) for card in legal["play"]]
    if len(moves) == 1:
        return moves[0]
    worlds = _worlds(view, memory, rng)
    if worlds is None:
        return heuristic_move(view, rng)  # memoria incompleta: meglio non immaginare mani sbagliate
    if len(worlds) == 1:
        scores = [_gain_of(worlds[0], move, seat) + _exact_gain(apply(worlds[0], move), seat) for move in moves]
    else:
        scores = [0] * len(moves)
        for world in worlds:
            seed = rng.random()  # stesse scelte a caso per tutte le mosse: si confrontano meglio
            for index, move in enumerate(moves):
                after = apply(world, move)
                scores[index] += _gain_of(world, move, seat) + _rollout_gain(after, seat, random.Random(seed))
    best = max(scores)
    return rng.choice([move for move, score in zip(moves, scores, strict=True) if score == best])


# --- Mani immaginate ---------------------------------------------------------------


def _worlds(view: dict, memory: CpuMemory, rng: random.Random) -> list[HandState] | None:
    """Le mani possibili dal punto di vista della CPU; una sola se le carte nascoste sono tutte note.

    None se i conti non tornano (la memoria non ha tutte le carte uscite).
    """
    seat = view["you"]["seat"]
    players = len(view["players"])
    hand = tuple(_card(card) for card in view["hand"])
    trick = tuple(TrickPlay(play["seat"], _card(play["card"])) for play in view["trick"]["cards"])
    on_table = {play.card for play in trick}
    sings = tuple(Sing(done["seat"], Suit(done["suit"]), done["points"]) for done in view["sings"])
    gone = memory.seen - on_table
    sizes = {entry["seat"]: entry["cards_in_hand"] for entry in view["players"] if entry["seat"] != seat}
    # Re e Cavallo cantati da un altro e non ancora giocati sono in mano a lui
    known: dict[int, list[Card]] = {other: [] for other in sizes}
    for done in sings:
        if done.seat != seat:
            for rank in (Rank.KING, Rank.KNIGHT):
                card = Card(done.suit, rank)
                if card not in memory.seen and card not in known[done.seat]:
                    known[done.seat].append(card)
    placed = {card for cards in known.values() for card in cards}
    pool = [card for card in full_deck() if card not in memory.seen and card not in hand and card not in placed]
    if len(pool) != sum(sizes.values()) - len(placed) + view["deck_count"]:
        return None
    if any(len(known[other]) > sizes[other] for other in sizes):
        return None
    last = view["last_trick"]
    last_trick = None if last is None else LastTrick(
        last["winner_seat"], tuple(TrickPlay(play["seat"], _card(play["card"])) for play in last["cards"]))
    # Le carte uscite stanno tutte nelle prese della squadra 0: conta solo quanto si guadagna da qui
    captured = (tuple(gone), *((),) * (TEAMS - 1))
    hidden_holders = [other for other in sizes if sizes[other] > len(known[other])]
    if view["deck_count"] == 0 and len(hidden_holders) <= 1:
        count = 1  # niente di nascosto: le carte che mancano sono tutte dell'unico che ne ha
    else:
        remaining = len(hand) + sum(sizes.values()) + view["deck_count"]
        count = max(MIN_WORLDS, min(MAX_WORLDS, SIMULATED_PLAYS // (len(view["legal"]["play"]) * remaining)))
    worlds = []
    for _ in range(count):
        cards = list(pool)
        rng.shuffle(cards)
        hands = []
        for index in range(players):
            if index == seat:
                hands.append(hand)
                continue
            take = sizes[index] - len(known[index])
            hands.append((*known[index], *cards[:take]))
            cards = cards[take:]
        worlds.append(HandState(
            num_players=players, hands=tuple(hands), deck=tuple(cards), trick=trick,
            leader_seat=view["trick"]["leader_seat"], turn_seat=seat, sings=sings,
            captured=captured, last_trick=last_trick,
        ))
    return worlds


def _gain(state: HandState, seat: int) -> int:
    """Punti della squadra della CPU meno quelli degli avversari, nelle prese e nei canti."""
    points = [sum(card.points for card in taken) for taken in state.captured]
    for done in state.sings:
        points[team_of(done.seat)] += done.points
    mine = team_of(seat)
    return sum(value if team == mine else -value for team, value in enumerate(points))


def _gain_of(state: HandState, move: Action, seat: int) -> int:
    return _gain(apply(state, move), seat) - _gain(state, seat)


def _rollout_gain(state: HandState, seat: int, rng: random.Random) -> int:
    start = _gain(state, seat)
    while not state.finished:
        state = apply(state, _policy(state, rng))
    return _gain(state, seat) - start


def _exact_gain(state: HandState, seat: int) -> int:
    """Quanto guadagna ancora la squadra della CPU se tutti giocano al meglio (carte tutte note)."""
    team = team_of(seat)
    known: dict[tuple, int] = {}

    def future(state: HandState) -> int:
        if state.finished:
            return 0
        key = (state.hands, state.trick, state.sings, state.turn_seat)
        if key not in known:
            before = _gain(state, seat)
            values = []
            for move in _exact_moves(state):
                after = apply(state, move)
                values.append(_gain(after, seat) - before + future(after))
            known[key] = max(values) if team_of(state.turn_seat) == team else min(values)
        return known[key]

    return future(state)


def _exact_moves(state: HandState) -> list[Action]:
    seat = state.turn_seat
    suits = _singable(state)
    if suits:
        return [SingAction(seat, suit) for suit in suits]
    return [PlayCardAction(seat, card) for card in state.hands[seat]]


def _singable(state: HandState) -> list[Suit]:
    return singable_suits(hand=state.hands[state.turn_seat], sings=state.sings, played_cards=state.played_cards,
                          deck_count=len(state.deck), is_turn=True, first_trick=state.last_trick is None)


def _policy(state: HandState, rng: random.Random) -> Action:
    """Il giocatore medio sullo stato della mano: le stesse scelte di heuristic_move."""
    seat = state.turn_seat
    hand = list(state.hands[seat])
    suits = _singable(state)
    if suits:
        return SingAction(seat, _best(suits, lambda suit: (-_count(hand, suit), -_strength(hand, suit)), rng))
    pairs = _open_pairs(hand, {done.suit for done in state.sings})
    trick = [play.card for play in state.trick]
    if trick:
        card = _answer(hand, trick, state.trump, not state.deck, pairs, rng)
    else:
        card = _lead(hand, state.trump, not state.deck, pairs, rng)
    return PlayCardAction(seat, card)


# --- Giocatore medio (la prima CPU, 30/09/2026) ------------------------------------


def heuristic_move(view: dict, rng: random.Random | None = None) -> Action:
    """Il "giocatore medio": regole fisse, senza memoria.

    - canta appena può; con più semi, quello di cui ha più carte (il primo canto fa la briscola);
    - quando risponde: se può prendere senza briscola prende, con la carta più economica;
      con la briscola prende solo se la presa vale almeno TRUMP_WORTH punti (a mazzo
      finito basta che valga qualcosa); altrimenti scarta la carta che vale meno;
    - quando apre gioca la carta che vale meno e tiene Assi, Tre e briscole; a mazzo finito
      apre con la briscola più forte;
    - scartando o aprendo evita di rompere una coppia Re e Cavallo ancora da cantare;
    - cala le carte appena può (P84, D45), dopo aver cantato.
    A parità sceglie a caso.
    """
    seat = view["you"]["seat"]
    legal = view["legal"]
    if not legal["play"]:
        raise EngineError("Non è il turno della CPU.")
    if rng is None:
        rng = secrets.SystemRandom()
    hand = [_card(card) for card in view["hand"]]
    if legal["sing"]:
        suits = [Suit(suit) for suit in legal["sing"]]
        return SingAction(seat, _best(suits, lambda suit: (-_count(hand, suit), -_strength(hand, suit)), rng))
    if legal["lay_down"]:
        return LayDownAction(seat)

    playable = [_card(card) for card in legal["play"]]
    trump = None if view["trump"] is None else Suit(view["trump"])
    deck_empty = view["deck_count"] == 0
    pairs = _open_pairs(hand, {Suit(done["suit"]) for done in view["sings"]})
    trick = [_card(play["card"]) for play in view["trick"]["cards"]]
    if trick:
        card = _answer(playable, trick, trump, deck_empty, pairs, rng)
    else:
        card = _lead(playable, trump, deck_empty, pairs, rng)
    return PlayCardAction(seat, card)


def _answer(playable, trick, trump, deck_empty, pairs, rng):
    lead = trick[0].suit
    best = trick[0]
    for card in trick[1:]:
        if _beats(card, best, lead, trump):
            best = card
    worth = sum(card.points for card in trick)
    winners = [card for card in playable if _beats(card, best, lead, trump)]
    plain = [card for card in winners if card.suit != trump]
    if plain:
        return _best(plain, lambda card: (card.points, card.strength), rng)
    trumps = [card for card in winners if card.suit == trump]
    if trumps and (worth >= TRUMP_WORTH or (deck_empty and worth > 0)):
        return _best(trumps, lambda card: (card.points, card.strength), rng)
    return _discard(playable, trump, pairs, rng)


def _lead(playable, trump, deck_empty, pairs, rng):
    trumps = [card for card in playable if card.suit == trump]
    if deck_empty and trumps:
        return _best(trumps, lambda card: -card.strength, rng)
    return _discard(playable, trump, pairs, rng)


def _discard(playable, trump, pairs, rng):
    """La carta che costa meno: pochi punti, non briscola, debole, senza rompere una coppia."""
    return _best(playable, lambda card: (card in pairs, card.points, card.suit == trump, card.strength), rng)


def _beats(card, best, lead, trump):
    """Stessa regola di trick.py: vince la briscola più forte, poi la più forte del seme di uscita."""
    def rank(c):
        return (c.suit == trump, c.suit == lead, c.strength)
    return rank(card) > rank(best)


def _open_pairs(hand, sung):
    """Re e Cavallo dello stesso seme ancora in mano e non cantati: meglio non giocarli."""
    cards = set(hand)
    pairs = set()
    for suit in Suit:
        king, knight = Card(suit, Rank.KING), Card(suit, Rank.KNIGHT)
        if suit not in sung and king in cards and knight in cards:
            pairs |= {king, knight}
    return pairs


def _best(items, key, rng):
    lowest = min(key(item) for item in items)
    return rng.choice([item for item in items if key(item) == lowest])


def _count(hand, suit):
    return sum(card.suit == suit for card in hand)


def _strength(hand, suit):
    return sum(card.strength for card in hand if card.suit == suit)


def _card(data: dict) -> Card:
    return Card(Suit(data["suit"]), Rank(data["rank"]))
