"""Mossa della CPU (P68, D43): strategia "simulazione".

La CPU sceglie guardando **solo la propria vista** (player_view, contratto 3.3) e quello
che ricorda delle viste di prima nella stessa mano (CpuMemory: le carte uscite, che ogni
giocatore al tavolo ha visto). Non vede mai le carte degli altri né il mazzo.

Strategia (D43):
- cala le carte appena può (P84, D45);
- canta sempre quando può: se può cantare più semi, sceglie quale cantare prima come sceglie
  le carte (qui sotto);
- altrimenti immagina molte distribuzioni possibili delle carte che non vede (le carte non
  ancora uscite; Re e Cavallo cantati dall'avversario e non giocati sono per forza in mano
  a lui), gioca ogni mano immaginata fino in fondo per ogni sua mossa possibile e sceglie la
  mossa che in media le fa guadagnare più punti dell'avversario. Nelle mani immaginate
  tutti giocano come il "giocatore medio" (heuristic_move, regole fisse e senza memoria);
- quando le carte nascoste sono tutte note (1v1 a mazzo finito: sono quelle in mano
  all'avversario) calcola la mossa migliore in modo esatto, supponendo che anche
  l'avversario giochi al meglio. Nel calcolo esatto chi può cantare canta sempre.
  Nel 2v2 a mazzo finito con al massimo EXACT_MAX_CARDS carte a testa fa il calcolo esatto
  su ogni mano immaginata (P127, D50), invece di giocarla da giocatore medio.

P127 (D50): quando le mosse migliori valgono quasi
uguale (sotto la migliore di meno di TIE_SPREAD volte l'incertezza della stima, misurata
mano immaginata per mano immaginata), non decide il caso:
- da ultima nella presa gioca la carta con il risultato migliore nella presa (punti della
  sua squadra meno quelli dati agli avversari), poi una carta non di briscola, poi la più
  debole; Re e Cavalli ancora accoppiabili solo se non c'è altro;
- altrimenti evita i carichi (Asso e Tre) che possono finire agli avversari e i Re e
  Cavalli ancora accoppiabili (per il 40 e per il 20); se è costretta sacrifica prima il Re
  o il Cavallo e tiene il carico; tra le carte rimaste gioca quella stimata meglio.
A parità sceglie a caso.

P134 (D51), **solo nel 2v2** (scelta di Giuseppe: nel 1v1, dove chi risponde è
sempre l'ultimo, la CPU vinceva meno partite): da ultima il risultato della presa conta solo
le carte degli altri (se la presa è sua guadagna i loro punti; se la perde regala anche la sua
carta), così su una presa povera scarta una cartina e su una che vale prende con la carta più
bassa che basta; su una presa che vale meno di TRUMP_WORTH evita l'Asso e il Tre di briscola
(anche da ultima) e, non da ultima, le briscole più alte di quella più
bassa che prende.

Il numero di mani immaginate si ricava dalle carte che restano (SIMULATED_PLAYS), non dal
tempo: nella stessa situazione e con lo stesso rng la mossa è sempre la stessa. Per questo
ogni scelta a caso (rng.choice, rng.shuffle) avviene sempre nello stesso ordine e sugli
stessi elenchi, nello stesso ordine: le prove di forza (tests/forza/) e i test con le
situazioni vere dipendono dai semi fissi.

Cosa contiene:
    CpuMemory                    le carte uscite nella mano, viste dalla CPU
    cpu_move(view, rng, memory)  la mossa della CPU, per esempio PlayCardAction(1, Card(Suit.COPPE, Rank.ACE))
    heuristic_move(view, rng)    la mossa del "giocatore medio" (regole fisse)
    e le funzioni interne (con il trattino basso davanti), divise in tre parti: pari
    merito (_ties, _preferred, ...), mani immaginate (_worlds, _gain, _exact_gain, ...)
    e giocatore medio (_answer, _lead, _discard, ...).

DA DOVE ARRIVANO I DATI: la stanza (app/realtime/room.py), quando è il turno di un posto
della CPU, prende la vista di quel posto (player_view di views.py, la stessa che riceve un
giocatore vero) e chiama cpu_move con la memoria del posto (CpuMemory, che la stanza
aggiorna a ogni vista nuova con see) e il suo rng; poi passa la mossa ad apply di game.py.

Nei commenti, una "vista" è il dizionario di player_view, per esempio
{"you": {"seat": 1}, "hand": [{"suit": "coppe", "rank": 1}, ...], "legal": {"play": [...],
"sing": ["denari"], "lay_down": False}, "trick": {"leader_seat": 0, "cards": [{"seat": 0,
"card": {"suit": "spade", "rank": 3}}]}, "last_trick": None, "trump": "denari",
"sings": [...], "deck_count": 22, "players": [...], "hand_number": 2, ...}.
"""

import random
import secrets

# dataclass e field: vedi il commento sopra CpuMemory
from dataclasses import dataclass, field

from app.game.engine.actions import Action, LayDownAction, PlayCardAction, SingAction
from app.game.engine.cards import Card, Rank, Suit
from app.game.engine.deck import full_deck
from app.game.engine.errors import EngineError
from app.game.engine.game import apply
from app.game.engine.rules import MARIANNA
from app.game.engine.singing import Sing, singable_suits
from app.game.engine.state import TEAMS, HandState, LastTrick, TrickPlay, team_of

