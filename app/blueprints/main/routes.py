"""Rotte della home (P22).

La home si disegna con i dati che arrivano dal server: numero di giocatori online
e partita in corso (home:status, P44), coda (P28), amici da invitare (P47).
Finché quei punti non ci sono, in sviluppo e nei test la pagina usa i dati finti
di app/static/dev/ (attributi data-demo-*); con ?demo=rientro mostra anche
l'avviso "Hai una partita in corso". Nella demo vera i dati finti non ci sono.
"""

from flask import abort, current_app, render_template, request, url_for

from app.blueprints.main import bp

DEMO_ENVS = {"development", "testing"}
DEMO_STATES = {"rientro"}
DEMO_FILES = {
    "home": "dev/home_esempio.json",
    "friends": "dev/amici_esempio.json",
    "stats": "dev/statistiche_esempio.json",
}


@bp.get("/")
def index():
    demo_env = current_app.config["ENV_NAME"] in DEMO_ENVS
    demo_state = request.args.get("demo")
    if demo_state is not None and (demo_state not in DEMO_STATES or not demo_env):
        abort(404)
    demo_urls = None
    if demo_env:
        demo_urls = {name: url_for("static", filename=path) for name, path in DEMO_FILES.items()}
    return render_template("main/index.html", demo_urls=demo_urls, demo_state=demo_state)
