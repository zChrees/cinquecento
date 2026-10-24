"""Pagine e risposte di errore (P7).

- 404: dal lotto 9d della migrazione vale la regola unica della SPA (spa_fallback di
  app/blueprints/spa/routes.py): un GET a un indirizzo senza rotta, fuori da /api/,
  /static/ e /socket.io, riceve la SPA, e la pagina "non trovata" la disegna React.
  La pagina di errore Jinja resta per il resto: file statici che mancano, 404 decisi
  da una rotta (per esempio ?demo= sbagliato) e richieste che non sono GET.
- 404 e 500: pagina in italiano basata su base.html, senza navbar (le pagine di errore
  non hanno uno script di pagina, e senza la navbar non si apre). Le richieste JSON
  (tutte sotto /api/: dal lotto 9c della migrazione anche amici e statistiche) ricevono invece
  la risposta del contratto (1.2):
  {"ok": false, "error": {"code": "not_found" o "server_error", "message"}}.
- 500: nessun dettaglio tecnico nella risposta. L'errore con il traceback va nel log
  (ERROR): lo scrive Flask stesso prima di chiamare il gestore (Flask.log_exception).
  Se nemmeno la pagina si può mostrare (un errore anche dentro il gestore, per
  esempio il database che non risponde al rollback o il template), si risponde con
  una pagina minima scritta qui.
- Eventi socket: un errore imprevisto in un gestore che non usa `handler`
  (app/realtime/events.py) va nel log, e la risposta server_error arriva solo a chi ha
  mandato l'evento; una connessione il cui controllo si è rotto si rifiuta.

Cosa contiene:
    JSON_PREFIXES                 gli inizi degli indirizzi JSON: ("/api/",)
    MINIMAL_500                   la pagina 500 di riserva, scritta qui come testo
    register_error_handlers(app)  collega i gestori qui sotto all'applicazione
    _wants_json()                 True se la richiesta è a un indirizzo JSON
    _not_found(exc)               404: JSON, SPA o pagina Jinja
    _csrf_error(exc)              codice CSRF mancante o scaduto
    _server_error(exc)            500: JSON o pagina Jinja (o quella minima)
    _socket_error(exc)            errore imprevisto in un evento del tempo reale

DA DOVE ARRIVANO I DATI: register_error_handlers la chiama create_app()
(app/__init__.py); i gestori li chiamano Flask e Flask-SocketIO quando qualcosa va
storto, con l'errore (exc) e la richiesta in corso (request).
"""

import logging

from flask import render_template, request
from flask_wtf.csrf import CSRFError

from app.blueprints.spa.routes import spa_fallback
from app.extensions import db, socketio
from app.realtime.events import error

log = logging.getLogger(__name__)

# Indirizzi delle richieste HTTP in JSON (contratto, sezione 2)
JSON_PREFIXES = ("/api/",)

# Due testi uno dopo l'altro tra parentesi diventano un testo solo (si scrive su più righe)
MINIMAL_500 = (
    '<!doctype html><html lang="it"><head><meta charset="utf-8">'
    "<title>Errore del server · Cinquecento</title></head><body>"
    "<h1>Errore del server</h1><p>Qualcosa è andato storto. Riprova tra poco.</p>"
    '<p><a href="/">Torna alla home</a></p></body></html>'
)


def register_error_handlers(app):
    """Chiamata da create_app(): pagine 404 e 500 ed errori degli eventi socket.

    In parole semplici:
        register_error_handlers(app)
        Dice a Flask quale funzione chiamare per ogni errore: _not_found per il 404,
        _server_error per il 500, _csrf_error per il codice CSRF sbagliato; e a
        Flask-SocketIO _socket_error per gli eventi. Le funzioni si passano senza
        chiamarle (senza le parentesi): in C sarebbero puntatori a funzione.
    """
    app.register_error_handler(404, _not_found)
    app.register_error_handler(500, _server_error)
    app.register_error_handler(CSRFError, _csrf_error)
    socketio.on_error_default(_socket_error)


def _wants_json():
    """True se la richiesta in corso è a un indirizzo JSON (sotto /api/).

    In parole semplici:
        _wants_json()
        Per esempio True per /api/friends/31, False per /profile/settings.
        startswith accetta anche una tupla: True se il testo comincia con uno
        qualunque dei prefissi.
    """
    return request.path.startswith(JSON_PREFIXES)


def _not_found(_exc):
    """La risposta per un 404.

    In parole semplici:
        _not_found(_exc)
        _exc è l'errore 404 di Flask: non serve (il trattino basso davanti lo dice).
        Sotto /api/ risponde not_found in JSON; altrimenti la SPA, se spa_fallback
        dice che l'indirizzo è suo (regola unica, lotto 9d); altrimenti la pagina
        errors/404.html.

        Restituisce: la risposta e, tranne per la SPA, il codice 404.
    """
    if _wants_json():
        return error("not_found"), 404
    # page: la SPA, se l'indirizzo è una sua pagina (regola unica, lotto 9d); altrimenti None
    page = spa_fallback()
    if page is not None:
        return page
    return render_template("errors/404.html"), 404


def _csrf_error(exc):
    """Codice CSRF mancante o scaduto: le rotte /api/ rispondono in JSON (la SPA lo
    mostra), le altre con il 400 di Flask-WTF di sempre (contratto 2.2).

    In parole semplici:
        _csrf_error(exc)
        exc è l'errore CSRFError di Flask-WTF. Restituirlo così com'è vuol dire
        "rispondi come avresti fatto tu" (la pagina 400 di Flask).
    """
    if request.path.startswith("/api/"):
        return error("invalid_data", "La pagina è scaduta: ricaricala e riprova."), 400
    return exc


def _server_error(_exc):
    """La risposta per un errore imprevisto (500).

    In parole semplici:
        _server_error(_exc)
        Sotto /api/ risponde server_error in JSON. Altrimenti annulla quello che il
        database stava facendo (rollback: la transazione rotta non deve restare
        aperta) e mostra errors/500.html; se anche questo va storto, scrive nel log
        e risponde con MINIMAL_500.
        try/except: si prova il blocco try; se lancia un'eccezione, invece di
        fermarsi si esegue il blocco except.
    """
    if _wants_json():
        return error("server_error"), 500
    try:
        db.session.rollback()
        return render_template("errors/500.html"), 500
    except Exception:
        log.exception("Non riesco a mostrare la pagina 500: rispondo con quella minima")
        return MINIMAL_500, 500


def _socket_error(exc):
    """Un errore imprevisto in un evento del tempo reale.

    In parole semplici:
        _socket_error(exc)
        Scrive nel log il nome dell'evento (per esempio "game:play_card") con
        l'errore. Se l'evento era il collegamento ("connect"), restituisce False:
        la connessione si rifiuta. Altrimenti la risposta server_error, che arriva
        solo alla scheda che aveva mandato l'evento.
    """
    # Nel log solo il nome dell'evento: i dati possono contenere testo degli utenti.
    # request.event: l'evento in corso, messo da Flask-SocketIO; "?" se manca il nome
    event = request.event.get("message", "?")
    log.error("Errore imprevisto nell'evento socket %s", event, exc_info=exc)
    if event == "connect":
        return False
    return error("server_error")
