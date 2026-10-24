"""Il frontend React (la SPA) servito da Flask.

Controlla:
- regola unica: Flask manda la SPA per ogni GET a un indirizzo senza rotta
  fuori da /api/, /static/ e /socket.io; un indirizzo con la / in fondo si rimanda a
  quello senza; i prefissi che restano a Flask sono gli stessi in Flask (NOT_SPA) e
  in Vite (FLASK_PATHS); in React ogni pagina distingue le maiuscole e c'è la pagina
  "non trovata", che nel browser ha la navbar e riporta alla home;
- Flask manda index.html del build, da richiedere ogni volta (no-cache), con la CSP;
  senza build risponde 503 con un messaggio chiaro; la pagina di prova /prova-react
  non deve tornare;
- con Node e frontend/node_modules: TypeScript non trova errori, il build vero
  (in una cartella temporanea, fuori dal progetto) non ha script né stili scritti
  dentro la pagina, e nel browser React disegna la pagina di accesso e la CSP non
  blocca niente. Senza Node o senza `npm ci` questi si saltano;
- tempo reale (frontend/src/socket/): senza login la pagina non si collega; con il
  login (le impostazioni) si collega. home:status lo controlla test_home.py, la coda
  test_home_coda.py;
- la cornice con il login: la navbar ha nome e avatar, il pannello
  statistiche si apre con i numeri e si chiude, "Esci" porta il codice CSRF; scollegati
  dal server compare l'avviso "Sei stato scollegato" con "Ricarica".
"""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from app import create_app
from app.blueprints.spa import routes
from app.realtime.presence import disconnect_user
from tests.browser import TEST_COOKIE, Browser, FakeUser, find_browser, running_server

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"
VITE_CONFIG = FRONTEND / "vite.config.ts"
ROUTES_TSX = FRONTEND / "src" / "routes.tsx"
NODE_MODULES = FRONTEND / "node_modules"
STATS_EXAMPLE = {k: v for k, v in json.loads(
    (ROOT / "app" / "static" / "dev" / "statistiche_esempio.json").read_text(encoding="utf-8")).items() if k != "_nota"}
# Come test_csp.py: registra ogni risorsa bloccata dalla CSP
RECORD = (
    "window.__csp = [];"
    "document.addEventListener('securitypolicyviolation',"
    " e => window.__csp.push(e.effectiveDirective + ' ' + e.blockedURI));"
)


@pytest.fixture
def app():
    return create_app("testing")


@pytest.fixture
def fake_dist(monkeypatch, tmp_path):
    monkeypatch.setattr(routes, "dist_dir", lambda: tmp_path)
    return tmp_path


# --- Indirizzi (regola unica) -------------------------------------------------

# INDEX: un index.html finto, riconoscibile dal suo <div id="root">
INDEX = '<!doctype html><div id="root"></div>'


def test_stessi_prefissi_in_flask_e_in_vite():
    # In sviluppo Vite gira a Flask solo quello che non è mai una pagina della SPA
    code = VITE_CONFIG.read_text(encoding="utf-8")
    found = re.search(r"const FLASK_PATHS: string\[\] = \[(.*?)\];", code, flags=re.DOTALL)
    assert found, "FLASK_PATHS non trovato in vite.config.ts"
    paths = re.findall(r"'([^']+)'", found.group(1))
    assert [path.strip("/") for path in paths] == list(routes.NOT_SPA)
    # Nessun elenco delle pagine: SPA_PATHS, GAME_TABLE e flaskPattern non devono tornare
    for name in ("SPA_PATHS", "GAME_TABLE", "flaskPattern"):
        assert name not in code, name
    assert not hasattr(routes, "SPA_PATHS")


