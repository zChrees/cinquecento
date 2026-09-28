"""Rotte: tavolo di gioco (P21).

/game/<game_id> è l'indirizzo che il server manda con game:start (contratto 3.2).
La pagina si collega alla stanza con i socket (P24); per ora, in sviluppo e nei
test, con ?demo=1v1 o ?demo=2v2 disegna una vista finta di app/static/dev/.
"""

import re

from flask import abort, current_app, render_template, request, url_for
from flask_login import login_required

from app.blueprints.game import bp

# Codice della stanza (testo, non il numero della partita nel database)
GAME_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")
DEMO_VIEWS = {"1v1": "dev/vista_1v1.json", "2v2": "dev/vista_2v2.json"}
DEMO_ENVS = {"development", "testing"}


@bp.get("/<game_id>")
@login_required
def table(game_id):
    if not GAME_ID.fullmatch(game_id):
        abort(404)
    demo = request.args.get("demo")
    demo_url = None
    if demo is not None:
        # Le viste finte esistono solo in sviluppo e nei test, mai nella demo vera
        if demo not in DEMO_VIEWS or current_app.config["ENV_NAME"] not in DEMO_ENVS:
            abort(404)
        demo_url = url_for("static", filename=DEMO_VIEWS[demo])
    return render_template("game/table.html", game_id=game_id, demo_url=demo_url)
