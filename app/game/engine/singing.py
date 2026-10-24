"""Cantare 40 e 20 (P12, regole in docs/REGOLE-GIOCO.md, "Canti").

Si canta un seme alla volta: il primo canto della mano vale 40 e fissa la briscola,
i successivi valgono 20. I canti della mano sono un elenco di Sing in ordine, come
"sings" nella vista (docs/CONTRATTO-SOCKET.md, 3.3): la briscola e i semi già
cantati si ricavano da lì.

Lo stato della mano arriva con P13: qui i dati si passano uno per uno.

Cosa contiene:
    Sing(seat, suit, points)   un canto, per esempio Sing(0, Suit.COPPE, 40)
    trump_from_sings(sings)    la briscola, per esempio Suit.COPPE, oppure None
    singable_suits(...)        i semi che si possono cantare adesso, per esempio [Suit.SPADE]
    sing(suit, ...)            controlla un canto e lo restituisce con i suoi punti

singable_suits e sing usano lo stesso controllo (_refusal), così danno sempre la
stessa risposta: una prova su 3.000 situazioni lo verifica.

DA DOVE ARRIVANO I DATI: game.py chiama singable_suits per le mosse legali
(legal.sing) e sing quando arriva un'azione di canto, passando i pezzi dello stato
della mano; lay_down.py li usa per i canti del compagno quando si cala (D45);
state.py usa trump_from_sings per la briscola.
"""

# Collection e Sequence: tipi generici per i parametri. Collection = "qualcosa in cui
# si può cercare con in" (una lista, una tupla, un insieme); Sequence = "qualcosa che
# si legge in ordine con un indice" (una lista o una tupla).
from collections.abc import Collection, Sequence
from dataclasses import dataclass

from app.game.engine.cards import Card, Rank, Suit
from app.game.engine.errors import InvalidMoveError, NotYourTurnError
from app.game.engine.rules import MARIANNA, RuleSet


# @dataclass(frozen=True): costruttore automatico e campi che non si cambiano più
# (vedi il commento in cards.py)
@dataclass(frozen=True)
class Sing:
    """Un canto della mano.

    In parole semplici:
        Sing(0, Suit.COPPE, 40)
        seat:   il posto di chi ha cantato, per esempio 0
        suit:   il seme cantato, per esempio Suit.COPPE
        points: 40 per il primo canto della mano, 20 per gli altri
    """

    seat: int
    suit: Suit
    points: int


def trump_from_sings(sings: Sequence[Sing]) -> Suit | None:
    """La briscola è il seme del primo canto; None finché nessuno ha cantato (carte franche).

    In parole semplici:
        trump_from_sings(sings)
        sings: i canti della mano in ordine, per esempio (Sing(0, Suit.COPPE, 40),).
               Arriva da state.py (HandState.trump).

        Restituisce: il seme del primo canto (nell'esempio Suit.COPPE), oppure None
        se l'elenco è vuoto.
    """
    if len(sings) > 0:
        return sings[0].suit
    return None


def _refusal(
    suit: Suit,
    hand: Collection[Card],
    sings: Sequence[Sing],
    played_cards: Collection[Card],
    deck_count: int,
    first_trick: bool,
    rules: RuleSet,
) -> str | None:
    """Perché quel seme non si può cantare adesso, oppure None se si può.

    In parole semplici:
        _refusal(suit, hand, sings, played_cards, deck_count, first_trick, rules)
        Controlla le regole del canto una dopo l'altra e restituisce il messaggio
        della prima che non va, per esempio "Nella prima presa della mano non si
        canta.". La usano sia singable_suits sia sing, qui sotto.

        suit:         il seme da controllare, per esempio Suit.COPPE
        hand:         le carte in mano a chi vuole cantare
        sings:        i canti già fatti nella mano, in ordine
        played_cards: le carte già giocate nella mano (state.played_cards)
        deck_count:   quante carte restano nel mazzo (0 = mazzo finito)
        first_trick:  True finché la prima presa della mano non si è chiusa (P64)
        rules:        le regole del gioco (MARIANNA)

        Restituisce: il messaggio di rifiuto (un testo), oppure None se si può cantare.
    """
    # 1. nella prima presa della mano nessuno canta (P64)
    if first_trick:
        return "Nella prima presa della mano non si canta."

    # 2. ogni seme si canta una volta sola per mano
    for done in sings:
        if done.suit == suit:
            return f"Il seme di {suit.value} è già stato cantato in questa mano."

    # 3. se il Re o il Cavallo di quel seme sono già sul tavolo, il seme è "bruciato"
    king = Card(suit, Rank.KING)
    knight = Card(suit, Rank.KNIGHT)
    for card in (king, knight):
        if card in played_cards:
            return f"Il {card} è già stato giocato: {suit.value} non si può più cantare."

    # 4. servono tutti e due in mano
    if king not in hand or knight not in hand:
        return f"Per cantare servono Re e Cavallo di {suit.value} nella tua mano."

    # 5. a mazzo finito si canta solo con almeno 3 carte in mano
    if deck_count == 0 and len(hand) < rules.min_hand_to_sing_after_deck:
        return f"A mazzo finito si canta solo con almeno {rules.min_hand_to_sing_after_deck} carte in mano."
    return None


