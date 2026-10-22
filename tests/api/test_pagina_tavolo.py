"""P21: pagina del tavolo di gioco con le viste finte (?demo=1v1, ?demo=2v2).

Controlla il "Fatto quando" di SCALETTA.md (P21): la pagina risponde e contiene i
marcatori data-*; con le viste finte il tavolo si disegna e le carte non giocabili
sono disattivate. Il disegno vero si controlla aprendo la pagina con Chrome o Edge
senza finestra (--dump-dom), su un server di prova alla porta 5099; se nessuno dei
due è installato quei controlli si saltano. Non serve MySQL: il login è spento
(LOGIN_DISABLED) tranne nel controllo che lo richiede.
Passo 8 della migrazione: dal lotto 8h l'indirizzo dà la pagina della SPA (il tavolo
React), in tutti gli ambienti, con le stesse regole di ?demo=, e la SPA carica gli
stessi CSS del template del tavolo (il disegno nel browser lo confronta
tests/table2/test_tavolo_react.py). Il template di prima si vede con ?ui=jinja, fino
al passo 9: i controlli sull'HTML del template lo aprono così.
"""

import json
import os
import re
import shutil
import socket
import subprocess
import threading
from html.parser import HTMLParser
from pathlib import Path

import pytest
from werkzeug.serving import make_server

from app import create_app

ROOT = Path(__file__).resolve().parents[2]
DEV = ROOT / "app" / "static" / "dev"
PORT = 5099
BROWSER_PATHS = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
)


def _app(login=False):
    app = create_app("testing")
    app.config["LOGIN_DISABLED"] = not login
    return app


@pytest.fixture
def client():
    return _app().test_client()


def _text(response):
    text = response.get_data(as_text=True)
    response.close()
    return text


# --- Risposte del server -----------------------------------------------------


def test_senza_login_rimanda_all_accesso():
    response = _app(login=True).test_client().get("/game/abc123")
    assert response.status_code == 302
    assert response.headers["Location"].startswith("/auth/login")


@pytest.mark.parametrize("mode", ["1v1", "2v2"])
def test_pagina_con_vista_finta(client, mode):
    response = client.get(f"/game/prova?demo={mode}&ui=jinja")
    assert response.status_code == 200
    html = _text(response)
    assert 'data-table data-game-id="prova"' in html
    assert f'data-demo-url="/static/dev/vista_{mode}.json"' in html
    assert 'data-page="game"' in html and "page--game" in html
    # Al tavolo niente navbar
    assert 'data-part="navbar"' not in html
    assert '<script type="module" src="/static/js/pages/game.js"></script>' in html


def test_pagina_senza_demo_aspetta_la_partita(client):
    html = _text(client.get("/game/a1b2c3d4?ui=jinja"))
    assert 'data-game-id="a1b2c3d4"' in html
    assert "data-demo-url" not in html


@pytest.mark.parametrize("path", ["/game/prova?demo=3v3", "/game/prova?demo=", "/game/" + "x" * 65, "/game/ab%20cd"])
def test_indirizzi_non_validi(client, path):
    assert client.get(path).status_code == 404


def test_viste_finte_solo_in_sviluppo_e_test():
    app = _app()
    app.config["ENV_NAME"] = "demo"
    assert app.test_client().get("/game/prova?demo=1v1&ui=jinja").status_code == 404
    assert app.test_client().get("/game/prova?ui=jinja").status_code == 200


# --- Passo 8: il tavolo React (con ?ui=react dall'8a, sempre dall'8h) -----------


@pytest.fixture
def fake_spa(monkeypatch, tmp_path):
    # Una pagina della SPA finta, così non serve il build (come test_spa.py)
    from app.blueprints.spa import routes as spa_routes
    (tmp_path / "index.html").write_text('<!doctype html><div id="root"></div>', encoding="utf-8")
    monkeypatch.setattr(spa_routes, "dist_dir", lambda: tmp_path)


@pytest.mark.parametrize("path", ["/game/prova", "/game/prova?demo=1v1", "/game/a1b2c3d4?demo=2v2",
                                  "/game/prova?ui=react", "/game/prova?demo=1v1&ui=react",
                                  "/game/a1b2c3d4?ui=react&demo=2v2"])
def test_tavolo_react_e_la_pagina_della_spa(client, fake_spa, path):
    html = _text(client.get(path))
    assert '<div id="root">' in html and "data-table" not in html


