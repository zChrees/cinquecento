"""Pagine e risposte di errore (P7).

- 404 e 500: pagina in italiano basata su base.html, senza navbar (le pagine di errore
  non hanno uno script di pagina, e senza la navbar non si apre). Le richieste JSON
  (/stats/..., /friends/...) ricevono invece la risposta del contratto (1.2):
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

from app.extensions import db, socketio
from app.realtime.events import error

log = logging.getLogger(__name__)

# Indirizzi delle richieste HTTP in JSON (contratto, sezione 2)
JSON_PREFIXES = ("/stats/", "/friends/")

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
    socketio.on_error_default(_socket_error)


def _wants_json():
    return request.path.startswith(JSON_PREFIXES)


def _not_found(_exc):
    if _wants_json():
        return error("not_found"), 404
    return render_template("errors/404.html"), 404


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
