"""Blueprint auth: registrazione, login e logout.

Un "blueprint" di Flask è un gruppo di rotte con un nome e un prefisso comune
all'indirizzo: create_app() (app/__init__.py) lo registra, e da lì Flask conosce
tutte le sue rotte. Qui ce ne sono due nello stesso pacchetto:
- bp (/auth/...): le pagine /auth/login e /auth/register (le disegna la SPA);
- api_bp (/api/auth/...): le rotte JSON che chiamano le pagine della SPA (api.py),
  compreso il logout (POST /api/auth/logout).

Cosa contiene:
    bp       il blueprint delle pagine, per esempio bp.get("/login") in routes.py
    api_bp   il blueprint delle rotte JSON, per esempio api_bp.post("/login") in api.py

DA DOVE ARRIVANO I DATI: niente dati; routes.py e api.py ci attaccano le rotte,
_register_blueprints di app/__init__.py li registra nell'applicazione.
"""

from flask import Blueprint

# Blueprint(nome, modulo, url_prefix): il nome serve a url_for ("auth.login"),
# il prefisso si mette davanti a ogni rotta del blueprint
bp = Blueprint("auth", __name__, url_prefix="/auth")
api_bp = Blueprint("auth_api", __name__, url_prefix="/api/auth")

# Import in fondo: routes.py e api.py usano bp e api_bp, definiti qui sopra.
# Importarli basta a far "attaccare" le loro rotte; noqa: F401 dice a ruff che
# l'import non usato è voluto.
from app.blueprints.auth import api, routes  # noqa: F401
