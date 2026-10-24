"""Oggetti condivisi dalle parti dell'applicazione: database, login, CSRF, socket.

Si creano qui senza applicazione e si collegano in create_app() (app/__init__.py,
con init_app): così ogni file li importa da qui, sempre gli stessi, anche prima che
l'applicazione esista.

Cosa contiene:
    db              il database (Flask-SQLAlchemy), per esempio db.session.commit()
    login_manager   il login (Flask-Login): chi è collegato, current_user
    load_user(id)   il segnaposto per leggere l'utente collegato (vedi sotto)
    csrf            il controllo del codice CSRF su ogni POST (Flask-WTF)
    socketio        il tempo reale (Flask-SocketIO), un oggetto unico per il processo

DA DOVE ARRIVANO I DATI: niente dati; li importano create_app, i repository
(app/repositories/), i gestori degli eventi (app/sockets/) e le rotte.
"""

from flask_login import LoginManager
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

db = SQLAlchemy()

login_manager = LoginManager()
# La pagina di login (P16) si chiama "login" nel blueprint auth: Flask-Login ci
# manda chi apre una pagina che vuole il login.
login_manager.login_view = "auth.login"
login_manager.login_message = "Accedi per continuare."
login_manager.login_message_category = "info"


# @login_manager.user_loader è un "decoratore": registra la funzione qui sotto come
# quella che Flask-Login chiama, a ogni richiesta, per leggere l'utente collegato dal
# numero salvato nel cookie della sessione.
@login_manager.user_loader
def load_user(user_id):
    """Segnaposto del P4: nessuno risulta collegato.

    In parole semplici:
        load_user(user_id)
        Restituisce sempre None (nessun utente). Flask-Login tiene un solo
        user_loader, e quello vero lo registra app/blueprints/auth/routes.py
        (auth_service.load_user, P16), che sostituisce questo quando si importa.
        Oggi quindi questa funzione non la chiama nessuno: si potrebbe togliere
        (da proporre come punto a parte, regole-codice.md, sezione 8).
    """


csrf = CSRFProtect()

# Un solo processo con i thread, niente gevent o eventlet (DECISIONI.md).
socketio = SocketIO(async_mode="threading")
