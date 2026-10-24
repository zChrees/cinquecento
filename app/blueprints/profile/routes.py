"""Rotte: la pagina delle impostazioni (P17).

Indirizzo deciso con P40: /profile/settings (link "Impostazioni" del pannello
statistiche). La pagina la disegna la SPA
(frontend/src/pages/SettingsPage.tsx); avatar e cancellazione dell'account passano
dalle rotte JSON di api.py. La logica sta in app/services/auth_service.py.

Cosa contiene:
    GET /profile/settings   settings: la pagina della SPA, solo con il login

DA DOVE ARRIVANO I DATI: il browser apre /profile/settings (il link "Impostazioni"
del pannello statistiche); chi è collegato lo dice Flask-Login (current_user).
"""

from flask_login import login_required

from app.blueprints.profile import bp
from app.blueprints.spa.routes import spa_page


# Due decoratori, letti dal basso: @login_required (di Flask-Login) controlla il login
# prima di chiamare la funzione; @bp.get dice a Flask a quale indirizzo risponde.
@bp.get("/settings")
@login_required
def settings():
    """GET /profile/settings: la pagina della SPA, solo con il login.

    In parole semplici:
        Senza login Flask-Login rimanda all'accesso (con ?next=);
        con il login risponde con la pagina della SPA, che disegna le impostazioni.
    """
    return spa_page()