# Questi numeri si leggono al momento della mossa: i test li cambiano con monkeypatch
TRUMP_WORTH = 10  # giocatore medio: punti della presa per cui vale la pena usare una briscola
SIMULATED_PLAYS = 6000  # carte giocate in tutto nelle mani immaginate per una mossa (circa 0,2 s)
MIN_WORLDS = 20
MAX_WORLDS = 200
TIE_SPREAD = 2  # P127: "pari merito" = sotto la migliore di meno di 2 volte l'incertezza
EXACT_MAX_CARDS = 3  # P127: calcolo esatto nel 2v2 a mazzo finito fino a 3 carte a testa
EXACT_WORLDS = 6  # P127: mani immaginate con il calcolo esatto (con 3 carte a testa fino a 70 ms l'una)


# @dataclass: un "decoratore" che scrive da solo il costruttore della classe a partire
# dai campi elencati sotto (come una struct del C con i valori iniziali): CpuMemory()
# crea una memoria vuota. field(default_factory=set): ogni memoria nuova riceve il suo
# insieme vuoto (set()), non uno condiviso con le altre.
@dataclass
class CpuMemory:
    """Quello che la CPU ricorda della mano in corso: le carte uscite, prese dalle sue viste.

    La stanza le fa vedere ogni vista nuova (see): nella presa in corso e nell'ultima presa
    chiusa passano tutte le carte giocate, quindi la memoria è quella di un giocatore attento.

    In parole semplici:
        CpuMemory()
        hand_number: il numero della mano che ricorda (None prima della prima vista)
        seen:        le carte uscite in questa mano, per esempio
                     {Card(Suit.SPADE, Rank.THREE), Card(Suit.COPPE, Rank.TWO)}
    """

    hand_number: int | None = None
    seen: set[Card] = field(default_factory=set)

    def see(self, view: dict) -> None:
        """Aggiunge alla memoria le carte uscite che si vedono in una vista.

        In parole semplici:
            memory.see(view)
            view: la vista del posto della CPU (da room.py, a ogni vista nuova; e da cpu_move)
            Con una mano nuova (hand_number diverso) la memoria si svuota. Poi si
            aggiungono le carte della presa in corso e quelle dell'ultima presa chiusa.
        """
        if view["hand_number"] != self.hand_number:
            self.hand_number = view["hand_number"]
            self.seen = set()
        for play in view["trick"]["cards"]:
            self.seen.add(_card(play["card"]))
        if view["last_trick"] is not None:
            for play in view["last_trick"]["cards"]:
                self.seen.add(_card(play["card"]))


def cpu_move(view: dict, rng: random.Random | None = None, memory: CpuMemory | None = None) -> Action:
    """La mossa della CPU dalla sua vista. In gioco rng è None; i test passano un seme fisso.

    In parole semplici:
        cpu_move(view, rng, memory)
        Restituisce una mossa: LayDownAction (cala), SingAction (canta un seme) o
        PlayCardAction (gioca una carta), per esempio PlayCardAction(1, Card(Suit.COPPE, Rank.ACE)).
        view:   la vista del posto della CPU (da room.py)
        rng:    facoltativo; il generatore dei numeri a caso. Se manca (None) si usa
                secrets.SystemRandom, che prende il caso dal sistema operativo; i test
                passano random.Random(seme), così la partita è sempre la stessa
        memory: facoltativo; la memoria della CPU per questa mano (da room.py); se
                manca se ne crea una vuota
        Nota: si chiama "simulazione" perché per ogni mossa possibile gioca fino in fondo
        tante mani immaginate e tiene quella che in media guadagna di più.
    """
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

    # moves: le mosse tra cui scegliere; se può cantare, solo i canti (canta sempre)
    moves = []
    if legal["sing"]:
        for suit in legal["sing"]:
            moves.append(SingAction(seat, Suit(suit)))
    else:
        for card in legal["play"]:
            moves.append(PlayCardAction(seat, _card(card)))
    if len(moves) == 1:
        return moves[0]

    # Le mani immaginate: con il calcolo esatto (P127) al massimo EXACT_WORLDS
    exact = _exact_worlds(view)
    if exact:
        cap = EXACT_WORLDS
    else:
        cap = None
    worlds = _worlds(view, memory, rng, cap)
    if worlds is None:
        return heuristic_move(view, rng)  # memoria incompleta: meglio non immaginare mani sbagliate

    # results: per ogni mano immaginata, quanto guadagna ogni mossa (una riga per mano,
    # una colonna per mossa), per esempio [[12, -3], [8, 0]] con due mani e due mosse
    results = []
    for world in worlds:
        row = []
        if exact or len(worlds) == 1:
            # known: le mosse arrivano spesso alle stesse situazioni: si calcolano una volta
            known: dict[tuple, int] = {}
            for move in moves:
                row.append(_gain_of(world, move, seat) + _exact_gain(apply(world, move), seat, known))
            results.append(row)
            continue
        # seed: stesse scelte a caso per tutte le mosse (ognuna riparte da random.Random(seed)):
        # così le mosse si confrontano sulla stessa partita immaginata
        seed = rng.random()
        for move in moves:
            row.append(_gain_of(world, move, seat) + _rollout_gain(apply(world, move), seat, random.Random(seed)))
        results.append(row)

    # scores: il guadagno totale di ogni mossa su tutte le mani immaginate
    scores = []
    for index in range(len(moves)):
        total = 0
        for row in results:
            total += row[index]
        scores.append(total)

    # Tra le carte a pari merito (P127) sceglie _preferred; tra i canti, il punteggio migliore
    ties = _ties(results)
    if isinstance(moves[0], PlayCardAction) and len(ties) > 1:
        tied_moves = []
        tied_scores = []
        for index in ties:
            tied_moves.append(moves[index])
            tied_scores.append(scores[index])
        ties = _preferred(view, memory, tied_moves, tied_scores)
        return rng.choice(ties)
    best = None
    for index in ties:
        if best is None or scores[index] > best:
            best = scores[index]
    choices = []
    for index in ties:
        if scores[index] == best:
            choices.append(moves[index])
    return rng.choice(choices)


