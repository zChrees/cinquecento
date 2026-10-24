"""Rotte JSON delle impostazioni per la SPA.

La pagina /profile/settings la disegna React (frontend/src/pages/SettingsPage.tsx);
qui ci sono le rotte che chiama, sotto /api/ come tutte le rotte di dati.
Rispondono nella forma del contratto (1.2).

Cosa contiene:
    GET  /api/profile/avatars   gli avatar che si possono scegliere: [{"code", "name"}]
    POST /api/profile/avatar    {"avatar"} ("" = l'iniziale) → {"redirect"}
    POST /api/profile/delete    {"password"} → {"redirect"} (e l'utente esce)

Tutte vogliono il login: senza, not_logged_in (401), non il rimando alla pagina di
accesso. Le regole stanno nel servizio (auth_service: set_avatar, delete_account
con i tentativi contati come al login, P17 e P96, e la chiusura delle schede prima
di cancellare, P32). Errori:
    invalid_data (400)  avatar fuori elenco, password mancante o sbagliata
                        (error.fields dice quale campo)
    not_allowed (403)   troppi tentativi, oppure una partita in corso

Dopo "Salva l'avatar" e dopo la cancellazione la pagina si ricarica con
un messaggio (flash), letto poi da GET /api/auth/session o dalla home.

DA DOVE ARRIVANO I DATI: dalla SPA (frontend/src/api/profile.ts), in JSON; il codice
CSRF lo controlla CSRFProtect sull'intestazione X-CSRFToken (come /api/auth/).
"""

import functools

from flask import flash, request, url_for
from flask_login import current_user, logout_user

from app.blueprints.profile import api_bp
from app.realtime.events import error, ok
from app.services import auth_service
from app.services.auth_service import AuthError
from app.services.avatars import AVATARS

ACCOUNT_DELETED = 'Account cancellato. Le partite giocate restano, con "utente eliminato" al posto del nome.'
AVATAR_SAVED = "Avatar salvato."


def login_needed(fn):
    """Decoratore: la rotta vuole il login; senza, not_logged_in (401).

    In parole semplici:
        @login_needed sopra una rotta vuol dire "prima di chiamarla controlla il
        login". login_required di Flask-Login rimanderebbe alla pagina di accesso
        (302), che a una pagina che aspetta JSON non serve: qui risponde
        nella forma del contratto, come json_endpoint di friends/routes.py.
    """

    # @functools.wraps(fn): wrapper prende il nome di fn, che Flask usa per
    # distinguere le rotte
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        """La funzione che Flask chiama al posto della rotta.

        In parole semplici:
            wrapper(*args, **kwargs)
            *args, **kwargs: i parametri che Flask passa alla rotta, qualunque siano,
            passati così come sono a fn. Senza login risponde not_logged_in (401) e
            la rotta non parte.
        """
        if not current_user.is_authenticated:
            return error("not_logged_in"), 401
        return fn(*args, **kwargs)

    return wrapper


def _json_field(name):
    """Il campo `name` del corpo JSON, oppure None se manca (o il corpo non è un oggetto).

    In parole semplici:
        _json_field("avatar")
        Il valore si passa così com'è al servizio, che rifiuta tutto quello che non è
        un testo valido con il suo messaggio (nessuna correzione silenziosa).
    """
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None
    return data.get(name)


@api_bp.get("/avatars")
@login_needed
def avatars():
    """GET /api/profile/avatars: gli avatar del set, nell'ordine di avatars.py (D29).

    In parole semplici:
        {"avatars": [{"code": "coppe", "name": "Coppe"}, ...]}
        Un solo elenco (avatars.py): la pagina non ne tiene una copia. "Nessun
        avatar" (l'iniziale) non è nell'elenco: lo aggiunge la pagina.
    """
    choices = []
    for code, name in AVATARS.items():
        choices.append({"code": code, "name": name})
    return ok({"avatars": choices})


@api_bp.post("/avatar")
@login_needed
def avatar():
    """POST /api/profile/avatar: salva l'avatar scelto ("" = l'iniziale).

    In parole semplici:
        Se va bene lascia "Avatar salvato." per la pagina (flash) e risponde con
        l'indirizzo delle impostazioni, che la pagina ricarica.
        Un codice fuori elenco, o un valore che non è un testo, si rifiuta.
    """
    try:
        auth_service.set_avatar(current_user._get_current_object(), _json_field("avatar"))
    except AuthError as exc:
        return error("invalid_data", exc.message, fields={"avatar": [exc.message]}), 400
    flash(AVATAR_SAVED, "success")
    return ok({"redirect": url_for("profile.settings")})


@api_bp.post("/delete")
@login_needed
def delete():
    """POST /api/profile/delete: cancella l'account dopo aver controllato la password.

    In parole semplici:
        Se va bene l'utente esce, resta il messaggio "Account cancellato..." per la
        home e la risposta dice di andare lì. Password mancante o sbagliata:
        invalid_data sul campo password; troppi tentativi o una partita in corso:
        not_allowed. La password non va mai nel log.
    """
    try:
        auth_service.delete_account(current_user._get_current_object(), _json_field("password"))
    except AuthError as exc:
        if exc.field == "password":
            return error("invalid_data", exc.message, fields={"password": [exc.message]}), 400
        return error("not_allowed", exc.message), 403
    logout_user()
    flash(ACCOUNT_DELETED, "success")
    return ok({"redirect": url_for("main.index")})
