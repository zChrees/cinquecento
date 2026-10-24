"""Blueprint spa: le pagine del frontend React (docs/MIGRAZIONE-FRONTEND.md, sezione 6).

Un "blueprint" di Flask è un gruppo di rotte con un nome e un prefisso comune
all'indirizzo (la spiegazione completa è in app/blueprints/auth/__init__.py);
questo non ha prefisso.

Cosa contiene:
    bp   il blueprint, a cui routes.py attacca le rotte dei file della SPA

DA DOVE ARRIVANO I DATI: niente dati; routes.py ci attacca le rotte,
_register_blueprints di app/__init__.py lo registra nell'applicazione.
"""

from flask import Blueprint

bp = Blueprint("spa", __name__)

# Import in fondo: routes.py usa bp, definito qui sopra (noqa: F401, import voluto).
from app.blueprints.spa import routes  # noqa: F401