def test_in_react_maiuscole_e_pagina_non_trovata():
    # Ogni pagina di routes.tsx ha caseSensitive (come le rotte di Flask: senza,
    # /Profile/Settings aprirebbe le impostazioni senza il controllo del login), e
    # l'ultima voce è '*', la pagina "non trovata"
    code = ROUTES_TSX.read_text(encoding="utf-8")
    entries = re.findall(r"^  \{ path: '([^']+)', element: <(\w+) />(, caseSensitive: true)? \},\r?$",
                         code, flags=re.MULTILINE)
    assert [path for path, _page, _case in entries] == [
        "/", "/auth/login", "/auth/register", "/profile/settings", "/game/:gameId", "*"]
    for path, _page, case in entries[:-1]:
        assert case, path
    assert entries[-1][1] == "NotFoundPage"


@pytest.mark.parametrize("url", [
    "/pagina-a-caso", "/game/prova/altro", "/Profile/Settings", "/AUTH/LOGIN",
    "/online", "/stats/me", "/friends/requests/1/accept", "/prova-react",
    "/apice", "/staticx", "/socket.iox",
])
def test_regola_unica_manda_la_spa(app, fake_dist, url):
    (fake_dist / "index.html").write_text(INDEX, encoding="utf-8")
    client = app.test_client()
    response = client.get(url)
    assert response.status_code == 200, url
    assert '<div id="root">' in response.get_data(as_text=True), url
    assert "no-cache" in response.headers["Cache-Control"]
    assert "script-src 'self'" in response.headers["Content-Security-Policy"]
    response.close()
    head = client.head(url)
    assert head.status_code == 200, url
    head.close()


@pytest.mark.parametrize(("method", "url", "status", "kind"), [
    # /api/: 404 in JSON (contratto 1.2); /api senza / è la pagina di errore
    ("get", "/api/non-esiste", 404, "json"),
    ("get", "/api", 404, "html"),
    # file statici che mancano: la pagina di errore (base.html)
    ("get", "/static/non-esiste.css", 404, "html"),
    ("get", "/static", 404, "html"),
    # un 404 deciso da una rotta resta 404 (?demo= sbagliato sulla home)
    ("get", "/?demo=altro", 404, "html"),
    # solo GET: un POST o un DELETE a un indirizzo che non esiste resta 404
    ("post", "/pagina-a-caso", 404, "html"),
    ("delete", "/pagina-a-caso", 404, "html"),
    # metodo sbagliato su una rotta che esiste: 405
    ("post", "/auth/login", 405, None),
    ("get", "/api/auth/logout", 405, None),
])
def test_regola_unica_non_tocca_il_resto(app, fake_dist, method, url, status, kind):
    (fake_dist / "index.html").write_text(INDEX, encoding="utf-8")
    response = getattr(app.test_client(), method)(url)
    assert response.status_code == status, url
    body = response.get_data(as_text=True)
    assert '<div id="root">' not in body, url
    if kind == "json":
        assert response.get_json()["error"]["code"] == "not_found"
    if kind == "html":
        assert 'data-error="404"' in body, url
    response.close()


@pytest.mark.parametrize(("path", "query", "target"), [
    ("/profile/settings/", "", "/profile/settings"),
    ("/game/prova/", "demo=1v1", "/game/prova?demo=1v1"),
    ("/auth/login//", "next=%2Fprofile%2Fsettings", "/auth/login?next=%2Fprofile%2Fsettings"),
    ("/pagina-a-caso/", "", "/pagina-a-caso"),
    # due / davanti: il rimando ne tiene una sola, altrimenti il browser andrebbe su altro.it
    ("//altro.it/", "", "/altro.it"),
])
def test_la_barra_in_fondo_si_rimanda(app, fake_dist, path, query, target):
    # PATH_INFO scritto a mano: il client dei test leggerebbe //altro.it come un altro sito
    (fake_dist / "index.html").write_text(INDEX, encoding="utf-8")
    response = app.test_client().get("/", environ_overrides={"PATH_INFO": path, "QUERY_STRING": query})
    assert response.status_code == 302, path
    assert response.headers["Location"] == target
    response.close()


