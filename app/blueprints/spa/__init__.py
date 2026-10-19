"""Blueprint spa: le pagine del frontend React (docs/MIGRAZIONE-FRONTEND.md, sezione 6)."""

from flask import Blueprint

bp = Blueprint("spa", __name__)

# Import in fondo: routes.py usa bp, definito qui sopra.
from app.blueprints.spa import routes  # noqa: F401
