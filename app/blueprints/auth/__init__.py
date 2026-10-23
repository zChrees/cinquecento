"""Blueprint auth: registrazione, login e logout.

Due blueprint nello stesso pacchetto:
- bp (/auth/...): le pagine /auth/login e /auth/register (dal passo 4 della
  migrazione le disegna la SPA);
- api_bp (/api/auth/...): le rotte JSON che chiamano le pagine della SPA (api.py),
  dal lotto 9c anche il logout (POST /api/auth/logout).
"""

from flask import Blueprint

bp = Blueprint("auth", __name__, url_prefix="/auth")
api_bp = Blueprint("auth_api", __name__, url_prefix="/api/auth")

# Import in fondo: routes.py e api.py usano bp e api_bp, definiti qui sopra.
from app.blueprints.auth import api, routes  # noqa: F401
