"""P32: sicurezza di base delle richieste HTTP.

- Intestazioni di sicurezza (CSP, nosniff, X-Frame-Options, Referrer-Policy) su pagine,
  file statici, errori e risposte JSON.
- Le pagine non hanno script scritti dentro (la CSP li bloccherebbe): solo <script src>.
- Senza il codice CSRF si rifiutano i moduli (accesso, registrazione, Esci,
  cancellazione dell'account) e le richieste JSON che modificano qualcosa.
- Il cookie di sessione è HttpOnly e SameSite=Lax.
- Uno username con <script> si rifiuta.

Non servono utenti: i controlli CSRF e dei moduli rispondono prima del database.
"""

import re

import pytest

from app import SECURITY_HEADERS, create_app

CSRF_FIELD = re.compile(r'name="csrf_token" type="hidden" value="([^"]+)"')


@pytest.fixture(scope="module")
def client():
    app = create_app("testing")
    assert app.config.get("WTF_CSRF_ENABLED", True), "nei test il CSRF deve restare acceso"
    return app.test_client()


@pytest.mark.parametrize("path", [
    "/auth/login",                   # pagina
    "/static/css/base/variables.css",  # file statico
    "/pagina-che-non-esiste",        # errore 404
    "/friends/",                     # JSON senza login (401)
])
def test_intestazioni_di_sicurezza(client, path):
    response = client.get(path)
    for name, value in SECURITY_HEADERS.items():
        assert response.headers.get(name) == value, (path, name)


def test_csp_senza_eccezioni_pericolose():
    csp = SECURITY_HEADERS["Content-Security-Policy"]
    directives = dict(item.split(" ", 1) for item in csp.split("; "))
    assert directives["script-src"] == "'self'"
    assert directives["connect-src"] == "'self'"
    assert directives["frame-ancestors"] == "'none'"
    assert directives["object-src"] == "'none'"
    assert "unsafe-inline" not in csp and "unsafe-eval" not in csp
    # Le sole risorse esterne sono i font di Google (base.html)
    external = set(re.findall(r"https://[^\s;]+", csp))
    assert external == {"https://fonts.googleapis.com", "https://fonts.gstatic.com"}


@pytest.mark.parametrize("path", ["/", "/auth/login", "/auth/register"])
def test_nessuno_script_scritto_nella_pagina(client, path):
    page = client.get(path).get_data(as_text=True)
    scripts = re.findall(r"<script\b([^>]*)>", page)
    assert all("src=" in attributes for attributes in scripts), (path, scripts)
    assert not re.search(r"\son[a-z]+=", page), "gestori come onclick= non passano la CSP"


@pytest.mark.parametrize(("method", "path", "body"), [
    ("post", "/auth/login", {"username": "Mario", "password": "Password-di-prova-1"}),
    ("post", "/auth/register", {"username": "Mario", "email": "mario@esempio.it",
                                "password": "Password-di-prova-1", "confirm": "Password-di-prova-1"}),
    ("post", "/auth/logout", {}),
    ("post", "/profile/delete", {"password": "Password-di-prova-1"}),
    ("post", "/profile/avatar", {"avatar": "coppe"}),
])
def test_moduli_senza_csrf_rifiutati(client, method, path, body):
    response = getattr(client, method)(path, data=body)
    assert response.status_code == 400, path


@pytest.mark.parametrize(("method", "path", "body"), [
    ("post", "/friends/requests", {"request_id": "abc", "username": "Mario"}),
    ("post", "/friends/requests/1/accept", None),
    ("delete", "/friends/1", None),
    ("post", "/friends/blocks", {"request_id": "abc", "user_id": 1}),
])
def test_richieste_json_senza_csrf_rifiutate(client, method, path, body):
    response = getattr(client, method)(path, json=body)
    assert response.status_code == 400, path


def test_cookie_di_sessione_httponly_e_samesite(client):
    fresh = client.application.test_client()  # senza cookie: la risposta crea la sessione
    response = fresh.get("/auth/login")  # il codice CSRF finisce nella sessione
    cookies = response.headers.getlist("Set-Cookie")
    session = next(c for c in cookies if c.startswith("session="))
    assert "HttpOnly" in session
    assert "SameSite=Lax" in session


@pytest.mark.parametrize("username", ["<script>", "<b>Mario</b>", "Mario\"onmouseover=\"x"])
def test_username_con_html_rifiutato(client, username):
    page = client.get("/auth/register").get_data(as_text=True)
    response = client.post("/auth/register", data={
        "csrf_token": CSRF_FIELD.search(page)[1], "username": username, "email": "html@esempio.it",
        "password": "Password-di-prova-1", "confirm": "Password-di-prova-1",
    })
    assert response.status_code == 200  # il modulo torna con l'errore, nessun rimando alla home
    assert username not in response.get_data(as_text=True)  # se torna nel campo, torna con l'escape
