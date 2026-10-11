"""Rotte: impostazioni: avatar e cancellazione dell'account (P17).

Indirizzo della pagina deciso con P40: /profile/settings (link "Impostazioni" del
pannello statistiche). I due moduli mandano il codice CSRF (Flask-WTF lo controlla
per ogni POST). La logica sta in app/services/auth_service.py.
"""

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, logout_user

from app.blueprints.profile import bp
from app.services import auth_service
from app.services.auth_service import AuthError
from app.services.avatars import AVATARS

ACCOUNT_DELETED = 'Account cancellato. Le partite giocate restano, con "utente eliminato" al posto del nome.'


@bp.get("/settings")
@login_required
def settings():
    return render_template("profile/settings.html", avatars=AVATARS)


@bp.post("/avatar")
@login_required
def avatar():
    try:
        auth_service.set_avatar(current_user._get_current_object(), request.form.get("avatar"))
    except AuthError as exc:
        flash(exc.message, "error")
    else:
        flash("Avatar salvato.", "success")
    return redirect(url_for("profile.settings"))


@bp.post("/delete")
@login_required
def delete():
    try:
        auth_service.delete_account(current_user._get_current_object(), request.form.get("password"))
    except AuthError as exc:
        flash(exc.message, "error")
        return redirect(url_for("profile.settings"))
    logout_user()
    flash(ACCOUNT_DELETED, "success")
    return redirect(url_for("main.index"))
