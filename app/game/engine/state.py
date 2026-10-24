"""Stato di una mano (P13). È immutabile: ogni mossa produce uno stato nuovo.

I posti sono numerati nell'ordine di gioco (verso destra, docs/CONTRATTO-SOCKET.md, 3.1):
dopo il posto 0 gioca l'1, poi il 2... La squadra di un posto è posto % 2
(1v1: posti 0 e 1; 2v2: squadra 0 = posti 0 e 2, squadra 1 = posti 1 e 3).

Cosa contiene (sono quasi tutti contenitori di dati, come le struct del C):
    TEAMS           il numero di squadre, 2
    team_of(seat)   la squadra di un posto, per esempio team_of(3) = 1
    TrickPlay       una carta giocata in una presa e chi l'ha giocata
    LastTrick       l'ultima presa chiusa: chi l'ha vinta e le sue carte
    LaidDown        le carte calate (P84)
    HandState       lo stato di una mano: carte di ognuno, mazzo, presa in corso, canti...
    HandResult      il risultato di una mano finita: punti delle carte e dei canti
    GameResult      chi ha vinto la partita
    GameState       lo stato della partita intera: mano in corso, punteggi, risultato

Perché immutabile: tutte le classi sono @dataclass(frozen=True) e usano tuple (elenchi
che non si cambiano) invece di liste. Così uno stato vecchio resta sempre uguale e si
può confrontare con quello nuovo, ricordare (la cache di lay_down.py, P84) o passare a
un altro thread (la CPU, P68) senza paura che qualcuno lo cambi a metà.

DA DOVE ARRIVANO I DATI: gli stati li crea solo game.py (new_game, apply, apply_game);
la stanza (app/realtime/room.py) tiene quello attuale, views.py lo trasforma nella
vista di ogni giocatore e la CPU lo legge.
"""

from dataclasses import dataclass

from app.game.engine.cards import Card, Suit
from app.game.engine.singing import Sing, trump_from_sings

# TEAMS: quante squadre ci sono, sempre 2 (nel 1v1 ogni giocatore è una "squadra")
TEAMS = 2


def team_of(seat: int) -> int:
    """La squadra di un posto.

    In parole semplici:
        team_of(seat)
        Il resto della divisione per 2: i posti pari (0, 2) sono la squadra 0, i
        dispari (1, 3) la squadra 1. Per esempio team_of(2) = 0.

        seat: il posto, da 0 a 3. Arriva da game.py e lay_down.py (chi ha giocato,
              chi ha vinto la presa, chi ha cantato).
    """
    return seat % TEAMS


# @dataclass(frozen=True): costruttore automatico e campi che non si cambiano più
# (vedi il commento in cards.py)
@dataclass(frozen=True)
class TrickPlay:
    """Una carta giocata in una presa.

    In parole semplici:
        TrickPlay(seat=1, card=Card(Suit.COPPE, Rank.KING))
        seat: il posto di chi l'ha giocata
        card: la carta
    """

    seat: int
    card: Card


@dataclass(frozen=True)
class LastTrick:
    """L'ultima presa chiusa, da mostrare al tavolo (P57).

    In parole semplici:
        LastTrick(winner_seat=0, plays=(TrickPlay(...), TrickPlay(...)))
        winner_seat: il posto di chi l'ha vinta
        plays:       le carte della presa, nell'ordine di gioco
    """

    winner_seat: int
    # tuple[TrickPlay, ...]: una tupla di TrickPlay, lunga quanto serve
    plays: tuple[TrickPlay, ...]


@dataclass(frozen=True)
class LaidDown:
    """Carte calate (P84): chi ha calato, le carte che restavano a ognuno e i 20 del compagno.

    In parole semplici:
        LaidDown(seat=2, hands=(...), sings=(...))
        La crea game.py quando qualcuno cala le carte; views.py la mostra al tavolo.
    """

    seat: int
    hands: tuple[tuple[Card, ...], ...]  # per posto, com'erano al momento di calare
    sings: tuple[Sing, ...]  # canti aggiunti dal server per il compagno (D45)


