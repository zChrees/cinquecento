"""Oggetti condivisi dalle parti dell'applicazione: database, login, CSRF, socket.

Si creano qui senza applicazione e si collegano in create_app() (app/__init__.py,
con init_app): così ogni file li importa da qui, sempre gli stessi, anche prima che
l'applicazione esista.

Cosa contiene:
    db              il database (Flask-SQLAlchemy), per esempio db.session.commit()
    login_manager   il login (Flask-Login): chi è collegato, current_user;
                    chi legge l'utente dal cookie (user_loader) lo registra
                    app/blueprints/auth/routes.py (auth_service.load_user, P16)
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

csrf = CSRFProtect()

# Un solo processo con i thread, niente gevent o eventlet (DECISIONI.md).
socketio = SocketIO(async_mode="threading")