# L'asterisco * da solo tra i parametri vuol dire: tutti quelli dopo si devono passare
# con il nome (singable_suits(hand=..., sings=...)), mai in ordine. Con tanti parametri
# dello stesso tipo evita di scambiarne due per sbaglio.
def singable_suits(
    *,
    hand: Collection[Card],
    sings: Sequence[Sing],
    played_cards: Collection[Card],
    deck_count: int,
    is_turn: bool,
    first_trick: bool,
    rules: RuleSet = MARIANNA,
) -> list[Suit]:
    """I semi che il giocatore può cantare adesso, sempre nello stesso ordine (legal.sing).

    In parole semplici:
        singable_suits(hand=..., sings=..., played_cards=..., deck_count=...,
                       is_turn=..., first_trick=...)
        Prova i quattro semi con _refusal e tiene quelli senza rifiuto.

        I parametri sono quelli di _refusal, più:
        is_turn: True se il giocatore è di turno e non ha ancora giocato la carta;
                 se è False la risposta è sempre un elenco vuoto.
        rules:   facoltativo, se manca vale MARIANNA.
        Arrivano da game.py (legal_actions) e lay_down.py, dallo stato della mano.

        Restituisce: l'elenco dei semi, nell'ordine di Suit (denari, coppe, spade,
        bastoni), per esempio [Suit.SPADE]; vuoto se non si può cantare niente.
    """
    if not is_turn:
        return []
    suits = []
    for suit in Suit:
        if _refusal(suit, hand, sings, played_cards, deck_count, first_trick, rules) is None:
            suits.append(suit)
    return suits


def sing(
    suit: Suit,
    *,
    seat: int,
    hand: Collection[Card],
    sings: Sequence[Sing],
    played_cards: Collection[Card],
    deck_count: int,
    is_turn: bool,
    first_trick: bool,
    rules: RuleSet = MARIANNA,
) -> Sing:
    """Controlla il canto e lo restituisce con i suoi punti; se non è ammesso lo rifiuta.

    is_turn è False anche dopo aver giocato la carta, perché la carta chiude il turno.
    first_trick è True finché la prima presa della mano non si chiude: lì nessuno canta (P64).

    In parole semplici:
        sing(Suit.COPPE, seat=0, hand=..., sings=..., played_cards=..., deck_count=...,
             is_turn=..., first_trick=...)
        suit: il seme che il giocatore vuole cantare; si passa in ordine, gli altri
              parametri con il nome (vedi l'asterisco sopra singable_suits).
        seat: il posto di chi canta, che finisce nel Sing restituito.
        Gli altri parametri sono quelli di singable_suits. Arrivano da game.py
        (apply, con un'azione di canto) e da lay_down.py (i canti del compagno).

        Restituisce: il Sing con i suoi punti, per esempio Sing(0, Suit.COPPE, 40).
        Se il canto non è ammesso lancia InvalidMoveError (o NotYourTurnError) con il
        messaggio da mostrare al giocatore.
    """
    if not isinstance(suit, Suit):
        raise InvalidMoveError("Seme non valido.")
    if not is_turn:
        raise NotYourTurnError("Non è il tuo turno.")
    reason = _refusal(suit, hand, sings, played_cards, deck_count, first_trick, rules)
    if reason is not None:
        raise InvalidMoveError(reason)

    # points: 40 se è il primo canto della mano (sings vuoto), altrimenti 20
    if len(sings) > 0:
        points = rules.sing_20_points
    else:
        points = rules.sing_40_points
    return Sing(seat, suit, points)
