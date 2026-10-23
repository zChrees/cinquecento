"""Rotte: pagine di accesso e registrazione (P16; dal passo 4 della migrazione).

Indirizzi decisi con P40: /auth/login e /auth/register. Il logout era qui
(POST /auth/logout, un modulo): dal lotto 9c della migrazione è POST /api/auth/logout,
in JSON, in api.py; il vecchio indirizzo risponde 404. Dal 19/10/2026 le
due pagine le disegna la SPA (frontend/src/pages/LoginPage.tsx e RegisterPage.tsx):
qui Flask manda la pagina della SPA, e i dati arrivano alle rotte JSON di api.py.
Gli indirizzi e i nomi delle rotte (auth.login, auth.register) restano quelli di
prima, così Flask-Login (login_view) e i link delle altre pagine non cambiano.
"""

from flask import redirect, url_for
from flask_login import current_user

from app.blueprints.auth import bp
from app.blueprints.spa.routes import spa_page
from app.extensions import login_manager
from app.services import auth_service

# Sostituisce il segnaposto di app/extensions.py: Flask-Login tiene l'ultimo registrato.
login_manager.user_loader(auth_service.load_user)


@bp.get("/login")
def login():
    """GET /auth/login: la pagina di accesso (SPA); chi ha già il login va alla home."""
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    return spa_page()


@bp.get("/register")
def register():
    """GET /auth/register: la pagina di registrazione (SPA); chi ha già il login va alla home."""
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    return spa_page()


def safe_next(target):
    """Dopo il login si torna alla pagina chiesta, ma solo se è di questo sito.

    In parole semplici:
        safe_next("/game/abc")          → "/game/abc"
        safe_next("//sito-esterno.it")  → "/" (la home): un indirizzo che comincia
        con // o /\\ porterebbe a un altro sito.
    """
    if target and target.startswith("/") and not target.startswith(("//", "/\\")):
        return target
    return url_for("main.index")
