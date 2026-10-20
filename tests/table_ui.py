"""Quale tavolo provano i test del tavolo nel browser (passo 8 della migrazione).

Fino al lotto 8h ci sono due tavoli allo stesso indirizzo: quello Jinja
(app/static/js/pages/game.js) e quello React (frontend/src/game/, con ?ui=react).
Invece di far girare ogni test su tutti e due (le suite del tavolo durerebbero il
doppio e supererebbero i 240 s del runner), i test aprono il tavolo con
table_path() e la variabile d'ambiente TABLE_UI sceglie quale:

    TABLE_UI non impostata, o "jinja"   il tavolo Jinja (come sempre)
    TABLE_UI=react                      il tavolo React

Per provare il tavolo React, in PowerShell:
    $env:TABLE_UI = "react"; python tests/esegui_tutti.py table3; Remove-Item Env:TABLE_UI

Con TABLE_UI=react il tavolo è una pagina della SPA: se il frontend non è compilato
per i test (manca Node o npm ci) il test si salta (needs_spa di tests/spa.py).
Scelta del 20/10/2026 (DECISIONI.md, passo 8). Al lotto 8h il predefinito diventa
"react".
"""

import os

from tests.spa import needs_spa

# UIS: i valori ammessi; un valore diverso è un errore di battitura, non si ignora
UIS = ("jinja", "react")


def table_ui():
    """Il tavolo scelto: 'jinja' (predefinito) oppure 'react'.

    In parole semplici:
        table_ui()  →  'jinja'
        Legge TABLE_UI. Con un valore non ammesso si ferma con un errore chiaro,
        invece di provare in silenzio il tavolo sbagliato.
    """
    ui = os.environ.get("TABLE_UI", "jinja")
    if ui not in UIS:
        raise ValueError(f"TABLE_UI vale {ui!r}: i valori ammessi sono {', '.join(UIS)}")
    return ui


def table_path(game_id, demo=None):
    """L'indirizzo del tavolo da aprire nel test.

    In parole semplici:
        table_path("prova", demo="1v1")
        → "/game/prova?demo=1v1"            con il tavolo Jinja
        → "/game/prova?demo=1v1&ui=react"   con il tavolo React (e salta il test
                                             se il frontend non è compilato)
        game_id: il codice della partita, per esempio "prova" o "e5f6a7b8".
        demo:    facoltativo, "1v1" o "2v2" per la vista finta; None per una partita vera.
    """
    params = []
    if demo is not None:
        params.append(f"demo={demo}")
    if table_ui() == "react":
        needs_spa()
        params.append("ui=react")
    path = f"/game/{game_id}"
    if params:
        path = f"{path}?{'&'.join(params)}"
    return path
