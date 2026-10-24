"""Chi vince la presa (P11, regole in docs/REGOLE-GIOCO.md, "Chi vince la presa").

Non c'è obbligo di rispondere al seme: vince la briscola più forte, se ne è stata
giocata almeno una; altrimenti la carta più forte del seme giocato per primo.
Le carte di altri semi non prendono mai.

Cosa contiene:
    trick_winner(cards, trump)       chi vince una presa completa, per esempio 1
    winning_position(cards, trump)   chi la sta vincendo, anche a presa non finita

Tutte e due restituiscono una POSIZIONE nella presa (0 = chi l'ha aperta, 1 = il
secondo che ha giocato, ...), non un posto al tavolo: chi le chiama la trasforma nel
posto del giocatore.

DA DOVE ARRIVANO I DATI: game.py chiama trick_winner quando la presa si chiude, con le
carte della presa in corso e la briscola dello stato della mano; views.py chiama
winning_position per mostrare chi sta vincendo la presa in corso (P75).
"""

# Sequence: il tipo "qualcosa che si legge in ordine con un indice", come una lista o
# una tupla. Serve solo per scrivere i tipi dei parametri.
from collections.abc import Sequence

from app.game.engine.cards import Card, Suit
from app.game.engine.errors import EngineError
from app.game.engine.rules import MARIANNA


def trick_winner(cards: Sequence[Card], trump: Suit | None) -> int:
    """Posizione della carta vincente nell'ordine di gioco (0 = chi ha aperto la presa).

    trump è None finché nessuno ha cantato 40 (carte franche).

    In parole semplici:
        trick_winner(cards, trump)
        Controlla che la presa sia completa (2 carte nel 1v1, 4 nel 2v2) e poi chiede
        a winning_position chi la vince.

        cards: le carte della presa nell'ordine in cui sono state giocate, per
               esempio [Card(Suit.COPPE, Rank.TWO), Card(Suit.COPPE, Rank.ACE)].
               Arriva da game.py, dalle giocate della presa in corso.
        trump: il seme di briscola, per esempio Suit.SPADE, oppure None se nessuno
               ha ancora cantato. Arriva da game.py (state.trump).

        Restituisce: la posizione della carta vincente; nell'esempio 1 (l'Asso).
    """
    if len(cards) not in MARIANNA.player_counts:
        raise EngineError("Una presa completa ha 2 o 4 carte.")
    return winning_position(cards, trump)


def winning_position(cards: Sequence[Card], trump: Suit | None) -> int:
    """Come trick_winner, ma anche a presa non finita (P75): la carta che la vincerebbe se finisse lì.

    trick_winner la usa per la presa completa, così la vista e il motore non possono dare
    risposte diverse.

    In parole semplici:
        winning_position(cards, trump)
        Prima controlla che i dati abbiano senso (da 1 a 4 carte, tutte carte vere,
        nessuna ripetuta, briscola valida), poi cerca la carta più forte.

        cards: le carte giocate finora, da 1 a 4, nell'ordine di gioco.
               Arriva da trick_winner o da views.py (la presa in corso).
        trump: il seme di briscola, oppure None (carte franche).

        Restituisce: la posizione della carta che vince (0 = la prima giocata).
    """
    # max_cards: il numero più grande di carte in una presa, cioè 4 (il 2v2)
    max_cards = max(MARIANNA.player_counts)
    if len(cards) < 1 or len(cards) > max_cards:
        raise EngineError("Una presa ha da 1 a 4 carte.")
    for card in cards:
        if not isinstance(card, Card):
            raise EngineError("La presa contiene qualcosa che non è una carta.")
    # set: un insieme, che tiene ogni elemento una volta sola; se è più corto della
    # presa, vuol dire che una carta compare due volte
    if len(set(cards)) != len(cards):
        raise EngineError("La stessa carta compare due volte nella presa.")
    if trump is not None and not isinstance(trump, Suit):
        raise EngineError("Briscola non valida.")

    # lead: il seme di chi ha aperto la presa (la prima carta)
    lead = cards[0].suit

    def rank_in_trick(position: int) -> tuple[bool, bool, int]:
        """Il "punteggio" della carta in quella posizione, da confrontare con le altre.

        In parole semplici:
            rank_in_trick(position)
            Una funzione scritta dentro un'altra: la usa solo winning_position, e
            legge cards, trump e lead direttamente da lei, senza riceverli come
            parametri. Per esempio (True, False, 10) per l'Asso di briscola quando
            si è aperto con un altro seme.

            position: la posizione della carta nella presa, da 0 a len(cards) - 1.

            Restituisce tre valori, confrontati uno dopo l'altro:
              1. è di briscola?          (una briscola batte sempre una carta non di briscola)
              2. è del seme di uscita?   (batte le carte degli altri semi, che non prendono mai)
              3. la sua forza            (tra due carte dello stesso tipo vince la più forte)
        """
        card = cards[position]
        is_trump = card.suit == trump
        is_lead = card.suit == lead
        return (is_trump, is_lead, card.strength)

    # Si cerca la carta migliore con una ricerca lineare, come il massimo di un array
    # in C. Python confronta le tuple (a, b, c) proprio così: prima a, a parità b,
    # poi c; True vale più di False. Con ">" (non ">=") a parità resta la prima trovata.
    best = 0
    best_rank = rank_in_trick(0)
    for position in range(1, len(cards)):
        rank = rank_in_trick(position)
        if rank > best_rank:
            best = position
            best_rank = rank
    return best
