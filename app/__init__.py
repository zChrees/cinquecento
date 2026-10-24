"""create_app(): monta tutte le parti dell'applicazione.

Tutti i collegamenti tra le parti sono qui (P4): ogni parte riempie i propri
file e non tocca questo.
Questo file è anche il "pacchetto" app: `from app import create_app` legge da qui.

Cosa contiene:
    create_app("testing")      l'applicazione Flask pronta, con database, login, CSRF,
                               tempo reale, pagine di errore, blueprint e intestazioni
    CSP_DIRECTIVES             le regole della Content Security Policy, una per riga
    CONTENT_SECURITY_POLICY    le stesse regole in un testo solo, separate da "; "
    SECURITY_HEADERS           le intestazioni di sicurezza aggiunte a ogni risposta
    _security_headers(resp)    aggiunge SECURITY_HEADERS a una risposta
    _register_blueprints(app)  registra tutti i blueprint di app/blueprints/

DA DOVE ARRIVANO I DATI: create_app la chiamano run.py (il server vero) e i test
che creano un'applicazione (per esempio create_app("testing")); la configurazione
arriva da config.py e dal file .env.
"""

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from app.checks import check_python
from app.errors import register_error_handlers
from app.extensions import csrf, db, login_manager, socketio
from app.logging_config import configure_logging
from app.sockets import register_handlers
from config import load_config


def create_app(config_name=None):
    """Crea l'applicazione con la configurazione `config_name` (development, testing, production).

    In parole semplici:
        app = create_app()            con la configurazione di APP_ENV (o development)
        app = create_app("testing")   per i test: database cinquecento_test, porta 5099
        Prima controlla la versione di Python (si ferma con StartupCheckError se è
        sbagliata), poi collega all'applicazione gli oggetti di extensions.py e
        registra pagine di errore, blueprint, eventi del tempo reale e intestazioni
        di sicurezza. Con un proxy davanti (TRUSTED_PROXIES più di 0) mette ProxyFix.
        Attenzione (punto delicato P24): mai due create_app() nello stesso processo
        con il tempo reale acceso, perché socketio è un oggetto unico e si ricollega
        all'ultima applicazione creata.

        Restituisce: l'applicazione Flask.
    """
    config = load_config(config_name)
    check_python(config.REQUIRED_PYTHON)

    app = Flask(__name__)
    app.config.from_object(config)

    configure_logging(app)

    # init_app: gli oggetti creati in extensions.py senza applicazione si collegano a questa
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    socketio.init_app(app)

    # ProxyFix (O1): dietro un proxy (Caddy) chi si collega parla con il proxy, e il proxy
    # con Flask; il proxy scrive nelle intestazioni X-Forwarded-For, -Proto e -Host
    # l'indirizzo vero, se era https e il nome del sito, e ProxyFix li dà a Flask
    # (request.remote_addr, request.scheme). Si fida solo degli ultimi TRUSTED_PROXIES
    # passaggi: senza proxy (0) non si mette, altrimenti chiunque potrebbe scriverle.
    # Va messo dopo socketio.init_app, che "avvolge" anche lui wsgi_app: così ProxyFix
    # è il primo a ricevere ogni richiesta, anche quelle del tempo reale
    proxies = app.config["TRUSTED_PROXIES"]
    if proxies > 0:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=proxies, x_proto=proxies, x_host=proxies)

    register_error_handlers(app)
    _register_blueprints(app)
    register_handlers(socketio)
    # after_request: Flask chiama _security_headers su ogni risposta, prima di mandarla
    app.after_request(_security_headers)
    return app


# Intestazioni di sicurezza su ogni risposta (P32). La CSP dice al browser da dove può
# caricare le risorse: script e connessioni (anche il websocket) solo da questo sito,
# stili anche da Google Fonts, font da fonts.gstatic.com (le sole risorse esterne,
# caricate da frontend/index.html e, per le pagine di errore, da base.html), nessuna
# cornice. Nelle pagine non ci sono script né stili scritti dentro l'HTML; gli stili
# che React imposta con style={{ ... }} (cioè element.style) sono ammessi.
CSP_DIRECTIVES = (
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self' https://fonts.googleapis.com",
    "font-src 'self' https://fonts.gstatic.com",
    "img-src 'self' data:",
    "connect-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
)
CONTENT_SECURITY_POLICY = "; ".join(CSP_DIRECTIVES)
SECURITY_HEADERS = {
    "Content-Security-Policy": CONTENT_SECURITY_POLICY,
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "same-origin",
}


def _security_headers(response):
    """Aggiunge le intestazioni di sicurezza a una risposta.

    In parole semplici:
        _security_headers(response)
        La chiama Flask dopo ogni richiesta (app.after_request in create_app).
        setdefault aggiunge un'intestazione solo se la risposta non l'ha già: una
        rotta che ne mette una sua la tiene.

        Restituisce: la stessa risposta, con le intestazioni.
    """
    for name, value in SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    return response


def _register_blueprints(app):
    """Registra nell'applicazione tutti i blueprint di app/blueprints/.

    In parole semplici:
        _register_blueprints(app)
        Gli import stanno dentro la funzione: si leggono quando si crea
        l'applicazione, non appena si importa questo file. "import bp as auth_bp"
        dà un nome diverso a ogni bp (si chiamano tutti bp nei loro file).
    """
    from app.blueprints.auth import api_bp as auth_api_bp
    from app.blueprints.auth import bp as auth_bp
    from app.blueprints.friends import bp as friends_bp
    from app.blueprints.game import bp as game_bp
    from app.blueprints.main import bp as main_bp
    from app.blueprints.profile import api_bp as profile_api_bp
    from app.blueprints.profile import bp as profile_bp
    from app.blueprints.spa import bp as spa_bp
    from app.blueprints.stats import bp as stats_bp

    for bp in (main_bp, auth_bp, auth_api_bp, profile_bp, profile_api_bp, game_bp, stats_bp, friends_bp, spa_bp):
        app.register_blueprint(bp)
