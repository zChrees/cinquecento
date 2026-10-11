"""Oggetti condivisi dalle parti dell'applicazione: database, login, CSRF, socket.

Si creano qui senza applicazione e si collegano in create_app() (app/__init__.py).
"""

from flask_login import LoginManager
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

db = SQLAlchemy()

login_manager = LoginManager()
# La pagina di login la crea P16 con il nome "login" nel blueprint auth.
login_manager.login_view = "auth.login"
login_manager.login_message = "Accedi per continuare."
login_manager.login_message_category = "info"


@login_manager.user_loader
def load_user(user_id):
    """Segnaposto: finché P16 non registra il suo user_loader, nessuno risulta collegato.

    Restituisce sempre None (nessun utente). Flask-Login tiene un solo
    user_loader: quello di P16 sostituisce questo.
    """


csrf = CSRFProtect()

# Un solo processo con i thread, niente gevent o eventlet (DECISIONI.md).
socketio = SocketIO(async_mode="threading")
