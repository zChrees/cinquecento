"""Blueprint auth: registrazione, login e logout."""

from flask import Blueprint

bp = Blueprint("auth", __name__, url_prefix="/auth")

# Import in fondo: routes.py usa bp, definito qui sopra.
from app.blueprints.auth import routes  # noqa: F401
