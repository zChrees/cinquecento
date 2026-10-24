"""Carte siciliane: seme, valore, punti e forza nella presa (P10, regole in docs/REGOLE-GIOCO.md).

Cosa fa il file: descrive una carta (seme e valore) e quello che il gioco deve sapere
di lei: quanti punti vale, quanto è forte in una presa, come si scrive il suo codice.

Cosa contiene:
    Suit                  i quattro semi, per esempio Suit.COPPE
    Rank                  i dieci valori, per esempio Rank.KING (il Re, numero 10)
    RANK_NAMES            il nome italiano di ogni valore, per esempio "Cavallo"
    POINTS                i punti di ogni valore, per esempio Asso 11
    STRENGTH_ORDER        i valori dal più debole al più forte
    STRENGTH              la forza di ogni valore, da 1 (il 2) a 10 (l'Asso)
    Card(suit, rank)      una carta, per esempio Card(Suit.COPPE, Rank.ACE)
    Card.from_code(code)  la carta dal suo codice, per esempio Card.from_code("coppe-1")

DA DOVE ARRIVANO I DATI: le carte le crea deck.py (il mazzo da 40); tutti gli altri
file del motore le ricevono già fatte, dentro lo stato della partita (state.py).
"""

# dataclass: un "decoratore" (una riga con la @ sopra una classe o una funzione, che
# le aggiunge qualcosa in automatico). @dataclass scrive da solo il costruttore
# __init__ a partire dai campi elencati, il confronto == campo per campo e la stampa
# leggibile. In C è come dichiarare una struct e avere già pronta la funzione che la
# riempie.
from dataclasses import dataclass

# Enum: un elenco chiuso di valori con un nome, come un enum del C. Suit.COPPE è
# sempre lo stesso oggetto: si confronta con == (o con "is") e non si può sbagliare a
# scriverlo, perché un nome che non esiste dà subito errore.
from enum import Enum

from app.game.engine.errors import InvalidMoveError


class Suit(Enum):
    """I quattro semi. Il valore a destra è il testo usato nei codici e nella vista.

    In parole semplici:
        Suit.COPPE è il seme; Suit.COPPE.value è il testo "coppe".
        Suit("coppe") fa il contrario: dal testo al seme (errore se il testo non c'è).
        "for suit in Suit" passa i semi nell'ordine scritto qui sotto.
    """

    DENARI = "denari"
    COPPE = "coppe"
    SPADE = "spade"
    BASTONI = "bastoni"


class Rank(Enum):
    """Il valore è il numero stampato sulla carta siciliana (Fante 8, Cavallo 9, Re 10).

    In parole semplici:
        Rank.KING è il Re; Rank.KING.value è il numero 10.
        "for rank in Rank" passa i valori dall'Asso al Re, nell'ordine qui sotto.
    """

    ACE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    JACK = 8
    KNIGHT = 9
    KING = 10


# RANK_NAMES: il nome italiano di ogni valore, usato quando una carta si scrive come
# testo (per esempio nei messaggi di errore del canto: "Il Re di coppe è già stato giocato")
RANK_NAMES = {
    Rank.ACE: "Asso",
    Rank.TWO: "2",
    Rank.THREE: "3",
    Rank.FOUR: "4",
    Rank.FIVE: "5",
    Rank.SIX: "6",
    Rank.SEVEN: "7",
    Rank.JACK: "Fante",
    Rank.KNIGHT: "Cavallo",
    Rank.KING: "Re",
}

# POINTS: quanti punti vale ogni valore a fine mano (in tutto il mazzo fa 120)
POINTS = {
    Rank.ACE: 11,
    Rank.THREE: 10,
    Rank.KING: 4,
    Rank.KNIGHT: 3,
    Rank.JACK: 2,
    Rank.SEVEN: 0,
    Rank.SIX: 0,
    Rank.FIVE: 0,
    Rank.FOUR: 0,
    Rank.TWO: 0,
}

# Dalla più debole alla più forte: A > 3 > R > C > F > 7 > 6 > 5 > 4 > 2
STRENGTH_ORDER = (
    Rank.TWO,
    Rank.FOUR,
    Rank.FIVE,
    Rank.SIX,
    Rank.SEVEN,
    Rank.JACK,
    Rank.KNIGHT,
    Rank.KING,
    Rank.THREE,
    Rank.ACE,
)

