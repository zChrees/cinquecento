"""Blueprint stats: dati del pannello statistiche."""

from flask import Blueprint

bp = Blueprint("stats", __name__, url_prefix="/stats")

# Import in fondo: routes.py usa bp, definito qui sopra.
from app.blueprints.stats import routes  # noqa: F401
