"""Parametri della variante siciliana (Marianna), da docs/REGOLE-GIOCO.md (P10).

I punteggi per vincere sono anche in config.py (TARGET_SCORES): il motore non può
importarlo, quindi un test controlla che le due liste restino uguali.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RuleSet:
    player_counts: tuple[int, ...] = (2, 4)  # 1v1 e 2v2
    hand_size: int = 5
    must_follow_suit: bool = False
    sing_40_points: int = 40  # primo canto della mano: fissa la briscola
    sing_20_points: int = 20  # canti successivi
    min_hand_to_sing_after_deck: int = 3  # a mazzo finito, con 2 carte non si canta
    last_trick_bonus: int = 0
    lay_down_max_cards_without_trump: int = 2  # senza briscola si cala solo con 2 carte o meno (D45)
    target_scores: tuple[int, ...] = (150, 300, 500)


MARIANNA = RuleSet()
