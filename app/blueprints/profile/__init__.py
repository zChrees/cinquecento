"""Blueprint profile: impostazioni: avatar e cancellazione dell'account.

Un "blueprint" di Flask è un gruppo di rotte con un nome e un prefisso comune
all'indirizzo (la spiegazione completa è in app/blueprints/auth/__init__.py).
Due blueprint nello stesso pacchetto (come auth):
- bp (/profile/...): la pagina /profile/settings (la disegna la SPA);
- api_bp (/api/profile/...): le rotte JSON che quella pagina chiama (api.py).

Cosa contiene:
    bp       il blueprint della pagina, per esempio bp.get("/settings") in routes.py
    api_bp   il blueprint delle rotte JSON, per esempio api_bp.post("/avatar") in api.py

DA DOVE ARRIVANO I DATI: niente dati; routes.py e api.py ci attaccano le rotte,
_register_blueprints di app/__init__.py li registra nell'applicazione.
"""

from flask import Blueprint

bp = Blueprint("profile", __name__, url_prefix="/profile")
api_bp = Blueprint("profile_api", __name__, url_prefix="/api/profile")

# Import in fondo: routes.py e api.py usano bp e api_bp, definiti qui sopra
# (noqa: F401, import voluto).
from app.blueprints.profile import api, routes  # noqa: F401
