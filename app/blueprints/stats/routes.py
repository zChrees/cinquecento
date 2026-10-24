"""Rotte: dati del pannello statistiche (P30; contratto 2.1).

GET /api/stats/me (prima del lotto 9c della migrazione /stats/me, ora 404)
risponde nella forma del contratto (1.2): {"ok": true, "data": ...};
senza login {"ok": false, "error": {"code": "not_logged_in", ...}} con 401, non il
rimando alla pagina di accesso (come le rotte degli amici, P45). Si vedono solo le
proprie statistiche: non c'è un indirizzo per quelle di un altro utente.
La logica sta in app/services/stats_service.py.

Cosa contiene:
    me()   GET /api/stats/me: le statistiche di chi ha fatto il login

DA DOVE ARRIVANO I DATI: la SPA chiede GET /api/stats/me quando si apre il pannello
statistiche (frontend/src/components/StatsSheet.tsx) e la home per il rating di
"In breve" nella carta-modal (frontend/src/pages/HomePage.tsx); chi è collegato lo dice Flask-Login
(current_user, dal cookie della sessione).
"""

from flask_login import current_user

from app.blueprints.stats import bp
from app.realtime.events import error, ok
from app.services import stats_service


# @bp.get("/me") è un "decoratore": dice a Flask che la funzione qui sotto risponde
# alle richieste GET a /me del blueprint (con il prefisso, /api/stats/me).
@bp.get("/me")
def me():
    """GET /api/stats/me: le statistiche di chi ha fatto il login.

    In parole semplici:
        me()
        Senza login risponde not_logged_in (401). Con il login risponde
        {"ok": true, "data": {...}} con i dati di stats_service.stats_of, per
        esempio {"games": 12, "wins": 7, "losses": 4, "draws": 1, "win_rate": 58,
        "ratings": {"1v1": {...}, "2v2": {...}}}.
    """
    if not current_user.is_authenticated:
        return error("not_logged_in"), 401
    return ok(stats_service.stats_of(current_user.id))
