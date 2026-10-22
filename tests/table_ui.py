"""Quale tavolo provano i test del tavolo nel browser (passo 8 della migrazione).

Fino al passo 9 ci sono due tavoli: quello React (frontend/src/game/), che dal
lotto 8h è /game/<codice>, e quello Jinja (app/static/js/pages/game.js), con
?ui=jinja. Invece di far girare ogni test su tutti e due (le suite del tavolo
durerebbero il doppio e supererebbero i 240 s del runner), i test aprono il tavolo
con table_path() e la variabile d'ambiente TABLE_UI sceglie quale:

    TABLE_UI non impostata, o "react"   il tavolo React (dal lotto 8h, 23/10/2026)
    TABLE_UI=jinja                      il tavolo Jinja, fino al passo 9

Per provare il tavolo Jinja, in PowerShell:
    $env:TABLE_UI = "jinja"; python tests/esegui_tutti.py table3; Remove-Item Env:TABLE_UI

Il tavolo React è una pagina della SPA: se il frontend non è compilato per i test
(manca Node o npm ci) il test si salta (needs_spa di tests/spa.py).
Scelta del 20/10/2026 (DECISIONI.md, passo 8); predefinito "react" dal lotto 8h.
"""

import os

from tests.spa import needs_spa

# UIS: i valori ammessi; un valore diverso è un errore di battitura, non si ignora
UIS = ("jinja", "react")


def table_ui():
    """Il tavolo scelto: 'react' (predefinito dal lotto 8h) oppure 'jinja'.

    In parole semplici:
        table_ui()  →  'react'
        Legge TABLE_UI. Con un valore non ammesso si ferma con un errore chiaro,
        invece di provare in silenzio il tavolo sbagliato.
    """
    ui = os.environ.get("TABLE_UI", "react")
    if ui not in UIS:
        raise ValueError(f"TABLE_UI vale {ui!r}: i valori ammessi sono {', '.join(UIS)}")
    return ui


def table_path(game_id, demo=None):
    """L'indirizzo del tavolo da aprire nel test.

    In parole semplici:
        table_path("prova", demo="1v1")
        → "/game/prova?demo=1v1"            con il tavolo React (e salta il test
                                             se il frontend non è compilato)
        → "/game/prova?demo=1v1&ui=jinja"   con il tavolo Jinja
        game_id: il codice della partita, per esempio "prova" o "e5f6a7b8".
        demo:    facoltativo, "1v1" o "2v2" per la vista finta; None per una partita vera.
    """
    params = []
    if demo is not None:
        params.append(f"demo={demo}")
    if table_ui() == "react":
        needs_spa()
    else:
        params.append("ui=jinja")
    path = f"/game/{game_id}"
    if params:
        path = f"{path}?{'&'.join(params)}"
    return path
