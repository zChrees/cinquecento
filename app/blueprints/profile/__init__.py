"""Blueprint profile: impostazioni: avatar e cancellazione dell'account.

Due blueprint nello stesso pacchetto (come auth):
- bp (/profile/...): la pagina /profile/settings (dal passo 6 della migrazione la
  disegna la SPA);
- api_bp (/api/profile/...): le rotte JSON che quella pagina chiama (api.py).
"""

from flask import Blueprint

bp = Blueprint("profile", __name__, url_prefix="/profile")
api_bp = Blueprint("profile_api", __name__, url_prefix="/api/profile")

# Import in fondo: routes.py e api.py usano bp e api_bp, definiti qui sopra.
from app.blueprints.profile import api, routes  # noqa: F401
