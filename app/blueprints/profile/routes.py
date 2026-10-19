"""Rotte: la pagina delle impostazioni (P17).

Indirizzo deciso con P40: /profile/settings (link "Impostazioni" del pannello
statistiche). Dal passo 6 della migrazione la pagina la disegna la SPA
(frontend/src/pages/SettingsPage.tsx); avatar e cancellazione dell'account passano
dalle rotte JSON di api.py. La logica sta in app/services/auth_service.py.
"""

from flask_login import login_required

from app.blueprints.profile import bp
from app.blueprints.spa.routes import spa_page


@bp.get("/settings")
@login_required
def settings():
    """GET /profile/settings: la pagina della SPA, solo con il login.

    In parole semplici:
        Senza login Flask-Login rimanda all'accesso (con ?next=), come prima;
        con il login risponde con la pagina della SPA, che disegna le impostazioni.
    """
    return spa_page()
