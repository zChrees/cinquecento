"""Passo 1 della migrazione (docs/MIGRAZIONE-FRONTEND.md): la SPA servita da Flask.

Controlla:
- gli indirizzi della SPA sono gli stessi in Flask (app/blueprints/spa/routes.py) e
  in Vite (frontend/vite.config.ts), e ognuno ha la sua rotta;
- Flask manda index.html del build, da richiedere ogni volta (no-cache), con la CSP;
  senza build risponde 503 con un messaggio chiaro; la pagina di prova non c'è con
  APP_ENV=demo;
- con Node e frontend/node_modules: TypeScript non trova errori, il build vero
  (in una cartella temporanea, fuori dal progetto) non ha script né stili scritti
  dentro la pagina, e nel browser React disegna la pagina di prova, il pulsante
  funziona e la CSP non blocca niente. Senza Node o senza `npm ci` questi si saltano;
- passo 3 (frontend/src/socket/): senza login la connessione è rifiutata e il pulsante
  del tempo reale resta spento; con il login la pagina si collega, riceve home:status
  (1 online) e manda queue:leave ricevendo "ok".
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest
from flask import send_from_directory

from app import create_app
from app.blueprints.spa import routes
from tests.browser import TEST_COOKIE, Browser, FakeUser, find_browser, running_server

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"
VITE_CONFIG = FRONTEND / "vite.config.ts"
NODE_MODULES = FRONTEND / "node_modules"
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
    rules = {rule.rule for rule in app.url_map.iter_rules() if rule.endpoint.startswith("spa.")}
    assert set(routes.SPA_PATHS) <= rules


# --- Flask -------------------------------------------------------------------


def test_pagina_di_prova_dal_build(app, fake_dist):
    (fake_dist / "index.html").write_text("<!doctype html><div id=\"root\"></div>", encoding="utf-8")
    response = app.test_client().get("/prova-react")
    assert response.status_code == 200
    assert response.mimetype == "text/html"
    assert "no-cache" in response.headers["Cache-Control"]
    assert "script-src 'self'" in response.headers["Content-Security-Policy"]
    assert '<div id="root">' in response.get_data(as_text=True)
    response.close()


def test_senza_build_errore_chiaro(app, fake_dist):
    response = app.test_client().get("/prova-react")
    assert response.status_code == 503
    assert response.get_data(as_text=True) == routes.NOT_BUILT


def test_pagina_di_prova_solo_in_sviluppo_e_nei_test(app, fake_dist):
    (fake_dist / "index.html").write_text("<!doctype html>", encoding="utf-8")
    app.config["ENV_NAME"] = "demo"
    assert app.test_client().get("/prova-react").status_code == 404


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
def spa_server(monkeypatch, build):
    monkeypatch.setattr(routes, "dist_dir", lambda: build)
    app = create_app("testing")
    # I file del build di prova stanno in una cartella temporanea: /static/dist/...
    # si serve da lì, il resto di /static come sempre
    static = app.view_functions["static"]

    def static_with_build(filename):
        if filename.startswith("dist/"):
            return send_from_directory(build, filename.removeprefix("dist/"))
        return static(filename=filename)

    app.view_functions["static"] = static_with_build
    # Con il cookie di prova risulta collegato Mario; senza, nessun login
    with running_server(app, FakeUser("Mario")) as url:
        yield url


def test_nel_browser_react_disegna_e_la_csp_non_blocca(spa_server, tmp_path):
    browser = Browser(find_browser(), tmp_path)
    try:
        browser.send("Page.enable")  # senza, lo script qui sotto non parte con le pagine nuove
        browser.send("Page.addScriptToEvaluateOnNewDocument", source=RECORD)
        browser.open(f"{spa_server}/prova-react", 390, 844,
                     ready="document.querySelector('[data-spa-message]') !== null")
        assert browser.js("document.querySelector('h1').textContent") == "Prova React"
        browser.click("[data-spa-button]")
        browser.wait_js(
            "document.querySelector('[data-spa-message]').textContent"
            " === 'Hai premuto il pulsante una volta.'",
            "il clic aggiorna la frase",
        )
        # Passo 3: senza login il server rifiuta la connessione (contratto 1.4)
        browser.wait_js("document.querySelector('[data-spa-connection=\"not_logged_in\"]') !== null",
                        "connessione rifiutata senza login")
        assert browser.js("document.querySelector('[data-spa-send]').disabled") is True
        assert browser.js("window.__csp") == []
    finally:
        browser.close()


def test_nel_browser_tempo_reale_con_il_login(spa_server, tmp_path):
    # Passo 3 (frontend/src/socket/): connessione, un evento del server (home:status)
    # e un evento della pagina con la sua risposta (queue:leave)
    browser = Browser(find_browser(), tmp_path)
    try:
        browser.send("Network.setCookie", name=TEST_COOKIE[0], value=TEST_COOKIE[1], url=spa_server)
        browser.send("Page.enable")
        browser.send("Page.addScriptToEvaluateOnNewDocument", source=RECORD)
        browser.open(f"{spa_server}/prova-react", 390, 844,
                     ready="document.querySelector('[data-spa-connection=\"connected\"]') !== null")
        browser.wait_js("document.querySelector('[data-spa-online]').textContent === '1'",
                        "home:status arrivato")
        browser.click("[data-spa-send]")
        browser.wait_js("document.querySelector('[data-spa-answer]').textContent === 'Il server ha risposto: ok'",
                        "risposta di queue:leave")
        assert browser.js("document.querySelector('[data-spa-send]').disabled") is False
        assert browser.js("window.__csp") == []
    finally:
        browser.close()
