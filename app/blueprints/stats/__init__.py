"""Blueprint stats: dati del pannello statistiche, sotto /api/stats/ (lotto 9c)."""

from flask import Blueprint

bp = Blueprint("stats", __name__, url_prefix="/api/stats")

# Import in fondo: routes.py usa bp, definito qui sopra.
from app.blueprints.stats import routes  # noqa: F401