# --- Pari merito (P127, D50) ---------------------------------------------------------


def _ties(results: list[list[int]]) -> list[int]:
    """Le mosse a pari merito con la migliore: sotto di meno di TIE_SPREAD volte l'incertezza.

    L'incertezza (errore standard) si misura sulla differenza con la migliore mano per mano,
    perché le mosse sono giocate sulle stesse mani immaginate. Con una mano sola (calcolo
    esatto) sono a pari merito solo le mosse che valgono uguale.

    In parole semplici:
        _ties(results)
        results: la tabella di cpu_move, una riga per mano immaginata e una colonna per
                 mossa, per esempio [[12, 10], [8, 9]]
        Restituisce le posizioni delle mosse a pari merito, sempre compresa la migliore,
        per esempio [0, 1].
    """
    count = len(results)
    moves = len(results[0])

    # totals: il guadagno totale di ogni mossa; best: la posizione della migliore (la
    # prima, se più mosse hanno lo stesso totale)
    totals = []
    for index in range(moves):
        total = 0
        for row in results:
            total += row[index]
        totals.append(total)
    best = 0
    for index in range(1, moves):
        if totals[index] > totals[best]:
            best = index

    ties = []
    for index in range(moves):
        # gaps: di quanto la migliore batte questa mossa, mano per mano (numeri interi)
        gaps = []
        for row in results:
            gaps.append(row[best] - row[index])
        mean = sum(gaps) / count
        if count > 1:
            # La varianza si somma con sum() su una lista: da Python 3.12 sum() dei numeri
            # con la virgola fa una somma più precisa di un ciclo con +=, e un ciclo
            # cambierebbe l'ultima cifra (e, raramente, la mossa scelta)
            squares = []
            for gap in gaps:
                squares.append((gap - mean) ** 2)
            variance = sum(squares) / (count - 1)
            # (variance / count) ** 0.5: la radice quadrata, cioè l'errore standard
            if mean < TIE_SPREAD * (variance / count) ** 0.5 or mean == 0:
                ties.append(index)
        elif mean == 0:
            ties.append(index)
    return ties


def _preferred(view: dict, memory: CpuMemory, moves: list[PlayCardAction], scores: list[int]) -> list[Action]:
    """Tra le carte a pari merito, quelle che un buon giocatore preferisce (vedi in cima).

    In parole semplici:
        _preferred(view, memory, moves, scores)
        moves:  le carte a pari merito (da cpu_move), per esempio
                [PlayCardAction(1, Card(Suit.COPPE, Rank.ACE)), PlayCardAction(1, Card(Suit.SPADE, Rank.TWO))]
        scores: il guadagno totale di ciascuna, nello stesso ordine
        Restituisce le mosse migliori secondo le regole di P127 e P134 (una o più:
        cpu_move ne sceglie una a caso).
    """
    seat = view["you"]["seat"]
    if view["trump"] is None:
        trump = None
    else:
        trump = Suit(view["trump"])

    # plays: le carte già sulla presa, come coppie (posto, carta)
    plays = []
    for play in view["trick"]["cards"]:
        plays.append((play["seat"], _card(play["card"])))

    # pairable: le carte che sono un Re o un Cavallo ancora da cantare
    pairable = set()
    for move in moves:
        if _pairable(move.card, view, memory):
            pairable.add(move.card)

    two_v_two = len(view["players"]) == 4  # P134 solo nel 2v2: nel 1v1 la CPU perdeva più partite

    # worth: quanti punti ci sono già sulla presa
    worth = 0
    for play in plays:
        worth += play[1].points

    # winning_trumps (P134, 2v2): le briscole che prenderebbero una presa povera
    winning_trumps = []
    if two_v_two and plays and worth < TRUMP_WORTH:
        for move in moves:
            if move.card.suit != trump:
                continue
            with_move = list(plays)
            with_move.append((seat, move.card))
            if _winning(with_move, trump)[0] == seat:
                winning_trumps.append(move.card)

    # Da ultima nella presa: il risultato della presa decide
    if len(plays) + 1 == len(view["players"]):
        keep = []
        for move in moves:
            if move.card not in pairable:
                keep.append(move)
        if not keep:
            keep = moves  # solo Re e Cavalli accoppiabili: si sceglie tra quelli

        def key(move):
            """L'ordine delle carte da ultima: la più bassa vince (le tuple si confrontano
            un elemento alla volta, False prima di True).

            In parole semplici:
                key(move) = (sprecata, -risultato della presa, è briscola, forza)
            """
            wasted = move.card in winning_trumps and move.card.points >= 10
            return (wasted, -_trick_result(plays, move.card, seat, trump, only_others=two_v_two),
                    move.card.suit == trump, move.card.strength)

        lowest = None
        for move in keep:
            if lowest is None or key(move) < lowest:
                lowest = key(move)
        best_moves = []
        for move in keep:
            if key(move) == lowest:
                best_moves.append(move)
        return best_moves

    # weakest_trump: la briscola più bassa tra quelle che prenderebbero (None se non ce ne sono)
    weakest_trump = None
    for card in winning_trumps:
        if weakest_trump is None or card.strength < weakest_trump.strength:
            weakest_trump = card

    def penalty(move):
        """Quanto è sconsigliata una carta non da ultima: 0 bene, 1 meglio di no, 2 da evitare.

        In parole semplici:
            penalty(move) = 2 per un carico a rischio (o di briscola su una presa povera),
            1 per un Re o Cavallo accoppiabile o una briscola più alta del necessario, 0 altrimenti.
        """
        if move.card.points >= 10 and (move.card in winning_trumps
                                       or not _safe_load(plays, move.card, seat, trump, view, memory)):
            return 2  # P134: un carico di briscola su una presa povera è sprecato anche se al sicuro
        if move.card in pairable:
            return 1
        if move.card in winning_trumps and move.card != weakest_trump:
            return 1  # P134: su una presa povera basta la briscola più bassa che prende
        return 0

    # Si tengono le carte con la penalità più bassa e, tra quelle, il guadagno migliore
    lowest = None
    for move in moves:
        if lowest is None or penalty(move) < lowest:
            lowest = penalty(move)
    keep = []
    for index in range(len(moves)):
        if penalty(moves[index]) == lowest:
            keep.append((moves[index], scores[index]))
    best = None
    for kept in keep:
        if best is None or kept[1] > best:
            best = kept[1]
    best_moves = []
    for kept in keep:
        if kept[1] == best:
            best_moves.append(kept[0])
    return best_moves


