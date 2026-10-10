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
  Nel 2v2 a mazzo finito con al massimo EXACT_MAX_CARDS carte a testa fa il calcolo esatto
  su ogni mano immaginata (P127, D50), invece di giocarla da giocatore medio.

P127 (D50, proposta di Christian del 09/10/2026): quando le mosse migliori valgono quasi
uguale (sotto la migliore di meno di TIE_SPREAD volte l'incertezza della stima, misurata
mano immaginata per mano immaginata), non decide il caso:
- da ultima nella presa gioca la carta con il risultato migliore nella presa (punti della
  sua squadra meno quelli dati agli avversari), poi una carta non di briscola, poi la più
  debole; Re e Cavalli ancora accoppiabili solo se non c'è altro;
- altrimenti evita i carichi (Asso e Tre) che possono finire agli avversari e i Re e
  Cavalli ancora accoppiabili (per il 40 e per il 20); se è costretta sacrifica prima il Re
  o il Cavallo e tiene il carico; tra le carte rimaste gioca quella stimata meglio.
A parità sceglie a caso.

P134 (D51, 10/10/2026), **solo nel 2v2** (scelta di Giuseppe: nel 1v1, dove chi risponde è
sempre l'ultimo, la CPU vinceva meno partite): da ultima il risultato della presa conta solo
le carte degli altri (se la presa è sua guadagna i loro punti; se la perde regala anche la sua
carta), così su una presa povera scarta una cartina e su una che vale prende con la carta più
bassa che basta; su una presa che vale meno di TRUMP_WORTH evita l'Asso e il Tre di briscola
(anche da ultima, aggiunta di Giuseppe) e, non da ultima, le briscole più alte di quella più
bassa che prende.

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
from app.game.engine.rules import MARIANNA
from app.game.engine.singing import Sing, singable_suits
from app.game.engine.state import TEAMS, HandState, LastTrick, TrickPlay, team_of

TRUMP_WORTH = 10  # giocatore medio: punti della presa per cui vale la pena usare una briscola
SIMULATED_PLAYS = 6000  # carte giocate in tutto nelle mani immaginate per una mossa (circa 0,2 s)
MIN_WORLDS = 20
MAX_WORLDS = 200
TIE_SPREAD = 2  # P127: "pari merito" = sotto la migliore di meno di 2 volte l'incertezza
EXACT_MAX_CARDS = 3  # P127: calcolo esatto nel 2v2 a mazzo finito fino a 3 carte a testa
EXACT_WORLDS = 6  # P127: mani immaginate con il calcolo esatto (con 3 carte a testa fino a 70 ms l'una)


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
    exact = _exact_worlds(view)
    worlds = _worlds(view, memory, rng, EXACT_WORLDS if exact else None)
    if worlds is None:
        return heuristic_move(view, rng)  # memoria incompleta: meglio non immaginare mani sbagliate
    results = []  # per ogni mano immaginata, quanto guadagna ogni mossa
    for world in worlds:
        if exact or len(worlds) == 1:
            known: dict[tuple, int] = {}  # le mosse arrivano spesso alle stesse situazioni: si calcolano una volta
            results.append([_gain_of(world, move, seat) + _exact_gain(apply(world, move), seat, known)
                            for move in moves])
            continue
        seed = rng.random()  # stesse scelte a caso per tutte le mosse: si confrontano meglio
        results.append([_gain_of(world, move, seat) + _rollout_gain(apply(world, move), seat, random.Random(seed))
                        for move in moves])
    scores = [sum(row[index] for row in results) for index in range(len(moves))]
    ties = _ties(results)
    if isinstance(moves[0], PlayCardAction) and len(ties) > 1:
        ties = _preferred(view, memory, [moves[index] for index in ties], [scores[index] for index in ties])
        return rng.choice(ties)
    best = max(scores[index] for index in ties)
    return rng.choice([moves[index] for index in ties if scores[index] == best])


# --- Pari merito (P127, D50) ---------------------------------------------------------


def _ties(results: list[list[int]]) -> list[int]:
    """Le mosse a pari merito con la migliore: sotto di meno di TIE_SPREAD volte l'incertezza.

    L'incertezza (errore standard) si misura sulla differenza con la migliore mano per mano,
    perché le mosse sono giocate sulle stesse mani immaginate. Con una mano sola (calcolo
    esatto) sono a pari merito solo le mosse che valgono uguale.
    """
    count = len(results)
    moves = len(results[0])
    totals = [sum(row[index] for row in results) for index in range(moves)]
    best = max(range(moves), key=lambda index: totals[index])
    ties = []
    for index in range(moves):
        gaps = [row[best] - row[index] for row in results]
        mean = sum(gaps) / count
        if count > 1:
            variance = sum((gap - mean) ** 2 for gap in gaps) / (count - 1)
            if mean < TIE_SPREAD * (variance / count) ** 0.5 or mean == 0:
                ties.append(index)
        elif mean == 0:
            ties.append(index)
    return ties


def _preferred(view: dict, memory: CpuMemory, moves: list[PlayCardAction], scores: list[int]) -> list[Action]:
    """Tra le carte a pari merito, quelle che un buon giocatore preferisce (vedi in cima)."""
    seat = view["you"]["seat"]
    trump = None if view["trump"] is None else Suit(view["trump"])
    plays = [(play["seat"], _card(play["card"])) for play in view["trick"]["cards"]]
    pairable = {move.card for move in moves if _pairable(move.card, view, memory)}
    two_v_two = len(view["players"]) == 4  # P134 solo nel 2v2: nel 1v1 la CPU perdeva più partite
    worth = sum(card.points for _, card in plays)
    winning_trumps = [move.card for move in moves if two_v_two and plays and worth < TRUMP_WORTH
                      and move.card.suit == trump and _winning([*plays, (seat, move.card)], trump)[0] == seat]
    if len(plays) + 1 == len(view["players"]):
        keep = [move for move in moves if move.card not in pairable] or moves

        def key(move):
            wasted = move.card in winning_trumps and move.card.points >= 10
            return (wasted, -_trick_result(plays, move.card, seat, trump, only_others=two_v_two),
                    move.card.suit == trump, move.card.strength)
        lowest = min(key(move) for move in keep)
        return [move for move in keep if key(move) == lowest]

    def penalty(move):
        if move.card.points >= 10 and (move.card in winning_trumps
                                       or not _safe_load(plays, move.card, seat, trump, view, memory)):
            return 2  # P134: un carico di briscola su una presa povera è sprecato anche se al sicuro
        if move.card in pairable:
            return 1
        if move.card in winning_trumps and move.card != min(winning_trumps, key=lambda card: card.strength):
            return 1  # P134: su una presa povera basta la briscola più bassa che prende
        return 0
    lowest = min(penalty(move) for move in moves)
    keep = [(move, score) for move, score in zip(moves, scores, strict=True) if penalty(move) == lowest]
    best = max(score for _, score in keep)
    return [move for move, score in keep if score == best]


def _trick_result(plays, card, seat, trump, only_others: bool) -> int:
    """Da ultima: punti che la presa sposta per la squadra della CPU.

    only_others (P134, D51, nel 2v2): se la presa è della sua squadra guadagna i punti delle
    carte degli altri (quelli della sua carta li avrebbe comunque); se va agli avversari regala
    tutto, compresa la sua carta. Senza (P127, nel 1v1): conta anche la sua carta se vince.
    """
    winner, _ = _winning([*plays, (seat, card)], trump)
    others = sum(played.points for _, played in plays)
    if team_of(winner) != team_of(seat):
        return -others - card.points
    return others if only_others else others + card.points


def _winning(plays, trump):
    lead = plays[0][1].suit
    best = plays[0]
    for play in plays[1:]:
        if _beats(play[1], best[1], lead, trump):
            best = play
    return best


def _safe_load(plays, card, seat, trump, view, memory) -> bool:
    """Un carico (Asso, Tre) giocato non da ultima resta di sicuro alla squadra della CPU?

    Sì se, giocata la carta, la presa è della sua squadra e nessuna carta che la CPU non vede
    (non uscita, non in mano sua né scoperta del compagno) può batterla.
    """
    all_plays = [*plays, (seat, card)]
    winner, best = _winning(all_plays, trump)
    if team_of(winner) != team_of(seat):
        return False
    lead = all_plays[0][1].suit
    return not any(_beats(other, best, lead, trump) for other in _unseen(view, memory))


def _unseen(view: dict, memory: CpuMemory) -> list[Card]:
    known = memory.seen | {_card(card) for card in view["hand"]}
    known |= {_card(card) for card in view.get("partner_hand") or ()}
    known |= {_card(play["card"]) for play in view["trick"]["cards"]}
    return [card for card in full_deck() if card not in known]


def _pairable(card: Card, view: dict, memory: CpuMemory) -> bool:
    """Un Re o un Cavallo che si può ancora cantare (40 o 20) insieme all'altra carta del seme.

    Il seme non è cantato, l'altra carta non è uscita e la CPU può ancora averla: in mano,
    oppure ancora da pescare (non scoperta in mano al compagno); a mazzo finito deve averla in
    mano e restare con almeno le carte che servono per cantare.
    """
    if card.rank not in (Rank.KING, Rank.KNIGHT):
        return False
    if any(done["suit"] == card.suit.value for done in view["sings"]):
        return False
    other = Card(card.suit, Rank.KNIGHT if card.rank == Rank.KING else Rank.KING)
    if other in memory.seen or other in {_card(play["card"]) for play in view["trick"]["cards"]}:
        return False
    if other in {_card(mate) for mate in view.get("partner_hand") or ()}:
        return False
    hand = {_card(mine) for mine in view["hand"]}
    if view["deck_count"] == 0:
        return other in hand and len(hand) - 1 >= MARIANNA.min_hand_to_sing_after_deck
    return True


def _exact_worlds(view: dict) -> bool:
    """2v2 a mazzo finito con poche carte: il calcolo esatto su ogni mano immaginata costa poco."""
    return (len(view["players"]) == 4 and view["deck_count"] == 0
            and max(entry["cards_in_hand"] for entry in view["players"]) <= EXACT_MAX_CARDS)


# --- Mani immaginate ---------------------------------------------------------------


def _worlds(view: dict, memory: CpuMemory, rng: random.Random, cap: int | None = None) -> list[HandState] | None:
    """Le mani possibili dal punto di vista della CPU; una sola se le carte nascoste sono tutte note.

    cap: al massimo quante mani (P127, calcolo esatto su ogni mano).

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
    if view.get("partner_hand"):
        # D46 (2v2, briscola e mazzo finito): le carte del compagno sono scoperte
        known[(seat + 2) % players] = [_card(card) for card in view["partner_hand"]]
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
        if cap is not None:
            count = min(count, cap)
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


def _exact_gain(state: HandState, seat: int, known: dict[tuple, int] | None = None) -> int:
    """Quanto guadagna ancora la squadra della CPU se tutti giocano al meglio (carte tutte note).

    known: le situazioni già calcolate nella stessa mano immaginata (P127).
    """
    team = team_of(seat)
    if known is None:
        known = {}

    def future(state: HandState) -> int:
        if state.finished:
            return 0
        key = (state.hands, state.trick, state.sings, state.turn_seat)
        if key not in known:
            values = []
            for move in _exact_moves(state):
                after = apply(state, move)
                values.append(_step_gain(state, after, seat) + future(after))
            known[key] = max(values) if team_of(state.turn_seat) == team else min(values)
        return known[key]

    return future(state)


def _step_gain(before: HandState, after: HandState, seat: int) -> int:
    """Come _gain(after) - _gain(before) dopo una mossa, contando solo le carte prese e i canti nuovi.

    Le prese si aggiungono in fondo a captured (game.py, _close_trick): il calcolo esatto
    lo chiama a ogni passo e rifare la somma di tutte le carte prese costava troppo (P127).
    """
    mine = team_of(seat)
    gain = 0
    for team, taken in enumerate(after.captured):
        points = sum(card.points for card in taken[len(before.captured[team]):])
        gain += points if team == mine else -points
    for done in after.sings[len(before.sings):]:
        gain += done.points if team_of(done.seat) == mine else -done.points
    return gain


def _exact_moves(state: HandState) -> list[Action]:
    seat = state.turn_seat
    suits = _singable(state)
    if suits:
        return [SingAction(seat, suit) for suit in suits]
    return [PlayCardAction(seat, card) for card in state.hands[seat]]


def _singable(state: HandState) -> list[Suit]:
    hand = state.hands[state.turn_seat]
    if not any(Card(suit, Rank.KING) in hand and Card(suit, Rank.KNIGHT) in hand for suit in Suit):
        return []  # senza una coppia Re e Cavallo in mano non si canta: si evita il controllo completo
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
