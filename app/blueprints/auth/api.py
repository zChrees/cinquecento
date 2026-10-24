"""Rotte JSON di accesso e registrazione per la SPA.

Le pagine /auth/login e /auth/register le disegna React (frontend/src/pages/);
qui ci sono le rotte che quelle pagine chiamano (e il logout del pannello
statistiche), sotto /api/ come tutte le rotte di dati. Rispondono nella forma
del contratto (1.2): {"ok": true, "data": ...} oppure {"ok": false, "error": {...}}.

Cosa contiene:
    GET  /api/auth/session    codice CSRF, utente collegato (o null) e messaggi da mostrare
    POST /api/auth/login      {"username", "password", "next"} → {"redirect"}
    POST /api/auth/register   {"username", "email", "password", "confirm"} → {"redirect"}
    POST /api/auth/logout     nessun corpo → {"redirect"} (la home)

Le regole stanno nei moduli (forms.py: LoginForm, RegisterForm, con \\Z di P137)
e nel servizio (auth_service: tentativi contati per account, P96). Errori:
    invalid_data (400)  un campo non valido; error.fields dice quale, con i messaggi
                        da mostrare sotto ogni campo
    not_allowed (403)   credenziali sbagliate o troppi tentativi (il messaggio lo dice)

Il codice CSRF lo controlla CSRFProtect (app/extensions.py) per ogni POST,
leggendolo dall'intestazione X-CSRFToken; senza, risponde app/errors.py con
invalid_data. Per questo i moduli qui non hanno il campo csrf_token.

DA DOVE ARRIVANO I DATI: dalla SPA (frontend/src/api/client.ts), che li manda in JSON.
"""

from flask import flash, get_flashed_messages, request, url_for
from flask_login import current_user, login_user, logout_user
from flask_wtf.csrf import generate_csrf
from werkzeug.datastructures import MultiDict

from app.blueprints.auth import api_bp
from app.blueprints.auth.forms import LoginForm, RegisterForm
from app.blueprints.auth.routes import safe_next
from app.realtime.events import error, ok
from app.realtime.presence import disconnect_user
from app.services import auth_service
from app.services.auth_service import AuthError

# NO_STORE: la risposta non si salva nella cache del browser (contiene il codice CSRF)
NO_STORE = {"Cache-Control": "no-store"}

# FLASH_KINDS: le categorie dei messaggi, come partials/flash.html: tutto il resto è "info"
FLASH_KINDS = ("success", "error")


def _body(names):
    """Legge il corpo JSON e controlla che i campi `names` siano testi.

    In parole semplici:
        _body(("username", "password"))
        Restituisce i campi in una MultiDict (la forma che leggono i moduli di
        WTForms), oppure None se il corpo non è un oggetto JSON o un campo non è
        un testo: un numero al posto di uno username si rifiuta, non si corregge.
        Un campo che manca vale "" e lo rifiuta il modulo con il suo messaggio.

        Restituisce: MultiDict oppure None.
    """
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None
    clean = {}
    for name in names:
        value = data.get(name, "")
        if not isinstance(value, str):
            return None
        clean[name] = value
    return MultiDict(clean)


def _field_errors(form):
    """La risposta invalid_data con gli errori di ogni campo del modulo.

    In parole semplici:
        _field_errors(form)
        Per esempio {"username": ["Lo username deve avere da 3 a 20 caratteri."]}
        dentro error.fields; error.message è il primo errore, da mostrare se la
        pagina non sa a quale campo riferirlo.
    """
    # fields: nome del campo → elenco dei suoi messaggi, solo per i campi con errori;
    # first: il primo messaggio del primo campo (i campi sono nell'ordine del modulo)
    fields = {}
    first = None
    for name, messages in form.errors.items():
        if not messages:
            continue
        fields[name] = list(messages)
        if first is None:
            first = messages[0]
    return error("invalid_data", first, fields=fields), 400


