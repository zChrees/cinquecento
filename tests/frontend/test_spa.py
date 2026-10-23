"""Passo 1 della migrazione (docs/MIGRAZIONE-FRONTEND.md): la SPA servita da Flask.

Controlla:
- gli indirizzi della SPA sono gli stessi in Flask (app/blueprints/spa/routes.py) e
  in Vite (frontend/vite.config.ts), e ognuno ha la sua rotta;
- Flask manda index.html del build, da richiedere ogni volta (no-cache), con la CSP;
  senza build risponde 503 con un messaggio chiaro; la pagina di prova /prova-react
  non c'è più (tolta con il passo 6);
- con Node e frontend/node_modules: TypeScript non trova errori, il build vero
  (in una cartella temporanea, fuori dal progetto) non ha script né stili scritti
  dentro la pagina, e nel browser React disegna la pagina di accesso e la CSP non
  blocca niente. Senza Node o senza `npm ci` questi si saltano;
- passo 3 (frontend/src/socket/): senza login la pagina non si collega al tempo
  reale; con il login (le impostazioni, dal passo 6) si collega. Il controllo su
  home:status della pagina di prova è tornato con la home (7a, test_spa_home.py);
  quello su queue:leave torna con la coda (7b);
- passo 5a (la cornice con il login): la navbar ha nome e avatar, il pannello
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


# --- Indirizzi ---------------------------------------------------------------


def test_stessi_indirizzi_in_flask_e_in_vite(app):
    code = VITE_CONFIG.read_text(encoding="utf-8")
    found = re.search(r"const SPA_PATHS: string\[\] = \[(.*?)\];", code, flags=re.DOTALL)
    assert found, "SPA_PATHS non trovato in vite.config.ts"
    assert tuple(re.findall(r"'([^']+)'", found.group(1))) == routes.SPA_PATHS
    # Ogni indirizzo ha una rotta GET (nel blueprint spa o in quello del suo argomento)
    rules = {rule.rule for rule in app.url_map.iter_rules() if "GET" in rule.methods}
    assert set(routes.SPA_PATHS) <= rules


@pytest.mark.parametrize(("url", "react"), [
    ("/game/prova", True),
    ("/game/prova?demo=1v1", True),
    ("/game/e5f6a7b8#qualcosa", True),
    ("/game/prova?ui=react", True),
    ("/game/prova?demo=1v1&ui=react", True),
    ("/game/e5f6a7b8?ui=react&demo=2v2", True),
    ("/game/prova?ui=jinjax", True),
    ("/game/prova?xui=jinja", True),
    ("/game/prova?ui=jinja", True),
    ("/game/prova?demo=1v1&ui=jinja", True),
    ("/game/e5f6a7b8?ui=jinja&demo=2v2", True),
    ("/game/prova/altro", False),
    ("/game/", False),
    ("/gamex/prova", False),
])
def test_vite_tiene_il_tavolo_react(url, react):
    # Passo 8: in sviluppo Vite serve il tavolo React (GAME_TABLE di vite.config.ts,
    # dentro l'espressione di flaskPattern): ogni /game/<codice>, con qualsiasi
    # parametro (dal lotto 9a anche ?ui=jinja: il tavolo Jinja non c'è più)
    code = VITE_CONFIG.read_text(encoding="utf-8")
    found = re.search(r"const GAME_TABLE: string = '([^']+)';", code)
    assert found, "GAME_TABLE non trovato in vite.config.ts"
    pattern = found.group(1).replace("\\\\", "\\")  # nel testo di JavaScript la \ è scritta \\
    to_flask = re.compile(f"^/(?!{pattern})")
    assert (to_flask.match(url) is None) is react


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


def test_pagina_di_prova_tolta(app, fake_dist):
    # Passo 6: /prova-react serviva finché non c'era una pagina vera con il login
    (fake_dist / "index.html").write_text("<!doctype html>", encoding="utf-8")
    assert app.test_client().get("/prova-react").status_code == 404
    assert "/prova-react" not in routes.SPA_PATHS
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
        # Passo 5a: le statistiche finte, così il test non ha bisogno del database
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
        # Passo 3: senza login la pagina non apre il collegamento al tempo reale
        browser.js("new Promise((r) => setTimeout(r, 500))")
        requests = browser.js("performance.getEntriesByType('resource').map((e) => e.name)")
        assert not [name for name in requests if "/socket.io/" in name], requests
    finally:
        browser.close()


def test_nel_browser_tempo_reale_con_il_login(spa_server, tmp_path):
    # Passo 3 (frontend/src/socket/), dal passo 6 sulle impostazioni: con il login la pagina si collega
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
    # Lotto 9c: "Esci" manda POST /api/auth/logout con il codice CSRF nell'intestazione.
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


# CONNECTED: la pagina è collegata al tempo reale (lo dice il pannello amici, dal passo 6)
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
        # Lotto 9c: Esci non è più un modulo che va al server da solo (niente action
        # né csrf_token): la richiesta la manda la pagina (test qui sotto)
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
