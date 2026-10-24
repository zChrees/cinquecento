"""Rotte della SPA (il frontend React).

Il frontend React è una sola pagina HTML, app/static/dist/index.html, scritta da
`npm run build` in frontend/ (la cartella dist/ non è nel repository, D54). Per
ogni indirizzo della SPA Flask restituisce sempre quella pagina; poi è React
Router, nel browser, a scegliere cosa disegnare. I file JavaScript della SPA
(/static/dist/assets/...) li serve Flask come ogni altro file statico.

Regola unica: ogni indirizzo
chiesto con GET che non ha una rotta Flask ed è fuori da /api/, /static/ e
/socket.io riceve la SPA; se React non conosce l'indirizzo, disegna "Pagina non
trovata" (NotFoundPage.tsx). Hanno una rotta Flask apposta solo le pagine dove il
server controlla qualcosa prima di mandarle: / (?demo=rientro), /auth/login e
/auth/register (chi ha il login va alla home), /profile/settings e /game/<id>
(login; codice della stanza e ?demo=). La regola la applica il gestore del 404
(app/errors.py), che chiama spa_fallback(): così un metodo sbagliato su una rotta
che esiste resta 405, e i 404 decisi da una rotta (abort) restano 404.

Cosa contiene:
    dist_dir()       la cartella del build
    spa_page()       la risposta con index.html (o l'errore se il build manca); la
                     usano anche le rotte di altri blueprint che sono pagine della
                     SPA (per esempio /auth/login in app/blueprints/auth/routes.py e la home /
                     in app/blueprints/main/routes.py)
    spa_fallback()   la regola unica: la SPA per un indirizzo senza rotta, o None
    asset(...)       GET /static/dist/<file>, i file JavaScript della SPA

DA DOVE ARRIVANO I DATI: il browser chiede un indirizzo della SPA (per esempio
/auth/login); Flask chiama la funzione della rotta (o, se non c'è, il gestore del
404), che legge il file scritto dal build.
"""

import logging
from pathlib import Path

from flask import current_app, redirect, request, send_file, send_from_directory

from app.blueprints.spa import bp

log = logging.getLogger(__name__)

# NOT_SPA: il primo pezzo degli indirizzi che non sono mai pagine della SPA (dati,
# file statici, tempo reale). Deve restare uguale a FLASK_PATHS di
# frontend/vite.config.ts, che in sviluppo li gira a Flask (lo controlla
# tests/frontend/test_spa.py).
NOT_SPA = ("api", "static", "socket.io")
# SPA_METHODS: la SPA si manda solo a chi chiede una pagina (HEAD è un GET senza
# contenuto); un POST a un indirizzo che non esiste resta 404
SPA_METHODS = ("GET", "HEAD")

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
        rimasta nel browser caricherebbe quelli del build precedente.
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


def spa_fallback():
    """La regola unica della SPA: decide se un 404 diventa la pagina della SPA.

    In parole semplici:
        spa_fallback()
        La chiama il gestore del 404 (app/errors.py) per ogni pagina non trovata.
        Risponde con la SPA solo se tutte e tre queste cose sono vere:
          - nessuna rotta Flask ha riconosciuto l'indirizzo (request.url_rule è
            None): se una rotta c'era, il 404 l'ha deciso lei (per esempio
            /?demo=altro o /static/manca.css) e resta la pagina di errore;
          - la richiesta è un GET (o HEAD);
          - l'indirizzo non comincia con un pezzo di NOT_SPA (/api, /static,
            /socket.io).
        Un indirizzo con la / in fondo (/profile/settings/) invece si rimanda a
        quello senza (/profile/settings), con gli stessi parametri: così valgono i
        controlli della sua rotta Flask (login, ?demo=), che React non farebbe.
        La pagina React "non trovata" risponde 200, non 404: lo stato lo sa solo il
        server, e qui il server non sa quali indirizzi conosce React.

        Esempi:
            GET /pagina-a-caso        ->  la SPA (React: "Pagina non trovata")
            GET /profile/settings/    ->  rimando (302) a /profile/settings
            GET /api/niente           ->  None (404 in JSON)
            POST /pagina-a-caso       ->  None (404)

        Restituisce: la risposta di Flask, oppure None (resta la risposta 404).
    """
    if request.url_rule is not None or request.method not in SPA_METHODS:
        return None
    # first: il primo pezzo dell'indirizzo, per esempio "api" per /api/niente
    first = request.path.lstrip("/").split("/")[0]
    if first in NOT_SPA:
        return None
    if request.path != "/" and request.path.endswith("/"):
        # target: l'indirizzo senza / in fondo, e con una sola / davanti: //altro.it/
        # diventerebbe //altro.it, che il browser leggerebbe come un altro sito
        target = "/" + request.path.strip("/")
        if request.query_string:
            # la stringa dei parametri arriva come byte, così come l'ha mandata il browser
            target = f"{target}?{request.query_string.decode('latin-1')}"
        # 302: rimando temporaneo, il browser non lo ricorda (un domani /x/ potrebbe esistere)
        return redirect(target, 302)
    return spa_page()


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