def test_la_barra_in_fondo_poi_passa_dal_controllo_del_login(app, fake_dist):
    # Il motivo del rimando: /profile/settings/ arriva alla rotta Flask, che vuole il login
    (fake_dist / "index.html").write_text(INDEX, encoding="utf-8")
    response = app.test_client().get("/profile/settings/", follow_redirects=True)
    assert [step.request.path for step in response.history] == ["/profile/settings/", "/profile/settings"]
    assert response.request.path == "/auth/login"
    response.close()


# --- Flask -------------------------------------------------------------------


def test_pagina_dal_build(app, fake_dist):
    (fake_dist / "index.html").write_text("<!doctype html><div id=\"root\"></div>", encoding="utf-8")
    response = app.test_client().get("/auth/login")
    assert response.status_code == 200
    assert response.mimetype == "text/html"
    assert "no-cache" in response.headers["Cache-Control"]
    assert "script-src 'self'" in response.headers["Content-Security-Policy"]
    assert '<div id="root">' in response.get_data(as_text=True)
    response.close()


def test_senza_build_errore_chiaro(app, fake_dist):
    response = app.test_client().get("/auth/login")
    assert response.status_code == 503
    assert response.get_data(as_text=True) == routes.NOT_BUILT


def test_pagina_di_prova_tolta(app):
    # /prova-react non è una rotta: risponde la SPA come ogni indirizzo senza rotta
    # (React: "non trovata")
    assert "/prova-react" not in {rule.rule for rule in app.url_map.iter_rules()}
    assert "prova-react" not in ROUTES_TSX.read_text(encoding="utf-8")
    assert not (FRONTEND / "src" / "pages" / "TestPage.tsx").exists()


# --- Build vero (con Node) ---------------------------------------------------


