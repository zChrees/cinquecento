"""Azioni che un giocatore può fare nel suo turno (P13): cantare un seme, giocare una carta
o, a mazzo finito, calare le carte (P84).

Cosa contiene:
    PlayCardAction(seat, card)   giocare una carta, per esempio PlayCardAction(0, Card(Suit.COPPE, Rank.ACE))
    SingAction(seat, suit)       cantare un seme, per esempio SingAction(1, Suit.SPADE)
    LayDownAction(seat)          calare le carte, per esempio LayDownAction(2)
    Action                       "una qualsiasi delle tre"

DA DOVE ARRIVANO I DATI: la stanza (app/realtime/room.py) le crea dagli eventi che
arrivano dal browser (game:play, game:sing, game:lay_down), dalla mossa automatica
(auto_move.py) o dalla CPU (cpu.py), e le passa ad apply di game.py.
In ogni azione "seat" è il posto di chi la fa, da 0 a 3, nell'ordine di gioco.
"""

from dataclasses import dataclass

from app.game.engine.cards import Card, Suit


# @dataclass(frozen=True): costruttore automatico e campi che non si cambiano più
# (vedi il commento in cards.py). Un'azione è solo un contenitore di dati, come una
# struct del C.
@dataclass(frozen=True)
class PlayCardAction:
    """Giocare una carta.

    In parole semplici:
        PlayCardAction(0, card)
        seat: il posto di chi gioca, per esempio 0
        card: la carta giocata, per esempio Card(Suit.COPPE, Rank.ACE)
    """

    seat: int
    card: Card


@dataclass(frozen=True)
class SingAction:
    """Un seme alla volta: il primo canto della mano vale 40, i successivi 20.

    In parole semplici:
        SingAction(1, Suit.SPADE)
        seat: il posto di chi canta, per esempio 1
        suit: il seme cantato, per esempio Suit.SPADE (servono Re e Cavallo di spade)
    """

    seat: int
    suit: Suit


@dataclass(frozen=True)
class LayDownAction:
    """"Cala le carte" (P84, D45): la squadra di chi cala prende tutte le prese rimaste.

    In parole semplici:
        LayDownAction(2)
        seat: il posto di chi cala, per esempio 2
    """

    seat: int


# Action: un "alias di tipo", cioè un nome corto per un tipo. La barra | vuol dire
# "oppure": un'Action è una PlayCardAction oppure una SingAction oppure una
# LayDownAction. Serve solo a scrivere i tipi dei parametri (per esempio in apply di
# game.py): Python non lo controlla mentre il programma gira.
Action = PlayCardAction | SingAction | LayDownAction
