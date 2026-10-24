"""Avvio del server: python run.py (configurazione dal file .env).

Crea l'applicazione, controlla che MySQL risponda con la versione giusta e avvia il
server con il tempo reale (Flask-SocketIO), all'indirizzo e alla porta del .env (di
solito http://127.0.0.1:5000).

Cosa contiene:
    main()   crea l'applicazione, fa i controlli e avvia il server

DA DOVE ARRIVANO I DATI: la configurazione da config.py e dal file .env (APP_ENV,
HOST, PORT, il database, ...).
"""

import sys

from app import create_app
from app.checks import StartupCheckError, check_mysql
from app.extensions import socketio
from config import ConfigError


def main():
    """Crea l'applicazione, controlla MySQL e avvia il server.

    In parole semplici:
        main()
        Se la configurazione è sbagliata (ConfigError) o un controllo non passa
        (StartupCheckError: versione di Python o di MySQL, MySQL spento), stampa il
        messaggio ed esce con il codice 1. Altrimenti avvia il server, che resta
        acceso finché non si chiude il terminale (o Ctrl+C).
        try/except: si prova il blocco try; con uno dei due errori elencati, invece
        di fermarsi con un messaggio tecnico, si esegue il blocco except.
    """
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


# __name__ vale "__main__" solo quando il file si lancia con python run.py, non quando
# un altro file lo importa: così importarlo non avvia il server.
if __name__ == "__main__":
    main()