@dataclass(frozen=True)
class HandState:
    """Lo stato di una mano, dalla distribuzione all'ultima presa.

    In parole semplici:
        Lo crea new_hand di game.py; ogni mossa (apply) ne crea uno nuovo con i campi
        cambiati. "per posto" vuol dire che hands[0] sono le carte del posto 0,
        hands[1] quelle del posto 1, e così via.
    """

    # num_players: quanti giocatori, 2 (1v1) o 4 (2v2)
    num_players: int
    hands: tuple[tuple[Card, ...], ...]  # per posto
    deck: tuple[Card, ...]  # si pesca dal primo
    trick: tuple[TrickPlay, ...]  # presa in corso, nell'ordine di gioco
    leader_seat: int  # chi apre la presa in corso
    # "int | None": un numero oppure None (in C, un valore speciale come -1 o NULL)
    turn_seat: int | None  # None a mano finita
    # sings: i canti della mano, in ordine; il primo decide la briscola
    sings: tuple[Sing, ...]
    captured: tuple[tuple[Card, ...], ...]  # carte prese, per squadra
    # last_trick: l'ultima presa chiusa, None finché non se ne chiude una
    last_trick: LastTrick | None
    # "= None": il campo si può non passare al costruttore, e allora vale None
    laid_down: LaidDown | None = None  # la mano è finita perché qualcuno ha calato le carte

    # @property: si legge come un campo (state.finished, senza parentesi), ma è
    # calcolato ogni volta dagli altri campi
    @property
    def finished(self) -> bool:
        """True se la mano è finita, cioè non c'è più nessuno di turno.

        In parole semplici:
            state.finished
            Lo leggono game.py (per chiudere la mano) e views.py.
        """
        return self.turn_seat is None

    @property
    def trump(self) -> Suit | None:
        """La briscola della mano, oppure None se nessuno ha ancora cantato.

        In parole semplici:
            state.trump
            Non si salva a parte: si ricava ogni volta dal primo canto (P12).
        """
        return trump_from_sings(self.sings)

    @property
    def played_cards(self) -> frozenset[Card]:
        """Carte già finite sul tavolo in questa mano: prese chiuse e presa in corso.

        In parole semplici:
            state.played_cards
            Un insieme che non si può cambiare (frozenset) con le carte prese da
            tutte e due le squadre e quelle della presa in corso. Lo usa singing.py
            per sapere se un Re o un Cavallo è già stato giocato (seme "bruciato").
        """
        cards = []
        # le carte già prese, squadra per squadra: extend aggiunge in fondo alla lista
        # tutte le carte della tupla, una dopo l'altra (come un append per ciascuna)
        for team in self.captured:
            cards.extend(team)
        # le carte della presa in corso
        for play in self.trick:
            cards.append(play.card)
        return frozenset(cards)


@dataclass(frozen=True)
class HandResult:
    """Il risultato di una mano finita.

    In parole semplici:
        Lo calcola hand_result di game.py. "per squadra" vuol dire che
        card_points[0] sono i punti della squadra 0 e card_points[1] della squadra 1.
    """

    card_points: tuple[int, ...]  # per squadra
    sing_points: tuple[int, ...]  # per squadra
    last_trick: LastTrick  # la presa che ha chiuso la mano (P58): la mano dopo parte con last_trick None
    laid_down: LaidDown | None = None  # con una calata (P84) last_trick è l'ultima presa chiusa prima

    @property
    def totals(self) -> tuple[int, ...]:
        """I punti della mano di ogni squadra: carte più canti.

        In parole semplici:
            result.totals
            Per esempio (75, 85) con card_points (55, 65) e sing_points (20, 20).
            Lo usano game.py (per aggiornare il punteggio) e views.py.
        """
        totals = []
        # zip: prende un elemento da ciascuna delle due tuple alla volta (prima i
        # valori della squadra 0, poi della 1); strict=True dà errore se le due
        # tuple non sono lunghe uguali, invece di fermarsi alla più corta
        for cards, sings in zip(self.card_points, self.sing_points, strict=True):
            totals.append(cards + sings)
        return tuple(totals)


@dataclass(frozen=True)
class GameResult:
    """Chi ha vinto la partita.

    In parole semplici:
        GameResult(winner_team=0), oppure GameResult(winner_team=None) per un pareggio.
    """

    winner_team: int | None  # None = pareggio


@dataclass(frozen=True)
class GameState:
    """Partita intera (P14): mani una dopo l'altra fino al punteggio scelto.

    In parole semplici:
        La crea new_game di game.py e la cambia (creandone una nuova) apply_game.
        È quello che la stanza tiene in self.game.
    """

    num_players: int
    # target_score: i punti per vincere, 150, 300 o 500
    target_score: int
    hand_number: int  # da 1
    first_seat: int  # chi comincia la mano in corso
    hand: HandState  # a partita finita resta l'ultima mano, finita
    scores: tuple[int, ...]  # per squadra, delle mani già finite
    last_hand: HandResult | None  # None nella prima mano
    result: GameResult | None  # None durante la partita

    @property
    def finished(self) -> bool:
        """True se la partita è finita (c'è un risultato).

        In parole semplici:
            game.finished
            Lo leggono auto_move.py, la stanza e views.py.
        """
        return self.result is not None

    @property
    def dealer_seat(self) -> int:
        """Il mazziere è sempre alla sinistra di chi comincia (D11).

        In parole semplici:
            game.dealer_seat
            Il posto prima di chi comincia; con % si torna all'ultimo posto dopo lo
            0 (in Python -1 % 4 vale 3). Non si salva: si calcola (P14). Lo usa
            views.py.
        """
        return (self.first_seat - 1) % self.num_players
