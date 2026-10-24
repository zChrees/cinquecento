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
  Se nemmeno la pagina si può mostrare (per esempio il database non risponde e
  base.html cerca l'utente), si risponde con una pagina minima scritta qui.
- Eventi socket: un errore imprevisto in un gestore che non usa `handler`
  (app/realtime/events.py) va nel log, e la risposta server_error arriva solo a chi ha
  mandato l'evento; una connessione il cui controllo si è rotto si rifiuta.
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

MINIMAL_500 = (
    '<!doctype html><html lang="it"><head><meta charset="utf-8">'
    "<title>Errore del server · Cinquecento</title></head><body>"
    "<h1>Errore del server</h1><p>Qualcosa è andato storto. Riprova tra poco.</p>"
    '<p><a href="/">Torna alla home</a></p></body></html>'
)


def register_error_handlers(app):
    """Chiamata da create_app(): pagine 404 e 500 ed errori degli eventi socket."""
    app.register_error_handler(404, _not_found)
    app.register_error_handler(500, _server_error)
    app.register_error_handler(CSRFError, _csrf_error)
    socketio.on_error_default(_socket_error)


def _wants_json():
    return request.path.startswith(JSON_PREFIXES)


def _not_found(_exc):
    if _wants_json():
        return error("not_found"), 404
    # page: la SPA, se l'indirizzo è una sua pagina (regola unica, lotto 9d); altrimenti None
    page = spa_fallback()
    if page is not None:
        return page
    return render_template("errors/404.html"), 404


def _csrf_error(exc):
    """Codice CSRF mancante o scaduto: le rotte /api/ rispondono in JSON (la SPA lo
    mostra), le altre con il 400 di Flask-WTF di sempre (contratto 2.2)."""
    if request.path.startswith("/api/"):
        return error("invalid_data", "La pagina è scaduta: ricaricala e riprova."), 400
    return exc


def _server_error(_exc):
    if _wants_json():
        return error("server_error"), 500
    try:
        db.session.rollback()
        return render_template("errors/500.html"), 500
    except Exception:
        log.exception("Non riesco a mostrare la pagina 500: rispondo con quella minima")
        return MINIMAL_500, 500


def _socket_error(exc):
    # Nel log solo il nome dell'evento: i dati possono contenere testo degli utenti.
    event = request.event.get("message", "?")
    log.error("Errore imprevisto nell'evento socket %s", event, exc_info=exc)
    if event == "connect":
        return False
    return error("server_error")
