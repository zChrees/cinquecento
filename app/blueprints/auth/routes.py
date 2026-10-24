"""Rotte: pagine di accesso e registrazione (P16).

Indirizzi decisi con P40: /auth/login e /auth/register. Le due pagine le disegna
la SPA (frontend/src/pages/LoginPage.tsx e RegisterPage.tsx): qui Flask manda la
pagina della SPA, e i dati arrivano alle rotte JSON di api.py (anche il logout,
POST /api/auth/logout). I nomi delle rotte (auth.login, auth.register) li usano
Flask-Login (login_view) e url_for.

Cosa contiene:
    GET /auth/login            login: la pagina di accesso (SPA)
    GET /auth/register         register: la pagina di registrazione (SPA)
    safe_next("/game/abc")     l'indirizzo dove tornare dopo il login, solo se è di questo sito
    e registra lo user_loader di Flask-Login (auth_service.load_user, P16)

DA DOVE ARRIVANO I DATI: il browser apre /auth/login (anche da Flask-Login, con
?next=, quando una pagina vuole il login); safe_next la usa login di api.py con il
next mandato dalla SPA.
"""

from flask import redirect, url_for
from flask_login import current_user

from app.blueprints.auth import bp
from app.blueprints.spa.routes import spa_page
from app.extensions import login_manager
from app.services import auth_service

# user_loader: la funzione che Flask-Login chiama a ogni richiesta per leggere l'utente
# collegato dal numero salvato nel cookie della sessione
login_manager.user_loader(auth_service.load_user)


# @bp.get("/login") è un "decoratore": dice a Flask che la funzione qui sotto risponde
# alle richieste GET a /login del blueprint (con il prefisso, /auth/login).
@bp.get("/login")
def login():
    """GET /auth/login: la pagina di accesso (SPA); chi ha già il login va alla home.

    In parole semplici:
        login()
        Con il login rimanda alla home (redirect, 302); senza, risponde con la
        pagina della SPA (spa_page), e React disegna il modulo.
    """
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    return spa_page()


@bp.get("/register")
def register():
    """GET /auth/register: la pagina di registrazione (SPA); chi ha già il login va alla home.

    In parole semplici:
        register()
        Come login, per la pagina di registrazione.
    """
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
