"""Rotte della SPA (passo 1 della migrazione, docs/MIGRAZIONE-FRONTEND.md, sezione 6).

Il frontend React è una sola pagina HTML, app/static/dist/index.html, scritta da
`npm run build` in frontend/ (la cartella dist/ non è nel repository, D54). Per
ogni indirizzo della SPA Flask restituisce sempre quella pagina; poi è React
Router, nel browser, a scegliere cosa disegnare. I file JavaScript della SPA
(/static/dist/assets/...) li serve Flask come ogni altro file statico.

Cosa contiene:
    dist_dir()     la cartella del build
    spa_page()     la risposta con index.html (o l'errore se il build manca); la
                   usano anche le rotte di altri blueprint che sono pagine della
                   SPA (per esempio /auth/login in app/blueprints/auth/routes.py e la home /
                   in app/blueprints/main/routes.py, dal passo 7d)
    asset(...)     GET /static/dist/<file>, i file JavaScript della SPA

DA DOVE ARRIVANO I DATI: il browser chiede un indirizzo della SPA (per esempio
/auth/login); Flask chiama la funzione della rotta, che legge il file scritto
dal build.
"""

import logging
from pathlib import Path

from flask import current_app, send_file, send_from_directory

from app.blueprints.spa import bp

log = logging.getLogger(__name__)

# SPA_PATHS: gli indirizzi che sono pagine della SPA. Deve restare uguale a
# SPA_PATHS di frontend/vite.config.ts (lo controlla tests/frontend/test_spa.py):
# una pagina nuova della SPA si aggiunge in tutti e due i posti, più la sua rotta
# (qui, o nel blueprint del suo argomento con spa_page(), come /auth/login).
SPA_PATHS = ("/", "/auth/login", "/auth/register", "/profile/settings")

# NOT_BUILT: il messaggio quando manca il build, invece di una pagina bianca
NOT_BUILT = "Frontend non compilato: lancia npm run build in frontend/."


def dist_dir():
    """Restituisce la cartella del build del frontend (app/static/dist).

    In parole semplici:
        dist_dir()
        È una funzione, non una costante, perché la cartella static la conosce
        solo l'app di Flask attiva (current_app). Nei test la cartella è un'altra,
        fuori dal progetto: SPA_DIST_DIR (config.py, solo con APP_ENV=testing),
        dove tests/conftest.py compila il frontend; alcuni test la sostituiscono
        con una cartella finta.

        Restituisce: un Path, per esempio C:/.../app/static/dist
    """
    configured = current_app.config.get("SPA_DIST_DIR")
    if configured:
        return Path(configured)
    return Path(current_app.static_folder) / "dist"


def spa_page():
    """Risponde con la pagina della SPA (index.html del build).

    In parole semplici:
        spa_page()
        Se il build c'è, manda index.html. Il browser deve richiederla ogni
        volta (max_age=0, cioè "Cache-Control: no-cache"): dopo un build nuovo
        index.html punta a file con un nome nuovo (index-3f9a1c.js), e una copia
        vecchia caricherebbe i file di prima.
        Se il build manca, risponde 503 ("servizio non disponibile") con un
        messaggio che dice cosa fare, e lo scrive nel log come anomalia.

        Restituisce: la risposta di Flask.
    """
    # index: il file scritto da npm run build
    index = dist_dir() / "index.html"
    if not index.is_file():
        log.warning("SPA: manca il build del frontend (%s)", index)
        return NOT_BUILT, 503, {"Content-Type": "text/plain; charset=utf-8"}
    return send_file(index, mimetype="text/html", max_age=0)


@bp.get("/static/dist/<path:filename>")
def asset(filename):
    """GET /static/dist/<file>: un file del build (per esempio assets/index-3f9a1c.js).

    In parole semplici:
        asset("assets/index-3f9a1c.js")
        Lo prende da dist_dir(). Con il build in app/static/dist farebbe lo stesso
        la rotta static di Flask; questa serve quando il build sta altrove (i test).
        Questa rotta vince su quella static perché il suo indirizzo ha un pezzo
        fisso in più (/static/dist/), e Flask sceglie la rotta più precisa.
        send_from_directory non esce mai dalla cartella (niente ../).
    """
    return send_from_directory(dist_dir(), filename)

