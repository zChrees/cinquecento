"""Blueprint game: tavolo di gioco."""

from flask import Blueprint

bp = Blueprint("game", __name__, url_prefix="/game")

# Import in fondo: routes.py usa bp, definito qui sopra.
from app.blueprints.game import routes  # noqa: F401
