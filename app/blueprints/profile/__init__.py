"""Blueprint profile: impostazioni: avatar e cancellazione dell'account."""

from flask import Blueprint

bp = Blueprint("profile", __name__, url_prefix="/profile")

# Import in fondo: routes.py usa bp, definito qui sopra.
from app.blueprints.profile import routes  # noqa: F401