def _trick_result(plays, card, seat, trump, only_others: bool) -> int:
    """Da ultima: punti che la presa sposta per la squadra della CPU.

    only_others (P134, D51, nel 2v2): se la presa è della sua squadra guadagna i punti delle
    carte degli altri (quelli della sua carta li avrebbe comunque); se va agli avversari regala
    tutto, compresa la sua carta. Senza (P127, nel 1v1): conta anche la sua carta se vince.

    In parole semplici:
        _trick_result(plays, card, seat, trump, only_others=True)
        Per esempio sulla presa [(0, 3 di spade)] il 2 di spade della CPU al posto 1
        perde: -10 - 0 = -10.
        plays: le carte già sulla presa, coppie (posto, carta) (da _preferred)
        card:  la carta che la CPU giocherebbe; seat: il suo posto; trump: la briscola o None
    """
    # all_plays: la presa con la carta della CPU in fondo (list() fa una copia: plays non cambia)
    all_plays = list(plays)
    all_plays.append((seat, card))
    winner = _winning(all_plays, trump)[0]
    others = 0
    for play in plays:
        others += play[1].points
    if team_of(winner) != team_of(seat):
        return -others - card.points
    if only_others:
        return others
    return others + card.points


def _winning(plays, trump):
    """La giocata che sta vincendo la presa, come coppia (posto, carta).

    In parole semplici:
        _winning(plays, trump)
        plays: le giocate in ordine, coppie (posto, carta), la prima è quella di uscita
        Per esempio _winning([(0, 3 di spade), (1, Asso di spade)], None) = (1, Asso di spade).
    """
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

    In parole semplici:
        _safe_load(plays, card, seat, trump, view, memory) -> True o False
        plays: le carte già sulla presa, coppie (posto, carta); card: il carico
    """
    # all_plays: la presa con la carta della CPU in fondo (list() fa una copia: plays non cambia)
    all_plays = list(plays)
    all_plays.append((seat, card))
    winning = _winning(all_plays, trump)
    winner = winning[0]
    best = winning[1]
    if team_of(winner) != team_of(seat):
        return False
    lead = all_plays[0][1].suit
    for other in _unseen(view, memory):
        if _beats(other, best, lead, trump):
            return False
    return True


def _unseen(view: dict, memory: CpuMemory) -> list[Card]:
    """Le carte che la CPU non vede, nell'ordine del mazzo completo.

    In parole semplici:
        _unseen(view, memory)
        Sono le 40 carte meno quelle uscite (memory.seen), quelle in mano alla CPU, quelle
        scoperte del compagno (partner_hand, se c'è) e quelle sulla presa.
    """
    known = set(memory.seen)
    for card in view["hand"]:
        known.add(_card(card))
    partner_hand = view.get("partner_hand")
    if partner_hand:
        for card in partner_hand:
            known.add(_card(card))
    for play in view["trick"]["cards"]:
        known.add(_card(play["card"]))

    unseen = []
    for card in full_deck():
        if card not in known:
            unseen.append(card)
    return unseen


def _pairable(card: Card, view: dict, memory: CpuMemory) -> bool:
    """Un Re o un Cavallo che si può ancora cantare (40 o 20) insieme all'altra carta del seme.

    Il seme non è cantato, l'altra carta non è uscita e la CPU può ancora averla: in mano,
    oppure ancora da pescare (non scoperta in mano al compagno); a mazzo finito deve averla in
    mano e restare con almeno le carte che servono per cantare.

    In parole semplici:
        _pairable(card, view, memory) -> True o False
        Per esempio il Re di coppe con il Cavallo di coppe ancora nascosto e coppe non
        cantato: True. Ogni carta che non è un Re o un Cavallo: False.
    """
    if card.rank not in (Rank.KING, Rank.KNIGHT):
        return False
    for done in view["sings"]:
        if done["suit"] == card.suit.value:
            return False

    # other: l'altra carta della coppia (il Cavallo per il Re, il Re per il Cavallo)
    if card.rank == Rank.KING:
        other = Card(card.suit, Rank.KNIGHT)
    else:
        other = Card(card.suit, Rank.KING)
    if other in memory.seen:
        return False
    for play in view["trick"]["cards"]:
        if _card(play["card"]) == other:
            return False
    partner_hand = view.get("partner_hand")
    if partner_hand:
        for mate in partner_hand:
            if _card(mate) == other:
                return False

    # hand: le carte della CPU, come insieme
    hand = set()
    for mine in view["hand"]:
        hand.add(_card(mine))
    if view["deck_count"] == 0:
        return other in hand and len(hand) - 1 >= MARIANNA.min_hand_to_sing_after_deck
    return True


def _exact_worlds(view: dict) -> bool:
    """2v2 a mazzo finito con poche carte: il calcolo esatto su ogni mano immaginata costa poco.

    In parole semplici:
        _exact_worlds(view) -> True nel 2v2, a mazzo finito, se nessuno ha più di
        EXACT_MAX_CARDS (3) carte in mano.
    """
    if len(view["players"]) != 4 or view["deck_count"] != 0:
        return False
    most = 0
    for entry in view["players"]:
        most = max(most, entry["cards_in_hand"])
    return most <= EXACT_MAX_CARDS


# --- Mani immaginate ---------------------------------------------------------------


def _worlds(view: dict, memory: CpuMemory, rng: random.Random, cap: int | None = None) -> list[HandState] | None:
    """Le mani possibili dal punto di vista della CPU; una sola se le carte nascoste sono tutte note.

    cap: al massimo quante mani (P127, calcolo esatto su ogni mano).

    None se i conti non tornano (la memoria non ha tutte le carte uscite).

    In parole semplici:
        _worlds(view, memory, rng, cap)
        Restituisce un elenco di HandState (lo stato di una mano del motore, state.py),
        uno per mano immaginata: la mano della CPU è quella vera, le carte che non vede
        sono distribuite a caso (rng.shuffle) tra gli altri e il mazzo.
        cap: facoltativo; None = nessun limite oltre a MAX_WORLDS
        Le mani immaginate si passano ad apply di game.py: hands, deck, trick, sings e
        captured devono essere tuple, non liste (lo stato del motore non si cambia mai).
    """
    seat = view["you"]["seat"]
    players = len(view["players"])

    # La mano della CPU, la presa in corso e i canti, nella forma dello stato del motore
    hand_cards = []
    for card in view["hand"]:
        hand_cards.append(_card(card))
    hand = tuple(hand_cards)
    trick_plays = []
    for play in view["trick"]["cards"]:
        trick_plays.append(TrickPlay(play["seat"], _card(play["card"])))
    trick = tuple(trick_plays)
    on_table = set()
    for play in trick:
        on_table.add(play.card)
    sung = []
    for done in view["sings"]:
        sung.append(Sing(done["seat"], Suit(done["suit"]), done["points"]))
    sings = tuple(sung)

    # gone: le carte uscite nelle prese chiuse (quelle della presa in corso stanno in trick)
    gone = memory.seen - on_table
    # sizes: quante carte ha in mano ogni altro giocatore, per esempio {0: 5} nel 1v1
    sizes = {}
    for entry in view["players"]:
        if entry["seat"] != seat:
            sizes[entry["seat"]] = entry["cards_in_hand"]

    # known: per ogni altro giocatore, le carte che ha di sicuro.
    # Re e Cavallo cantati da un altro e non ancora giocati sono in mano a lui
    known: dict[int, list[Card]] = {}
    for other in sizes:
        known[other] = []
    for done in sings:
        if done.seat != seat:
            for rank in (Rank.KING, Rank.KNIGHT):
                card = Card(done.suit, rank)
                if card not in memory.seen and card not in known[done.seat]:
                    known[done.seat].append(card)
    if view.get("partner_hand"):
        # D46 (2v2, briscola e mazzo finito): le carte del compagno sono scoperte
        mate_cards = []
        for card in view["partner_hand"]:
            mate_cards.append(_card(card))
        known[(seat + 2) % players] = mate_cards

    # pool: le carte da distribuire a caso, nell'ordine del mazzo completo
    placed = set()
    for cards in known.values():
        for card in cards:
            placed.add(card)
    pool = []
    for card in full_deck():
        if card not in memory.seen and card not in hand and card not in placed:
            pool.append(card)

    # I conti devono tornare: carte da distribuire = carte nascoste degli altri + mazzo
    # for other, size in sizes.items(): a ogni giro other è il posto e size il suo numero di carte
    hidden_total = 0
    for other, size in sizes.items():
        hidden_total += size
    if len(pool) != hidden_total - len(placed) + view["deck_count"]:
        return None
    for other, size in sizes.items():
        if len(known[other]) > size:
            return None

    last = view["last_trick"]
    if last is None:
        last_trick = None
    else:
        last_plays = []
        for play in last["cards"]:
            last_plays.append(TrickPlay(play["seat"], _card(play["card"])))
        last_trick = LastTrick(last["winner_seat"], tuple(last_plays))

    # Le carte uscite stanno tutte nelle prese della squadra 0: conta solo quanto si guadagna
    # da qui. ((),) * (TEAMS - 1): una tupla vuota per ognuna delle altre squadre
    captured = (tuple(gone),) + ((),) * (TEAMS - 1)

    # count: quante mani immaginare
    hidden_holders = []
    for other, size in sizes.items():
        if size > len(known[other]):
            hidden_holders.append(other)
    if view["deck_count"] == 0 and len(hidden_holders) <= 1:
        count = 1  # niente di nascosto: le carte che mancano sono tutte dell'unico che ne ha
    else:
        remaining = len(hand) + hidden_total + view["deck_count"]
        count = max(MIN_WORLDS, min(MAX_WORLDS, SIMULATED_PLAYS // (len(view["legal"]["play"]) * remaining)))
        if cap is not None:
            count = min(count, cap)

    # Ogni mano immaginata: si mescolano le carte da distribuire e si danno nell'ordine dei posti
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
            hands.append(tuple(known[index]) + tuple(cards[:take]))
            cards = cards[take:]
        worlds.append(HandState(
            num_players=players, hands=tuple(hands), deck=tuple(cards), trick=trick,
            leader_seat=view["trick"]["leader_seat"], turn_seat=seat, sings=sings,
            captured=captured, last_trick=last_trick,
        ))
    return worlds


def _gain(state: HandState, seat: int) -> int:
    """Punti della squadra della CPU meno quelli degli avversari, nelle prese e nei canti.

    In parole semplici:
        _gain(state, seat)
        Per esempio con 30 punti di prese e un 40 per la squadra della CPU e 25 per gli
        avversari: 30 + 40 - 25 = 45.
    """
    # points: i punti di ogni squadra (prese, poi canti)
    points = []
    for taken in state.captured:
        total = 0
        for card in taken:
            total += card.points
        points.append(total)
    for done in state.sings:
        points[team_of(done.seat)] += done.points

    mine = team_of(seat)
    gain = 0
    for team in range(len(points)):
        if team == mine:
            gain += points[team]
        else:
            gain -= points[team]
    return gain


def _gain_of(state: HandState, move: Action, seat: int) -> int:
    """Quanto fa guadagnare una mossa da sola (prima di giocare il resto della mano).

    In parole semplici:
        _gain_of(state, move, seat) = _gain dopo la mossa - _gain prima.
    """
    return _gain(apply(state, move), seat) - _gain(state, seat)


def _rollout_gain(state: HandState, seat: int, rng: random.Random) -> int:
    """Quanto guadagna ancora la squadra della CPU giocando la mano fino in fondo da giocatore medio.

    In parole semplici:
        _rollout_gain(state, seat, rng)
        rng: un random.Random(seed) nuovo per ogni mossa (da cpu_move), così tutte le
             mosse vedono le stesse scelte a caso
    """
    start = _gain(state, seat)
    while not state.finished:
        state = apply(state, _policy(state, rng))
    return _gain(state, seat) - start


def _exact_gain(state: HandState, seat: int, known: dict[tuple, int] | None = None) -> int:
    """Quanto guadagna ancora la squadra della CPU se tutti giocano al meglio (carte tutte note).

    known: le situazioni già calcolate nella stessa mano immaginata (P127).

    In parole semplici:
        _exact_gain(state, seat, known)
        È il "minimax": nel turno della squadra della CPU si prende la mossa che guadagna
        di più, nel turno degli avversari quella che le fa guadagnare di meno, fino alla
        fine della mano. future chiama sé stessa (ricorsione) dopo ogni mossa.
        known: facoltativo; un dizionario situazione -> valore, per non rifare i conti
    """
    team = team_of(seat)
    if known is None:
        known = {}

    def future(state: HandState) -> int:
        """Il valore della situazione state per la squadra della CPU, da qui alla fine.

        In parole semplici:
            future(state)
            key: la situazione (mani, presa, canti, turno), per ritrovarla in known.
            Usa team, seat e known della funzione che la contiene (in Python una
            funzione dentro un'altra vede le sue variabili).
        """
        if state.finished:
            return 0
        key = (state.hands, state.trick, state.sings, state.turn_seat)
        if key not in known:
            values = []
            for move in _exact_moves(state):
                after = apply(state, move)
                values.append(_step_gain(state, after, seat) + future(after))
            if team_of(state.turn_seat) == team:
                known[key] = max(values)
            else:
                known[key] = min(values)
        return known[key]

    return future(state)


def _step_gain(before: HandState, after: HandState, seat: int) -> int:
    """Come _gain(after) - _gain(before) dopo una mossa, contando solo le carte prese e i canti nuovi.

    Le prese si aggiungono in fondo a captured (game.py, _close_trick): il calcolo esatto
    lo chiama a ogni passo e rifare la somma di tutte le carte prese costava troppo (P127).

    In parole semplici:
        _step_gain(before, after, seat)
        taken[len(before.captured[team]):]: le carte prese da quella squadra con questa
        mossa (quelle dopo le carte che aveva già).
    """
    mine = team_of(seat)
    gain = 0
    for team in range(len(after.captured)):
        taken = after.captured[team]
        points = 0
        for card in taken[len(before.captured[team]):]:
            points += card.points
        if team == mine:
            gain += points
        else:
            gain -= points
    for done in after.sings[len(before.sings):]:
        if team_of(done.seat) == mine:
            gain += done.points
        else:
            gain -= done.points
    return gain


def _exact_moves(state: HandState) -> list[Action]:
    """Le mosse del calcolo esatto: i canti se chi è di turno può cantare, altrimenti le sue carte.

    In parole semplici:
        _exact_moves(state) -> per esempio [PlayCardAction(0, ...), PlayCardAction(0, ...)]
    """
    seat = state.turn_seat
    suits = _singable(state)
    actions = []
    if suits:
        for suit in suits:
            actions.append(SingAction(seat, suit))
        return actions
    for card in state.hands[seat]:
        actions.append(PlayCardAction(seat, card))
    return actions


def _singable(state: HandState) -> list[Suit]:
    """I semi che chi è di turno può cantare adesso, nello stato del motore.

    In parole semplici:
        _singable(state) -> per esempio [Suit.DENARI]
        Prima un controllo veloce (una coppia Re e Cavallo in mano), poi le regole
        complete di singable_suits (singing.py).
    """
    hand = state.hands[state.turn_seat]
    has_pair = False
    for suit in Suit:
        if Card(suit, Rank.KING) in hand and Card(suit, Rank.KNIGHT) in hand:
            has_pair = True
            break
    if not has_pair:
        return []  # senza una coppia Re e Cavallo in mano non si canta: si evita il controllo completo
    return singable_suits(hand=state.hands[state.turn_seat], sings=state.sings, played_cards=state.played_cards,
                          deck_count=len(state.deck), is_turn=True, first_trick=state.last_trick is None)


def _policy(state: HandState, rng: random.Random) -> Action:
    """Il giocatore medio sullo stato della mano: le stesse scelte di heuristic_move.

    In parole semplici:
        _policy(state, rng)
        La usano le mani immaginate (_rollout_gain): lo stato del motore al posto della vista.
    """
    seat = state.turn_seat
    hand = list(state.hands[seat])
    suits = _singable(state)
    if suits:
        def sing_order(suit):
            """Il seme con più carte (e più forti) viene prima: la sua chiave è la più bassa."""
            return (-_count(hand, suit), -_strength(hand, suit))

        return SingAction(seat, _best(suits, sing_order, rng))

    sung = set()
    for done in state.sings:
        sung.add(done.suit)
    pairs = _open_pairs(hand, sung)
    trick = []
    for play in state.trick:
        trick.append(play.card)
    if trick:
        card = _answer(hand, trick, state.trump, not state.deck, pairs, rng)
    else:
        card = _lead(hand, state.trump, not state.deck, pairs, rng)
    return PlayCardAction(seat, card)


# --- Giocatore medio (regole fisse, senza memoria) ---------------------------------


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

    In parole semplici:
        heuristic_move(view, rng)
        view: una vista (da cpu_move, quando la memoria non basta, e dai test)
        rng:  facoltativo; come in cpu_move
        Restituisce una mossa, come cpu_move.
    """
    seat = view["you"]["seat"]
    legal = view["legal"]
    if not legal["play"]:
        raise EngineError("Non è il turno della CPU.")
    if rng is None:
        rng = secrets.SystemRandom()
    hand = []
    for card in view["hand"]:
        hand.append(_card(card))
    if legal["sing"]:
        suits = []
        for suit in legal["sing"]:
            suits.append(Suit(suit))

        def sing_order(suit):
            """Il seme con più carte (e più forti) viene prima: la sua chiave è la più bassa."""
            return (-_count(hand, suit), -_strength(hand, suit))

        return SingAction(seat, _best(suits, sing_order, rng))
    if legal["lay_down"]:
        return LayDownAction(seat)

    playable = []
    for card in legal["play"]:
        playable.append(_card(card))
    if view["trump"] is None:
        trump = None
    else:
        trump = Suit(view["trump"])
    deck_empty = view["deck_count"] == 0
    sung = set()
    for done in view["sings"]:
        sung.add(Suit(done["suit"]))
    pairs = _open_pairs(hand, sung)
    trick = []
    for play in view["trick"]["cards"]:
        trick.append(_card(play["card"]))
    if trick:
        card = _answer(playable, trick, trump, deck_empty, pairs, rng)
    else:
        card = _lead(playable, trump, deck_empty, pairs, rng)
    return PlayCardAction(seat, card)


def _answer(playable, trick, trump, deck_empty, pairs, rng):
    """Il giocatore medio risponde a una presa aperta: prende se conviene, altrimenti scarta.

    In parole semplici:
        _answer(playable, trick, trump, deck_empty, pairs, rng) -> una carta
        playable:   le carte che può giocare; trick: le carte sulla presa, in ordine
        trump:      la briscola o None; deck_empty: True a mazzo finito
        pairs:      i Re e Cavalli da non rompere (da _open_pairs)
    """
    # best: la carta che sta vincendo la presa; worth: i punti sulla presa
    lead = trick[0].suit
    best = trick[0]
    for card in trick[1:]:
        if _beats(card, best, lead, trump):
            best = card
    worth = 0
    for card in trick:
        worth += card.points

    # winners: le carte che prendono; prima quelle non di briscola (plain)
    winners = []
    for card in playable:
        if _beats(card, best, lead, trump):
            winners.append(card)
    plain = []
    for card in winners:
        if card.suit != trump:
            plain.append(card)
    if plain:
        return _best(plain, _cheapness, rng)
    trumps = []
    for card in winners:
        if card.suit == trump:
            trumps.append(card)
    if trumps and (worth >= TRUMP_WORTH or (deck_empty and worth > 0)):
        return _best(trumps, _cheapness, rng)
    return _discard(playable, trump, pairs, rng)


def _cheapness(card):
    """La chiave della carta più economica per prendere: pochi punti, poi poca forza.

    In parole semplici:
        _cheapness(card) = (card.points, card.strength); la usa _best.
    """
    return (card.points, card.strength)


def _strongest_first(card):
    """La chiave della carta più forte: la forza con il segno meno (la più forte è la più bassa).

    In parole semplici:
        _strongest_first(card) = -card.strength; la usa _best in _lead.
    """
    return -card.strength


def _lead(playable, trump, deck_empty, pairs, rng):
    """Il giocatore medio apre la presa: a mazzo finito con la briscola più forte, altrimenti scarta.

    In parole semplici:
        _lead(playable, trump, deck_empty, pairs, rng) -> una carta
    """
    trumps = []
    for card in playable:
        if card.suit == trump:
            trumps.append(card)
    if deck_empty and trumps:
        return _best(trumps, _strongest_first, rng)
    return _discard(playable, trump, pairs, rng)


def _discard(playable, trump, pairs, rng):
    """La carta che costa meno: pochi punti, non briscola, debole, senza rompere una coppia.

    In parole semplici:
        _discard(playable, trump, pairs, rng) -> una carta
        cost(card): la chiave dell'ordine (rompe una coppia, punti, è briscola, forza)
    """
    def cost(card):
        """La chiave di _discard: la carta con la chiave più bassa costa meno."""
        return (card in pairs, card.points, card.suit == trump, card.strength)

    return _best(playable, cost, rng)


def _beats(card, best, lead, trump):
    """Stessa regola di trick.py: vince la briscola più forte, poi la più forte del seme di uscita.

    In parole semplici:
        _beats(card, best, lead, trump) -> True se card batte best
        rank(c): la tupla (è briscola, è del seme di uscita, forza); le tuple si
        confrontano un elemento alla volta, e True vale più di False.
    """
    def rank(c):
        """La forza di una carta in questa presa, come tupla."""
        return (c.suit == trump, c.suit == lead, c.strength)
    return rank(card) > rank(best)


def _open_pairs(hand, sung):
    """Re e Cavallo dello stesso seme ancora in mano e non cantati: meglio non giocarli.

    In parole semplici:
        _open_pairs(hand, sung) -> per esempio {Re di coppe, Cavallo di coppe}
        hand: le carte in mano; sung: i semi già cantati (un insieme di Suit)
    """
    cards = set(hand)
    pairs = set()
    for suit in Suit:
        king = Card(suit, Rank.KING)
        knight = Card(suit, Rank.KNIGHT)
        if suit not in sung and king in cards and knight in cards:
            pairs.add(king)
            pairs.add(knight)
    return pairs


def _best(items, key, rng):
    """Uno a caso tra gli elementi con la chiave più bassa.

    In parole semplici:
        _best(items, key, rng)
        items: le carte (o i semi) tra cui scegliere, in un ordine fisso
        key:   la funzione che dà la chiave di un elemento, per esempio _cheapness (in C,
               un puntatore a funzione)
        L'elenco passato a rng.choice resta nell'ordine di items: con lo stesso rng la
        scelta è sempre la stessa.
    """
    lowest = None
    for item in items:
        if lowest is None or key(item) < lowest:
            lowest = key(item)
    choices = []
    for item in items:
        if key(item) == lowest:
            choices.append(item)
    return rng.choice(choices)


def _count(hand, suit):
    """Quante carte di quel seme ci sono in mano.

    In parole semplici:
        _count(hand, Suit.COPPE) -> per esempio 2
    """
    count = 0
    for card in hand:
        if card.suit == suit:
            count += 1
    return count


def _strength(hand, suit):
    """La forza di tutte le carte di quel seme in mano, sommata.

    In parole semplici:
        _strength(hand, Suit.COPPE) -> la somma di card.strength delle carte di coppe
    """
    total = 0
    for card in hand:
        if card.suit == suit:
            total += card.strength
    return total


def _card(data: dict) -> Card:
    """Una carta del contratto ({"suit", "rank"}) come Card del motore.

    In parole semplici:
        _card({"suit": "coppe", "rank": 1}) = Card(Suit.COPPE, Rank.ACE)
    """
    return Card(Suit(data["suit"]), Rank(data["rank"]))
