"""Rotte: registrazione, login e logout (P16).

Indirizzi decisi con P40: /auth/login, /auth/register e /auth/logout, quest'ultimo
solo in POST con il codice CSRF (il modulo "Esci" della navbar). La logica sta in
app/services/auth_service.py.
"""

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user

from app.blueprints.auth import bp
from app.blueprints.auth.forms import LoginForm, RegisterForm
from app.extensions import login_manager
from app.realtime.presence import disconnect_user
from app.services import auth_service
from app.services.auth_service import AuthError

# Sostituisce il segnaposto di app/extensions.py: Flask-Login tiene l'ultimo registrato.
login_manager.user_loader(auth_service.load_user)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = LoginForm()
    if form.validate_on_submit():
        try:
            user = auth_service.authenticate(form.username.data, form.password.data)
        except AuthError as exc:
            flash(exc.message, "error")
        else:
            login_user(user)
            return redirect(_safe_next(request.args.get("next")))
    return render_template("auth/login.html", form=form)


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = RegisterForm()
    if form.validate_on_submit():
        try:
            user = auth_service.register(form.username.data, form.email.data, form.password.data)
        except AuthError as exc:
            getattr(form, exc.field).errors.append(exc.message)
        else:
            login_user(user)
            flash(f"Benvenuto, {user.username}!", "success")
            return redirect(url_for("main.index"))
    return render_template("auth/register.html", form=form)


@bp.post("/logout")
def logout():
    if current_user.is_authenticated:
        disconnect_user(current_user.id)  # P32: anche le altre schede smettono di agire come lui
    logout_user()
    return redirect(url_for("main.index"))


def _safe_next(target):
    """Dopo il login si torna alla pagina chiesta, ma solo se è di questo sito."""
    if target and target.startswith("/") and not target.startswith(("//", "/\\")):
        return target
    return url_for("main.index")
