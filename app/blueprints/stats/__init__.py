"""Blueprint stats: dati del pannello statistiche, sotto /api/stats/ (lotto 9c).

Un "blueprint" di Flask è un gruppo di rotte con un nome e un prefisso comune
all'indirizzo (la spiegazione completa è in app/blueprints/auth/__init__.py).

Cosa contiene:
    bp   il blueprint, per esempio bp.get("/me") in routes.py diventa GET /api/stats/me

DA DOVE ARRIVANO I DATI: niente dati; routes.py ci attacca la rotta,
_register_blueprints di app/__init__.py lo registra nell'applicazione.
"""

from flask import Blueprint

bp = Blueprint("stats", __name__, url_prefix="/api/stats")

# Import in fondo: routes.py usa bp, definito qui sopra (noqa: F401, import voluto).
from app.blueprints.stats import routes  # noqa: F401
