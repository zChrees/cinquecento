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
    return app


def _register_blueprints(app):
    from app.blueprints.auth import bp as auth_bp
    from app.blueprints.friends import bp as friends_bp
    from app.blueprints.game import bp as game_bp
    from app.blueprints.main import bp as main_bp
    from app.blueprints.profile import bp as profile_bp
    from app.blueprints.stats import bp as stats_bp

    for bp in (main_bp, auth_bp, profile_bp, game_bp, stats_bp, friends_bp):
        app.register_blueprint(bp)
