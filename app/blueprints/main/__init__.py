"""Blueprint main: la home (/) e il numero dei giocatori online (GET /api/online).

Un "blueprint" di Flask è un gruppo di rotte con un nome e un prefisso comune
all'indirizzo (la spiegazione completa è in app/blueprints/auth/__init__.py);
questo non ha prefisso.

Cosa contiene:
    bp   il blueprint, per esempio bp.get("/") e bp.get("/api/online") in routes.py

DA DOVE ARRIVANO I DATI: niente dati; routes.py ci attacca la rotta,
_register_blueprints di app/__init__.py lo registra nell'applicazione.
"""

from flask import Blueprint

bp = Blueprint("main", __name__)

# Import in fondo: routes.py usa bp, definito qui sopra (noqa: F401, import voluto).
from app.blueprints.main import routes  # noqa: F401