def _run_node(args):
    node = shutil.which("node")
    result = subprocess.run(
        [node, *args], cwd=FRONTEND, capture_output=True, text=True,
        encoding="utf-8", timeout=120, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.fixture(scope="module")
def build(tmp_path_factory):
    if shutil.which("node") is None:
        pytest.skip("Node non installato: build del frontend saltato")
    if not NODE_MODULES.is_dir():
        pytest.skip("frontend/node_modules manca (npm ci in frontend/): build saltato")
    out = tmp_path_factory.mktemp("dist")
    _run_node([str(NODE_MODULES / "typescript" / "bin" / "tsc"), "--noEmit"])
    _run_node([str(NODE_MODULES / "vite" / "bin" / "vite.js"), "build", "--outDir", str(out), "--emptyOutDir"])
    return out


def test_typescript_e_build_senza_script_ne_stili_dentro(build):
    html = (build / "index.html").read_text(encoding="utf-8")
    scripts = re.findall(r"<script\b[^>]*>", html)
    assert scripts, "nessuno script nel build"
    for tag in scripts:
        src = re.search(r'\bsrc="([^"]+)"', tag)
        assert src and src.group(1).startswith("/static/dist/"), tag
        assert (build / src.group(1).removeprefix("/static/dist/")).is_file(), tag
    assert "style=" not in html
    assert "<style" not in html


@pytest.fixture
def spa_app(monkeypatch, build):
    # Il build di prova sta in una cartella temporanea: dist_dir() la indica sia per
    # index.html sia per i file di /static/dist/ (rotta asset del blueprint spa)
    monkeypatch.setattr(routes, "dist_dir", lambda: build)
    app = create_app("testing")

    @app.before_request
    def fake_stats():
        # Le statistiche finte, così il test non ha bisogno del database
        from flask import request
        if request.path == "/api/stats/me":
            return {"ok": True, "data": STATS_EXAMPLE}
        return None

    return app


@pytest.fixture
def spa_server(spa_app):
    # Con il cookie di prova risulta collegato Mario; senza, nessun login
    with running_server(spa_app, FakeUser("Mario")) as url:
        yield url


def test_nel_browser_react_disegna_e_la_csp_non_blocca(spa_server, tmp_path):
    browser = Browser(find_browser(), tmp_path)
    try:
        browser.send("Page.enable")  # senza, lo script qui sotto non parte con le pagine nuove
        browser.send("Page.addScriptToEvaluateOnNewDocument", source=RECORD)
        browser.open(f"{spa_server}/auth/login", 390, 844, ready="document.querySelector('h1') !== null")
        assert browser.js("document.querySelector('h1').textContent") == "Accedi"
        assert browser.js("window.__csp") == []
        # Senza login la pagina non apre il collegamento al tempo reale
        browser.js("new Promise((r) => setTimeout(r, 500))")
        requests = browser.js("performance.getEntriesByType('resource').map((e) => e.name)")
        assert not [name for name in requests if "/socket.io/" in name], requests
    finally:
        browser.close()


@pytest.mark.parametrize("path", ["/pagina-a-caso", "/Profile/Settings", "/game/prova/altro"])
def test_nel_browser_pagina_non_trovata(spa_server, tmp_path, path):
    # React disegna "Pagina non trovata" con la navbar, e "Torna alla home"
    # porta alla home senza ricaricare; la CSP non blocca niente
    browser = Browser(find_browser(), tmp_path)
    try:
        browser.send("Page.enable")
        browser.send("Page.addScriptToEvaluateOnNewDocument", source=RECORD)
        browser.open(f"{spa_server}{path}", 390, 844, ready="document.querySelector('h1') !== null")
        page = browser.js("""(() => { const main = document.querySelector('main');
          return { page: main.dataset.page, form: main.classList.contains('page--form'),
                   error: document.querySelector('[data-error]')?.dataset.error,
                   h1: document.querySelector('h1').textContent, title: document.title,
                   navbar: document.querySelector('[data-part="navbar"]') !== null,
                   home: document.querySelector('[data-error] a').getAttribute('href') }; })()""")
        assert page == {"page": "error", "form": True, "error": "404", "h1": "Pagina non trovata",
                        "title": "Pagina non trovata · Cinquecento", "navbar": True, "home": "/"}
        assert browser.js("window.__csp") == []
        # __samePage: resta solo se si cambia pagina senza ricaricare
        browser.js("window.__samePage = true")
        browser.click("[data-error] a")
        browser.wait_js("location.pathname === '/' && document.querySelector('[data-error]') === null", "home")
        assert browser.js("window.__samePage") is True
    finally:
        browser.close()


def test_nel_browser_tempo_reale_con_il_login(spa_server, tmp_path):
    # frontend/src/socket/, sulle impostazioni: con il login la pagina si collega
    browser = Browser(find_browser(), tmp_path)
    try:
        browser.send("Network.setCookie", name=TEST_COOKIE[0], value=TEST_COOKIE[1], url=spa_server)
        browser.send("Page.enable")
        browser.send("Page.addScriptToEvaluateOnNewDocument", source=RECORD)
        browser.open(f"{spa_server}/profile/settings", 390, 844, ready=CONNECTED)
        assert browser.js("document.querySelector('h1').textContent") == "Impostazioni"
        assert browser.js("window.__csp") == []
    finally:
        browser.close()


def test_esci_manda_la_richiesta_e_ricarica_la_home(spa_server, tmp_path):
    # "Esci" manda POST /api/auth/logout con il codice CSRF nell'intestazione.
    # La risposta la dà il browser (routes), perché con l'utente finto di running_server
    # il logout vero non cambierebbe niente: la prima volta un errore del server (il
    # pulsante si riaccende e si resta nella pagina), la seconda ok (si ricarica la home)
    calls = []

    def logout(request):
        calls.append({"method": request["method"], "csrf": request["headers"].get("X-CSRFToken", "")})
        if len(calls) == 1:
            return 500, {"ok": False, "error": {"code": "server_error", "message": "Errore del server."}}
        return 200, {"ok": True, "data": {"redirect": "/"}}

    browser = Browser(find_browser(), tmp_path, routes={"*/api/auth/logout": logout})
    try:
        browser.send("Network.setCookie", name=TEST_COOKIE[0], value=TEST_COOKIE[1], url=spa_server)
        browser.open(f"{spa_server}/profile/settings", 390, 844, ready=CONNECTED)
        browser.click("[data-open-stats]")
        browser.wait_js(f"{STATS_OPEN} === '{STATS_EXAMPLE['games']}'", "statistiche nel pannello")
        # __samePage: sparisce solo se la pagina si ricarica davvero (non con navigate di React)
        browser.js("window.__samePage = true")

        browser.click("[data-logout]")
        browser.wait_js("document.querySelector('[data-logout]').disabled === false", "pulsante riacceso dopo l'errore")
        assert len(calls) == 1
        assert browser.js("[window.__samePage, location.pathname]") == [True, "/profile/settings"]

        browser.click("[data-logout]")
        browser.wait_js("window.__samePage === undefined && location.pathname === '/'", "home ricaricata")
    finally:
        browser.close()
    assert [call["method"] for call in calls] == ["POST", "POST"]
    assert all(call["csrf"] for call in calls), calls


# CONNECTED: la pagina è collegata al tempo reale (lo dice il pannello amici)
CONNECTED = "document.querySelector('[data-friends-panel]')?.dataset.connection === 'connected'"
# STATS_OPEN: il pannello statistiche è aperto e mostra le partite giocate
STATS_OPEN = "document.getElementById('stats').open && document.querySelector('[data-stat=\"Partite\"] dd')?.textContent"


def test_cornice_con_il_login(spa_server, spa_app, tmp_path):
    browser = Browser(find_browser(), tmp_path)
    try:
        browser.send("Network.setCookie", name=TEST_COOKIE[0], value=TEST_COOKIE[1], url=spa_server)
        browser.open(f"{spa_server}/profile/settings", 390, 844, ready=CONNECTED)
        # Navbar con il login: nome e iniziale, niente "Accedi"
        navbar = browser.js("""(() => { const b = document.querySelector('[data-open-stats]');
          return { label: b.querySelector('.navbar__label').textContent, avatar: b.querySelector('.avatar').textContent,
                   prompt: document.querySelectorAll('[data-login-prompt]').length,
                   friends: document.querySelector('[data-friends-button]') !== null }; })()""")
        assert navbar == {"label": "Mario", "avatar": "M", "prompt": 0, "friends": True}
        assert browser.js("document.querySelector('[data-banner]')") is None

        # Pannello statistiche: si apre, mostra i numeri, si chiude con la X
        browser.click("[data-open-stats]")
        browser.wait_js(f"{STATS_OPEN} === '{STATS_EXAMPLE['games']}'", "statistiche nel pannello")
        assert browser.js("document.getElementById('stats-title').textContent") == "Mario"
        assert browser.js("document.querySelector('[data-stat=\"Vittorie\"] dd').textContent") == "55%"
        # Esci è un modulo che non va al server da solo (niente action né csrf_token):
        # la richiesta la manda la pagina (test qui sotto)
        logout = browser.js("""(() => { const f = document.querySelector('.sheet__logout');
          return { action: f.getAttribute('action'), inputs: f.querySelectorAll('input').length,
                   button: f.querySelector('[data-logout]') !== null }; })()""")
        assert logout == {"action": None, "inputs": 0, "button": True}
        browser.click("#stats [data-close]")
        browser.wait_js("!document.getElementById('stats').open", "pannello chiuso")

        # Scollegati dal server (come "Esci" da un'altra scheda, P32): avviso con "Ricarica"
        with spa_app.app_context():
            disconnect_user(7)
        browser.wait_js("document.querySelector('[data-banner]')?.dataset.banner === 'error'", "avviso di scollegamento")
        banner = browser.js("""(() => { const b = document.querySelector('[data-banner]');
          return { role: b.role, text: b.querySelector('.banner__text').textContent,
                   action: b.querySelector('[data-banner-action]').textContent }; })()""")
        assert banner["role"] == "alert" and "ricarica la pagina" in banner["text"] and banner["action"] == "Ricarica"
    finally:
        browser.close()
