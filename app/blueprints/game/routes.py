"""Rotte: tavolo di gioco (P21).

/game/<game_id> è l'indirizzo che il server manda con game:start (contratto 3.2).
La pagina si collega alla stanza con i socket (P24); in sviluppo e nei test, con
?demo=1v1 o ?demo=2v2 disegna una vista finta di app/static/dev/. Il tavolo lo
disegna la SPA (frontend/src/game/); gli altri parametri si ignorano.

Cosa contiene:
    GAME_ID      il codice ammesso di una stanza: lettere, numeri, _ e -, al massimo 64
    DEMO_VIEWS   le viste finte della prova, per esempio "1v1" → "dev/vista_1v1.json"
    DEMO_ENVS    dove vale ?demo= ({"development", "testing"})
    GET /game/<game_id>   table: il tavolo (SPA), solo con il login

DA DOVE ARRIVANO I DATI: l'indirizzo lo manda il server con game:start (o "Rientra"
della home); chi è collegato lo dice Flask-Login (current_user).
"""

import re

from flask import abort, current_app, request
from flask_login import login_required

from app.blueprints.game import bp
from app.blueprints.spa.routes import spa_page

# Codice della stanza (testo, non il numero della partita nel database)
GAME_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")
# DEMO_VIEWS: le viste finte della prova; i file li legge il tavolo React
# (DEMO_VIEWS di frontend/src/game/tableStore.ts), qui servono solo i nomi ammessi
DEMO_VIEWS = {"1v1": "dev/vista_1v1.json", "2v2": "dev/vista_2v2.json"}
DEMO_ENVS = {"development", "testing"}


# Due decoratori, letti dal basso: @login_required (di Flask-Login) controlla il login
# prima di chiamare la funzione; @bp.get dice a Flask a quale indirizzo risponde.
# <game_id> nell'indirizzo arriva alla funzione come parametro.
@bp.get("/<game_id>")
@login_required
def table(game_id):
    """GET /game/<game_id>: il tavolo React.

    In parole semplici:
        table("e5f6a7b8")
        Controlla il codice della stanza e ?demo= (solo in sviluppo e nei test, solo
        1v1 o 2v2). Risponde con la pagina della SPA (spa_page): il tavolo lo disegna
        React, che legge da sé game_id e ?demo= dall'indirizzo.

        Restituisce: la pagina della SPA, oppure 404.
    """
    if not GAME_ID.fullmatch(game_id):
        abort(404)
    demo = request.args.get("demo")
    # Le viste finte esistono solo in sviluppo e nei test, mai online
    demo_allowed = demo in DEMO_VIEWS and current_app.config["ENV_NAME"] in DEMO_ENVS
    if demo is not None and not demo_allowed:
        abort(404)
    return spa_page()
