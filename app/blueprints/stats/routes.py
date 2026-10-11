"""Rotte: dati del pannello statistiche (P30; contratto 2.1).

GET /stats/me risponde nella forma del contratto (1.2): {"ok": true, "data": ...};
senza login {"ok": false, "error": {"code": "not_logged_in", ...}} con 401, non il
rimando alla pagina di accesso (come le rotte degli amici, P45). Si vedono solo le
proprie statistiche: non c'è un indirizzo per quelle di un altro utente.
La logica sta in app/services/stats_service.py.
"""

from flask_login import current_user

from app.blueprints.stats import bp
from app.realtime.events import error, ok
from app.services import stats_service


@bp.get("/me")
def me():
    if not current_user.is_authenticated:
        return error("not_logged_in"), 401
    return ok(stats_service.stats_of(current_user.id))