def _bad_body():
    """La risposta invalid_data per un corpo che non va.

    In parole semplici:
        _bad_body()  →  ({"ok": False, "error": {"code": "invalid_data", ...}}, 400)
        La usano login e register quando _body restituisce None (corpo che non è un
        oggetto JSON, o un campo che non è un testo).
    """
    return error("invalid_data", "Dati non validi."), 400


@api_bp.get("/session")
def session():
    """GET /api/auth/session: quello che la SPA deve sapere appena si apre.

    In parole semplici:
        Il codice CSRF da mandare con ogni POST (al posto del <meta name="csrf-token">
        di base.html), l'utente collegato (null senza login) e i messaggi lasciati da
        un'altra pagina con flash() (per esempio "Account cancellato." prima di
        tornare all'accesso): li legge e li toglie, come faceva partials/flash.html.
    """
    user = None
    if current_user.is_authenticated:
        user = {"user_id": current_user.id, "username": current_user.username, "avatar": current_user.avatar}
    flashes = []
    # get_flashed_messages(with_categories=True): coppie (categoria, messaggio),
    # per esempio ("success", "Account cancellato.")
    for flashed in get_flashed_messages(with_categories=True):
        category = flashed[0]
        message = flashed[1]
        kind = "info"
        if category in FLASH_KINDS:
            kind = category
        flashes.append({"kind": kind, "message": message})
    return ok({"csrf_token": generate_csrf(), "user": user, "flashes": flashes}), 200, NO_STORE


@api_bp.post("/login")
def login():
    """POST /api/auth/login: entra con nome utente (o email) e password.

    In parole semplici:
        Se va bene fa il login e risponde con l'indirizzo dove andare: la pagina
        chiesta prima (next), ma solo se è di questo sito (safe_next), altrimenti
        la home. Chi ha già fatto il login va alla home.
    """
    if current_user.is_authenticated:
        return ok({"redirect": url_for("main.index")})
    data = _body(("username", "password", "next"))
    if data is None:
        return _bad_body()
    # meta csrf False: il codice l'ha già controllato CSRFProtect sull'intestazione
    form = LoginForm(formdata=data, meta={"csrf": False})
    if not form.validate():
        return _field_errors(form)
    try:
        user = auth_service.authenticate(form.username.data, form.password.data)
    except AuthError as exc:
        return error("not_allowed", exc.message), 403
    login_user(user)
    return ok({"redirect": safe_next(data["next"])})


@api_bp.post("/register")
def register():
    """POST /api/auth/register: crea l'account ed entra.

    In parole semplici:
        Le regole sono quelle di RegisterForm (username, email, password, conferma);
        username o email già usati li rifiuta il database (P16) e l'errore va
        sotto il campo giusto. Se va bene fa il login, lascia "Benvenuto, Mario!"
        per la home (flash) e risponde con l'indirizzo della home.
    """
    if current_user.is_authenticated:
        return ok({"redirect": url_for("main.index")})
    data = _body(("username", "email", "password", "confirm"))
    if data is None:
        return _bad_body()
    form = RegisterForm(formdata=data, meta={"csrf": False})
    if not form.validate():
        return _field_errors(form)
    try:
        user = auth_service.register(form.username.data, form.email.data, form.password.data)
    except AuthError as exc:
        return error("invalid_data", exc.message, fields={exc.field: [exc.message]}), 400
    login_user(user)
    flash(f"Benvenuto, {user.username}!", "success")
    return ok({"redirect": url_for("main.index")})


@api_bp.post("/logout")
def logout():
    """POST /api/auth/logout: esce (il pulsante "Esci" del pannello statistiche).

    In parole semplici:
        Prima scollega le schede dell'utente dal tempo reale (P32: anche le altre
        schede smettono di agire come lui; va fatto mentre ha ancora il login),
        poi toglie il login e risponde con l'indirizzo della home, che la pagina
        ricarica. Chi non ha il login riceve la stessa risposta: uscire due volte
        non è un errore. Il codice CSRF lo controlla CSRFProtect, come per le altre POST.
    """
    if current_user.is_authenticated:
        disconnect_user(current_user.id)
    logout_user()
    return ok({"redirect": url_for("main.index")})
