"""Rotte: tavolo di gioco (P21).

/game/<game_id> è l'indirizzo che il server manda con game:start (contratto 3.2).
La pagina si collega alla stanza con i socket (P24); per ora, in sviluppo e nei
test, con ?demo=1v1 o ?demo=2v2 disegna una vista finta di app/static/dev/.

Passo 8 della migrazione (docs/MIGRAZIONE-FRONTEND.md, "Piano del passo 8"): dal
lotto 8h (23/10/2026) l'indirizzo dà sempre il tavolo React (frontend/src/game/), in
tutti gli ambienti. Il tavolo Jinja resta raggiungibile con ?ui=jinja fino al passo 9,
quando si toglie; ?ui=react (l'indirizzo dei lotti 8a-8g) dà ancora il tavolo React.
Le regole di ?demo= sono le stesse per tutti e due.
"""

import re

from flask import abort, current_app, render_template, request, url_for
from flask_login import login_required

from app.blueprints.game import bp
from app.blueprints.spa.routes import spa_page

# Codice della stanza (testo, non il numero della partita nel database)
GAME_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")
DEMO_VIEWS = {"1v1": "dev/vista_1v1.json", "2v2": "dev/vista_2v2.json"}
DEMO_ENVS = {"development", "testing"}
# UI_REACT e UI_JINJA: i valori ammessi di ?ui= (passo 8): il tavolo React, quello di
# sempre dall'8h, e il tavolo Jinja, fino al passo 9; ogni altro valore è 404
UI_REACT = "react"
UI_JINJA = "jinja"


@bp.get("/<game_id>")
@login_required
def table(game_id):
    """GET /game/<game_id>: il tavolo (React; Jinja con ?ui=jinja fino al passo 9).

    In parole semplici:
        table("e5f6a7b8")
        Controlla il codice della stanza e ?demo= (solo in sviluppo e nei test, solo
        1v1 o 2v2). Risponde con la pagina della SPA (spa_page): il tavolo lo disegna
        React, che legge da sé game_id e ?demo= dall'indirizzo. Con ?ui=jinja
        risponde con il template di prima. Un altro valore di ?ui= è un indirizzo
        sbagliato: 404, invece di ignorarlo in silenzio.

        Restituisce: la pagina (SPA o template), oppure 404.
    """
    if not GAME_ID.fullmatch(game_id):
        abort(404)
    ui = request.args.get("ui")
    if ui is not None and ui not in (UI_REACT, UI_JINJA):
        abort(404)
    demo = request.args.get("demo")
    demo_url = None
    if demo is not None:
        # Le viste finte esistono solo in sviluppo e nei test, mai nella demo vera
        if demo not in DEMO_VIEWS or current_app.config["ENV_NAME"] not in DEMO_ENVS:
            abort(404)
        demo_url = url_for("static", filename=DEMO_VIEWS[demo])
    if ui == UI_JINJA:
        return render_template("game/table.html", game_id=game_id, demo_url=demo_url)
    return spa_page()
