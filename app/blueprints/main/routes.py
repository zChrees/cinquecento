"""Rotte della home (la pagina vera la fa P22: per ora c'è la pagina "ok" di P4)."""

from flask import render_template

from app.blueprints.main import bp


@bp.get("/")
def index():
    return render_template("main/index.html")
