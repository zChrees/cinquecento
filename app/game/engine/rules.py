"""Parametri della variante siciliana (Marianna), da docs/REGOLE-GIOCO.md (P10).

I punteggi per vincere sono anche in config.py (TARGET_SCORES): il motore non può
importarlo, quindi un test controlla che le due liste restino uguali.

Cosa contiene:
    RuleSet    l'elenco dei numeri che definiscono le regole, per esempio RuleSet().hand_size = 5
    MARIANNA   le regole della nostra variante, quelle usate in tutto il programma

DA DOVE ARRIVANO I DATI: sono scritti qui. Le funzioni del motore ricevono le regole
come parametro "rules", che se manca vale MARIANNA; i test possono passarne altre.
"""

from dataclasses import dataclass


# @dataclass(frozen=True): crea da solo il costruttore dai campi qui sotto e impedisce
# di cambiarli dopo (vedi il commento in cards.py). Il valore dopo "=" è quello che il
# campo prende se non si passa niente: RuleSet() ha tutti i valori della Marianna.
@dataclass(frozen=True)
class RuleSet:
    """I numeri delle regole del gioco.

    In parole semplici:
        RuleSet()                    le regole della Marianna (tutti i valori qui sotto)
        RuleSet(hand_size=3)         uguali, ma con 3 carte in mano (solo per prova)
        rules.sing_40_points         si legge come un campo di una struct del C
    """

    # player_counts: quanti giocatori può avere una partita (2 = 1v1, 4 = 2v2).
    # tuple[int, ...] vuol dire "una tupla di numeri interi, lunga quanto serve"
    player_counts: tuple[int, ...] = (2, 4)
    # hand_size: quante carte ha in mano ognuno a inizio mano
    hand_size: int = 5
    # must_follow_suit: se bisogna rispondere al seme di chi apre (nella Marianna no)
    must_follow_suit: bool = False
    sing_40_points: int = 40  # primo canto della mano: fissa la briscola
    sing_20_points: int = 20  # canti successivi
    min_hand_to_sing_after_deck: int = 3  # a mazzo finito, con 2 carte non si canta
    # last_trick_bonus: punti in più a chi vince l'ultima presa (nella Marianna nessuno)
    last_trick_bonus: int = 0
    lay_down_max_cards_without_trump: int = 2  # senza briscola si cala solo con 2 carte o meno (D45)
    # target_scores: i punteggi per vincere che si possono scegliere (uguali a config.py)
    target_scores: tuple[int, ...] = (150, 300, 500)


# MARIANNA: le regole usate dal programma; è il valore predefinito di "rules" in tutto il motore
MARIANNA = RuleSet()
