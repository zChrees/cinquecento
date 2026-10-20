"""Rotte della home (P22).

Dal passo 7d della migrazione la home (/) è una pagina della SPA (HomePage.tsx),
con gli stessi dati veri; la home Jinja descritta qui sotto resta su /vecchia-home,
solo in sviluppo e nei test, fino al passo 9.

La home si disegna con i dati che arrivano dal server: numero di giocatori online
e partita in corso (home:status, P44), coda (P28), amici da invitare (P47).
Finché quei punti non ci sono, in sviluppo e nei test la pagina usa i dati finti
di app/static/dev/ (attributi data-demo-*); con ?demo=rientro mostra anche
l'avviso "Hai una partita in corso". Nella demo vera i dati finti non ci sono.
Da P82 "giocatori online" non usa più i dati finti.

P82: GET /online dà il numero di giocatori online anche a chi non ha fatto il login
(contratto 5.1), che non si collega al tempo reale e quindi non riceve home:status.
Solo il numero, lo stesso di home:status: nessun dato sugli utenti.
"""

from flask import abort, current_app, render_template, request, url_for

from app.blueprints.main import bp
from app.blueprints.spa.routes import spa_page
from app.realtime.events import ok
from app.realtime.presence import presence

DEMO_ENVS = {"development", "testing"}
DEMO_STATES = {"rientro"}
DEMO_FILES = {
    "home": "dev/home_esempio.json",
    "friends": "dev/amici_esempio.json",
    "stats": "dev/statistiche_esempio.json",
}


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


@bp.get("/vecchia-home")
def old_index():
    """GET /vecchia-home: la home Jinja di prima (P22), solo in sviluppo e nei test.

    In parole semplici:
        old_index()
        Resta fino al passo 9 della migrazione perché i test del JavaScript vecchio
        (navbar, pannello amici, chat, carta-modal di js/) hanno bisogno di una
        pagina che li carichi. Altrove risponde 404, come se non esistesse. Al passo
        9 si cancellano insieme questa rotta, il template e il JavaScript vecchio.

        Restituisce: il template main/index.html, oppure 404.
    """
    if current_app.config["ENV_NAME"] not in DEMO_ENVS:
        abort(404)
    demo_state = _check_demo()
    demo_urls = {name: url_for("static", filename=path) for name, path in DEMO_FILES.items()}
    return render_template("main/index.html", demo_urls=demo_urls, demo_state=demo_state)


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


@bp.get("/online")
def online():
    return ok({"online_count": presence.count()}), 200, {"Cache-Control": "no-store"}