@pytest.mark.parametrize("path", ["/game/prova?ui=jinjax", "/game/prova?ui=", "/game/prova?ui=react&demo=3v3",
                                  "/game/prova?ui=jinja&demo=3v3", "/game/" + "x" * 65 + "?ui=react"])
def test_tavolo_react_indirizzi_non_validi(client, fake_spa, path):
    assert client.get(path).status_code == 404


def test_tavolo_react_ovunque_ma_viste_finte_solo_in_sviluppo_e_test(fake_spa):
    # Scelta del 20/10: ?ui=react in tutti gli ambienti, per provarlo dal telefono
    app = _app()
    app.config["ENV_NAME"] = "demo"
    assert app.test_client().get("/game/prova?ui=react").status_code == 200
    assert app.test_client().get("/game/prova").status_code == 200
    assert app.test_client().get("/game/prova?demo=1v1&ui=react").status_code == 404
    assert app.test_client().get("/game/prova?demo=1v1").status_code == 404


def test_tavolo_react_senza_login_rimanda_all_accesso(fake_spa):
    response = _app(login=True).test_client().get("/game/abc123?ui=react")
    assert response.status_code == 302
    assert response.headers["Location"].startswith("/auth/login")
    response = _app(login=True).test_client().get("/game/abc123?ui=jinja")
    assert response.status_code == 302
    assert response.headers["Location"].startswith("/auth/login")


def test_la_spa_carica_i_css_del_tavolo_nello_stesso_ordine():
    # frontend/index.html (la <head> della SPA) deve avere i CSS di game/table.html,
    # nello stesso ordine: il tavolo React usa gli stessi stili
    template = (ROOT / "app" / "templates" / "game" / "table.html").read_text(encoding="utf-8")
    wanted = re.findall(r"filename='(css/[^']+)'", template)
    spa = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    loaded = re.findall(r'href="/static/(css/[^"]+)"', spa)
    assert len(wanted) == 9
    assert [name for name in loaded if name in wanted] == wanted


def test_css_e_js_del_tavolo_esistono(client):
    html = _text(client.get("/game/prova?demo=1v1&ui=jinja"))
    for name in ("card", "hand", "table", "trick", "scoreboard", "timer"):
        path = f"/static/css/components/{name}.css"
        assert f'href="{path}"' in html, name
        assert client.get(path).status_code == 200, name
    assert client.get("/static/css/pages/game.css").status_code == 200
    for name in ("Table", "Trick", "Scoreboard", "Timer", "SingButtons"):
        assert client.get(f"/static/js/components/{name}.js").status_code == 200, name


def test_una_sola_funzione_render():
    code = (ROOT / "app" / "static" / "js" / "pages" / "game.js").read_text(encoding="utf-8")
    assert code.count("function render(") == 1
    assert code.count("root.replaceChildren(Table(") == 1


# --- Il tavolo disegnato nel browser ------------------------------------------


class _Elements(HTMLParser):
    """Raccoglie gli elementi della pagina con i loro attributi e il loro testo."""

    def __init__(self):
        super().__init__()
        self.elements = []
        self._open = []

    def handle_starttag(self, tag, attrs):
        element = {"tag": tag, "attrs": dict(attrs), "text": ""}
        self.elements.append(element)
        if tag not in {"img", "input", "br", "meta", "link"}:
            self._open.append(element)

    def handle_endtag(self, tag):
        for index in range(len(self._open) - 1, -1, -1):
            if self._open[index]["tag"] == tag:
                del self._open[index:]
                break

    def handle_data(self, data):
        for element in self._open:
            element["text"] += data

    def having(self, name, value=None):
        return [e for e in self.elements if name in e["attrs"] and (value is None or e["attrs"][name] == value)]


def _browser():
    path = os.environ.get("CHROME_PATH")
    if path and Path(path).is_file():
        return path
    for name in ("chrome", "msedge", "google-chrome", "chromium"):
        found = shutil.which(name)
        if found:
            return found
    for candidate in BROWSER_PATHS:
        if Path(candidate).is_file():
            return candidate
    pytest.skip("Chrome o Edge non trovati: controllo del tavolo nel browser saltato")


