"""Blueprint main: home."""

from flask import Blueprint

bp = Blueprint("main", __name__)

# Import in fondo: routes.py usa bp, definito qui sopra.
from app.blueprints.main import routes  # noqa: F401
