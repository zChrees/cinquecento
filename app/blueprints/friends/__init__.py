"""Blueprint friends: richieste di amicizia e lista amici, sotto /api/friends/ (lotto 9c)."""

from flask import Blueprint

bp = Blueprint("friends", __name__, url_prefix="/api/friends")

# Import in fondo: routes.py usa bp, definito qui sopra.
from app.blueprints.friends import routes  # noqa: F401