@pytest.fixture(scope="module")
def server():
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", PORT)) == 0:
            pytest.fail(f"La porta {PORT} è occupata: chiudi il server che la usa e rilancia.", pytrace=False)
    srv = make_server("127.0.0.1", PORT, _app(), threaded=True)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{PORT}"
    srv.shutdown()
    thread.join(timeout=5)


def _render(server, tmp_path, mode):
    browser = _browser()
    result = subprocess.run(
        [browser, "--headless=new", "--disable-gpu", f"--user-data-dir={tmp_path}",
         "--virtual-time-budget=5000", "--window-size=390,844", "--dump-dom",
         f"{server}/game/prova?demo={mode}&ui=jinja"],
        capture_output=True, text=True, encoding="utf-8", timeout=60, check=False,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    page = _Elements()
    page.feed(result.stdout)
    return page


def _view(mode):
    return json.loads((DEV / f"vista_{mode}.json").read_text(encoding="utf-8"))


def _hand_buttons(page):
    return [e for e in page.having("data-suit") if e["tag"] == "button" and "card" in e["attrs"].get("class", "")]


def test_tavolo_1v1_nel_browser(server, tmp_path):
    view = _view("1v1")
    page = _render(server, tmp_path, "1v1")
    assert page.having("data-mode", "1v1"), "il tavolo non è stato disegnato"
    assert {e["attrs"]["data-position"] for e in page.having("data-position")} == {"top", "bottom"}

    # La tua mano: giocabili solo le carte di legal.play
    buttons = _hand_buttons(page)
    assert len(buttons) == len(view["hand"])
    playable = {(c["suit"], c["rank"]) for c in view["legal"]["play"]}
    for button in buttons:
        card = (button["attrs"]["data-suit"], int(button["attrs"]["data-rank"]))
        assert ("disabled" in button["attrs"]) == (card not in playable), card

    # Canto: un pulsante per ogni seme di legal.sing; 20 perché nella mano c'è già un canto
    sing = page.having("data-sing-button")
    assert [e["attrs"]["data-suit"] for e in sing] == view["legal"]["sing"]
    assert "Canta 20 a spade" in sing[0]["text"]

    # Presa, mazzo, briscola, turno
    assert page.having("data-trick")[0]["attrs"]["data-count"] == str(len(view["trick"]["cards"]))
    assert page.having("data-deck-count")[0]["attrs"]["data-deck-count"] == str(view["deck_count"])
    # P108: la briscola solo nell'angolo in alto a destra (Cavallo e Re), non più sul mazzo
    assert not page.having("data-trump")
    badges = page.having("data-trump-badge")
    assert len(badges) == 1 and badges[0]["attrs"]["data-trump-badge"] == view["trump"]
    turn = page.having("data-turn", "yes")
    assert len(turn) == 1 and turn[0]["attrs"]["data-seat"] == str(view["turn"]["seat"])
    assert len(page.having("data-timer")) == 1
    assert page.having("data-scoreboard") and page.having("data-leave")


def test_tavolo_2v2_nel_browser(server, tmp_path):
    view = _view("2v2")
    page = _render(server, tmp_path, "2v2")
    assert page.having("data-mode", "2v2"), "il tavolo non è stato disegnato"
    positions = {e["attrs"]["data-seat"]: e["attrs"]["data-position"] for e in page.having("data-position")}
    # Tu (posto 0) in basso, poi verso destra: 1 a destra, 2 (compagno) in alto, 3 a sinistra
    assert positions == {"0": "bottom", "1": "right", "2": "top", "3": "left"}

    # Non è il tuo turno: tutte le carte disattivate, nessun pulsante Canta
    buttons = _hand_buttons(page)
    assert len(buttons) == len(view["hand"])
    assert all("disabled" in b["attrs"] for b in buttons)
    assert not page.having("data-sing-button")

    # Nessuno ha cantato 40: niente seme né scritta al posto della briscola (P71);
    # turno di Rosalia (scollegata)
    assert not page.having("data-trump") and not page.having("data-trump-badge")
    turn = page.having("data-turn", "yes")
    assert len(turn) == 1 and turn[0]["attrs"]["data-seat"] == "3"
    assert "scollegato · 48 s" in turn[0]["text"]
    partner = next(e for e in page.having("data-seat", "2") if e["tag"] == "section")
    assert "compagno" in partner["text"]
    # P71: niente più "mazziere" né "Carte franche"
    table = page.having("data-mode", "2v2")[0]["text"]
    assert "mazziere" not in table and "Carte franche" not in table