# STRENGTH: la forza di ogni valore, cioè la sua posizione in STRENGTH_ORDER contando
# da 1. Per esempio STRENGTH[Rank.TWO] è 1 e STRENGTH[Rank.ACE] è 10: tra due carte
# dello stesso seme vince quella con il numero più alto.
STRENGTH = {}
for _index in range(len(STRENGTH_ORDER)):
    STRENGTH[STRENGTH_ORDER[_index]] = _index + 1


# frozen=True: dopo la creazione i campi non si possono più cambiare (card.suit = ...
# dà errore). Serve perché il motore non modifica mai uno stato: ne crea uno nuovo
# (P13). Una carta "congelata" si può anche usare come chiave di un dizionario o
# metterla in un insieme (set).
@dataclass(frozen=True)
class Card:
    """Una carta: il seme e il valore.

    In parole semplici:
        Card(Suit.COPPE, Rank.ACE) è l'Asso di coppe.
        card.points, card.strength e card.code si leggono come campi, ma sono
        calcolati ogni volta dalle tabelle qui sopra (vedi @property sotto).
    """

    # suit: il seme, per esempio Suit.COPPE
    suit: Suit
    # rank: il valore, per esempio Rank.ACE
    rank: Rank

    # @property: un decoratore che fa leggere una funzione come se fosse un campo.
    # Si scrive card.points (senza parentesi) e Python chiama questa funzione.
    @property
    def points(self) -> int:
        """Punti della carta a fine mano.

        In parole semplici:
            card.points
            Per esempio 11 per un Asso, 0 per un 7. Li sommano game.py (hand_result)
            e la CPU.
        """
        return POINTS[self.rank]

    @property
    def strength(self) -> int:
        """Forza nella presa: più alta è, più la carta è forte (2 vale 1, Asso vale 10).

        In parole semplici:
            card.strength
            La usa trick.py per decidere chi vince la presa, e auto_move.py per
            scegliere la carta più debole.
        """
        return STRENGTH[self.rank]

    @property
    def code(self) -> str:
        """Codice stabile usato nelle viste e nelle azioni, per esempio "denari-1".

        In parole semplici:
            card.code
            Il seme come testo, un trattino e il numero del valore. Si usa come
            chiave fissa per riconoscere una carta (per esempio in _BY_CODE qui sotto).
        """
        return f"{self.suit.value}-{self.rank.value}"

    # @classmethod: la funzione si chiama dalla classe (Card.from_code(...)), non da una
    # carta già fatta; il primo parametro, cls, è la classe Card stessa.
    @classmethod
    def from_code(cls, code: str) -> "Card":
        """Carta dal suo codice; un codice sconosciuto è una mossa non valida.

        In parole semplici:
            Card.from_code("denari-1")
            Restituisce l'Asso di denari. Il confronto è esatto con i 40 codici:
            "denari-01" o un numero al posto del testo si rifiutano con
            InvalidMoveError("Carta non valida.").

            code: il testo del codice, per esempio "coppe-10".

            Nota: nel programma oggi la usano solo i test; la stanza riceve le carte
            dal client come {"suit", "rank"} e le converte da sé.
        """
        card = None
        if isinstance(code, str):
            # get: come [code], ma se il codice non c'è restituisce None invece di un errore
            card = _BY_CODE.get(code)
        if card is None:
            raise InvalidMoveError("Carta non valida.")
        return card

    def __str__(self) -> str:
        """Il nome della carta in italiano, per i messaggi.

        In parole semplici:
            str(card), oppure la carta dentro una f-string
            Per esempio "Re di coppe". La usa singing.py nei messaggi di rifiuto.
        """
        return f"{RANK_NAMES[self.rank]} di {self.suit.value}"


# _BY_CODE: le 40 carte, ognuna con il suo codice come chiave, per esempio
# {"denari-1": Card(Suit.DENARI, Rank.ACE), ...}. Confronto esatto con i 40 codici:
# niente conversioni che accettino "denari-01" o "denari- 1"
_BY_CODE = {}
for _suit in Suit:
    for _rank in Rank:
        _card = Card(_suit, _rank)
        _BY_CODE[_card.code] = _card
