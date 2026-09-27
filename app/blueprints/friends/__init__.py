"""Blueprint friends: richieste di amicizia e lista amici."""

from flask import Blueprint

bp = Blueprint("friends", __name__, url_prefix="/friends")

# Import in fondo: routes.py usa bp, definito qui sopra.
from app.blueprints.friends import routes  # noqa: F401
