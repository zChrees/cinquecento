"""Set degli avatar (P17, D29): 12 avatar, i 4 semi e 8 figure siciliane.

Il codice si salva in utenti.avatar (al massimo 30 caratteri) e arriva alle pagine
come `avatar` (contratto, 1.1); vuoto = iniziale del nome. Il server rifiuta ogni
codice fuori da questo elenco. Le immagini (P43) sono app/static/img/avatars/<codice>.svg,
una per codice; frontend/src/game/SeatAvatar.tsx (l'avatar al tavolo) ha una copia
dell'elenco (AVATAR_CODES), che tests/frontend/test_avatar.py confronta con questo.
Un codice già scelto da qualcuno non si cambia più: resterebbe nel database.

Cosa contiene:
    AVATARS          codice -> nome mostrato, per esempio "re_coppe" -> "Re di coppe"
    is_valid(code)   se il codice è dell'elenco: is_valid("re_coppe") = True

DA DOVE ARRIVANO I DATI: la pagina delle impostazioni (SettingsPage.tsx) chiede
l'elenco a GET /api/profile/avatars (app/blueprints/profile/api.py, che legge AVATARS)
e manda il codice scelto a POST /api/profile/avatar, che arriva a
auth_service.set_avatar e da lì a is_valid.
"""

# Codice -> nome mostrato, nell'ordine della pagina delle impostazioni.
# Un dizionario di Python tiene l'ordine in cui si sono scritte le chiavi.
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
    """True se code è uno dei codici di AVATARS.

    In parole semplici:
        is_valid(code)
        Per esempio is_valid("re_coppe") = True, is_valid("re_picche") = False,
        is_valid(None) = False (non è un testo).
        code: il codice mandato dalla pagina delle impostazioni (da auth_service.set_avatar)
    """
    return isinstance(code, str) and code in AVATARS
