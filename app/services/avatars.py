"""Set degli avatar (P17, D29): 12 avatar, i 4 semi e 8 figure siciliane.

Il codice si salva in utenti.avatar (al massimo 30 caratteri) e arriva alle pagine
come `avatar` (contratto, 1.1); vuoto = iniziale del nome. Il server rifiuta ogni
codice fuori da questo elenco. Le immagini arrivano con P43, una per codice: fino
ad allora le pagine mostrano il nome.
Un codice già scelto da qualcuno non si cambia più: resterebbe nel database.
"""

# Codice -> nome mostrato, nell'ordine della pagina delle impostazioni
AVATARS = {
    "coppe": "Coppe",
    "denari": "Denari",
    "spade": "Spade",
    "bastoni": "Bastoni",
    "re_coppe": "Re di coppe",
    "re_denari": "Re di denari",
    "re_spade": "Re di spade",
    "re_bastoni": "Re di bastoni",
    "cavallo_coppe": "Cavallo di coppe",
    "cavallo_bastoni": "Cavallo di bastoni",
    "fante_denari": "Fante di denari",
    "fante_spade": "Fante di spade",
}


def is_valid(code):
    return isinstance(code, str) and code in AVATARS
