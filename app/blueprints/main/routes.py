"""Rotte della home (P22).

Dal passo 7d della migrazione la home (/) è una pagina della SPA (HomePage.tsx);
la home Jinja di prima (/vecchia-home) è stata tolta al lotto 9b-2.

La home si disegna con i dati che arrivano dal server: numero di giocatori online
e partita in corso (home:status, P44), coda (P28), amici da invitare (P47). In
sviluppo e nei test, con ?demo=rientro, mostra l'avviso "Hai una partita in corso"
con i dati finti di app/static/dev/home_esempio.json (li legge api/home.ts); online
?demo= non c'è.

P82: GET /api/online (fino al lotto 9c /online, ora 404) dà il numero di giocatori online anche a chi non ha fatto il login
(contratto 5.1), che non si collega al tempo reale e quindi non riceve home:status.
Solo il numero, lo stesso di home:status: nessun dato sugli utenti.
"""

from flask import abort, current_app, request

from app.blueprints.main import bp
from app.blueprints.spa.routes import spa_page
from app.realtime.events import ok
from app.realtime.presence import presence

DEMO_ENVS = {"development", "testing"}
DEMO_STATES = {"rientro"}


@bp.get("/")
def index():
    """GET /: la home, pagina della SPA dal passo 7d della migrazione (HomePage.tsx).

    In parole semplici:
        index()
        Risponde con la pagina della SPA (spa_page); poi è React, nel browser, a
        disegnare la home. Come prima, ?demo=rientro (l'avviso "Hai una partita in
        corso" con i dati finti) vale solo in sviluppo e nei test: altrove, o con un
        altro valore, risponde 404. Non serve il login: la home si apre anche senza.

        Restituisce: la pagina della SPA, oppure 404.
    """
    _check_demo()
    return spa_page()


def _check_demo():
    """Controlla ?demo= e lo restituisce (None se manca); con un valore non ammesso, 404.

    In parole semplici:
        _check_demo()  →  None, oppure 'rientro'
        ?demo= vale solo in sviluppo e nei test (DEMO_ENVS) e solo con i valori di
        DEMO_STATES; altrimenti la richiesta finisce con 404 (abort ferma la funzione).
    """
    demo_state = request.args.get("demo")
    if demo_state is not None and (demo_state not in DEMO_STATES or current_app.config["ENV_NAME"] not in DEMO_ENVS):
        abort(404)
    return demo_state


@bp.get("/api/online")
def online():
    return ok({"online_count": presence.count()}), 200, {"Cache-Control": "no-store"}
