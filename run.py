"""Avvio del server: python run.py (configurazione dal file .env)."""

import sys

from app import create_app
from app.checks import StartupCheckError, check_mysql
from app.extensions import socketio
from config import ConfigError


def main():
    try:
        app = create_app()
        check_mysql(app.config["SQLALCHEMY_DATABASE_URI"], app.config["REQUIRED_MYSQL"])
    except (ConfigError, StartupCheckError) as exc:
        print(f"Avvio annullato: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Cinquecento ({app.config['ENV_NAME']}): http://{app.config['HOST']}:{app.config['PORT']}")
    socketio.run(
        app,
        host=app.config["HOST"],
        port=app.config["PORT"],
        debug=app.config["DEBUG"],
        # Niente riavvio automatico: resterebbero due processi (DECISIONI.md, un solo processo).
        use_reloader=False,
        allow_unsafe_werkzeug=app.config["ALLOW_UNSAFE_WERKZEUG"],
    )


if __name__ == "__main__":
    main()
