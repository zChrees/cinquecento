"""create_app(): monta tutte le parti dell'applicazione.

Tutti i collegamenti sono già qui (P4): i punti successivi riempiono i propri
file e non toccano questo (SCALETTA.md, sezione 3).
"""

from flask import Flask

from app.checks import check_python
from app.errors import register_error_handlers
from app.extensions import csrf, db, login_manager, socketio
from app.logging_config import configure_logging
from app.sockets import register_handlers
from config import load_config


def create_app(config_name=None):
    """Crea l'applicazione con la configurazione `config_name` (development, testing, demo)."""
    config = load_config(config_name)
    check_python(config.REQUIRED_PYTHON)

    app = Flask(__name__)
    app.config.from_object(config)

    configure_logging(app)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    socketio.init_app(app)

    register_error_handlers(app)
    _register_blueprints(app)
    register_handlers(socketio)
    app.after_request(_security_headers)
    return app


# Intestazioni di sicurezza su ogni risposta (P32). La CSP dice al browser da dove può
# caricare le risorse: script e connessioni (anche il websocket) solo da questo sito,
# stili anche da Google Fonts, font da fonts.gstatic.com (le sole risorse esterne,
# caricate da base.html), nessuna cornice. Nei template non ci sono script né stili
# scritti dentro la pagina; gli stili che il JS imposta con element.style sono ammessi.
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
    for name, value in SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    return response


def _register_blueprints(app):
    from app.blueprints.auth import bp as auth_bp
    from app.blueprints.friends import bp as friends_bp
    from app.blueprints.game import bp as game_bp
    from app.blueprints.main import bp as main_bp
    from app.blueprints.profile import bp as profile_bp
    from app.blueprints.stats import bp as stats_bp

    for bp in (main_bp, auth_bp, profile_bp, game_bp, stats_bp, friends_bp):
        app.register_blueprint(bp)
