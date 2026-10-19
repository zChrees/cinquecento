"""Registrazione e login nei test, con le rotte JSON della SPA (passo 4 della migrazione).

Fino al passo 4 i test leggevano il codice CSRF dentro le pagine Jinja /auth/login e
/auth/register e mandavano il modulo; ora quelle pagine le disegna React e i dati vanno
a /api/auth/ (app/blueprints/auth/api.py). Il codice CSRF si prende da
GET /api/auth/session e va nell'intestazione X-CSRFToken, come fa la SPA.

Due versioni di ogni funzione:
- client di prova di Flask (app.test_client()): register(client, ...), login(client, ...);
- sessione di `requests` verso un server vero (suite sockets, e2e, frontend2):
  register_http(session, url, ...), login_http(session, url, ...).
Restituiscono la risposta; chi vuole essere sicuro che sia andata bene usa ok().
"""

PASSWORD = "Password-di-prova-1"
WAIT = 10


def _email(username):
    return f"{username.lower()}@esempio.it"


def _token(client):
    return client.get("/api/auth/session").get_json()["data"]["csrf_token"]


def register(client, username, email=None, password=PASSWORD, confirm=None):
    """Registra `username` (e fa il login) con il client di prova di Flask."""
    body = {"username": username, "email": email or _email(username), "password": password,
            "confirm": password if confirm is None else confirm}
    return client.post("/api/auth/register", json=body, headers={"X-CSRFToken": _token(client)})


def login(client, username, password=PASSWORD, next_url=""):
    """Fa il login con il client di prova di Flask."""
    body = {"username": username, "password": password, "next": next_url}
    return client.post("/api/auth/login", json=body, headers={"X-CSRFToken": _token(client)})


def ok(response):
    """La risposta è "fatto" (200 e ok true); con il client di Flask o con requests."""
    data = response.get_json() if hasattr(response, "get_json") else response.json()
    return response.status_code == 200 and data.get("ok") is True


def messages(response):
    """Tutti i messaggi di errore della risposta (error.message e quelli dei campi), in un testo."""
    data = response.get_json() if hasattr(response, "get_json") else response.json()
    if data.get("ok"):
        return ""
    error = data["error"]
    texts = [error["message"]]
    for field_messages in error.get("fields", {}).values():
        texts.extend(field_messages)
    return "\n".join(texts)


def _http_token(session, url):
    return session.get(f"{url}/api/auth/session", timeout=WAIT).json()["data"]["csrf_token"]


def register_http(session, url, username, email=None, password=PASSWORD):
    """Registra `username` (e fa il login) su un server vero, con una sessione di requests."""
    body = {"username": username, "email": email or _email(username), "password": password, "confirm": password}
    return session.post(f"{url}/api/auth/register", json=body,
                        headers={"X-CSRFToken": _http_token(session, url)}, timeout=WAIT)


def login_http(session, url, username, password=PASSWORD):
    """Fa il login su un server vero, con una sessione di requests."""
    body = {"username": username, "password": password, "next": ""}
    return session.post(f"{url}/api/auth/login", json=body,
                        headers={"X-CSRFToken": _http_token(session, url)}, timeout=WAIT)
