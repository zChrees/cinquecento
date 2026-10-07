"""Aiuti comuni per i test che aprono le pagine in un browser vero (P22, P46).

- find_browser(): Chrome o Edge installati; se mancano, il test si salta.
- Browser: il browser senza finestra, pilotato con il protocollo DevTools
  (websocket-client, in requirements-dev.txt). Serve i font di Google Fonts da
  una copia fuori dal progetto (FONT_CACHE, scaricata la prima volta: il font
  delle icone pesa circa 5 MB, D40) e può rispondere lui ad altre richieste
  (per esempio GET /friends/ con i dati di app/static/dev/), così il test non
  ha bisogno di MySQL.
- running_server(): il sito sulla porta dei test (5099), con un utente finto che
  risulta collegato solo con il cookie di prova (TEST_COOKIE).

Non è un file di test (non comincia con test_): lo importano i test con
`from tests.browser import ...` (la cartella del progetto è nel percorso di
Python grazie a tests/conftest.py).
"""

import base64
import contextlib
import fnmatch
import hashlib
import json
import os
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

import pytest
import websocket
from werkzeug.serving import make_server

from app.extensions import login_manager
from app.realtime.presence import presence

PORT = 5099
TEST_COOKIE = ("prova_utente", "mario")
FONT_CACHE = Path(tempfile.gettempdir()) / "cinquecento-test-font-cache"
FONT_ORIGINS = ("https://fonts.googleapis.com/*", "https://fonts.gstatic.com/*")
BROWSER_PATHS = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
)


class FakeUser:
    """Utente con il login, con i nomi che base.html e la navbar leggono (P16)."""

    is_authenticated = True
    is_active = True
    is_anonymous = False

    def __init__(self, username, user_id=7):
        self.username = username
        self.avatar = None
        self.id = user_id

    def get_id(self):
        return str(self.id)


def find_browser():
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
    pytest.skip("Chrome o Edge non trovati: controlli nel browser saltati")


def read_devtools_port(port_file):
    """La porta scritta da Chrome in DevToolsActivePort (prima riga), o None se non è ancora
    pronta: il file non c'è, non è completo (Chrome scrive la porta e poi una seconda riga),
    o Chrome lo sta scrivendo (su Windows è bloccato e leggerlo dà PermissionError: prima
    questo faceva fallire a caso i test nel browser)."""
    try:
        lines = port_file.read_text().splitlines()
    except (FileNotFoundError, PermissionError):
        return None
    return lines[0].strip() if len(lines) >= 2 and lines[0].strip() else None


def wait(condition, timeout, what):
    """Aspetta che condition() sia vera, controllando spesso; fallisce dopo timeout secondi."""
    end = time.monotonic() + timeout
    while True:
        value = condition()
        if value:
            return value
        if time.monotonic() > end:
            pytest.fail(f"Tempo scaduto: {what}", pytrace=False)
        time.sleep(0.05)


@contextlib.contextmanager
def running_server(app, user=None):
    """Avvia `app` sulla porta dei test; con il cookie di prova risulta collegato `user`.

    P124: spegnendo il server, le schede ancora collegate non passano dallo scollegamento
    (connection_events.py): quelle segnate online mentre era acceso si tolgono da
    presence.py, altrimenti i file di test dopo vedrebbero "2 online" invece di 1.
    """
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", PORT)) == 0:
            pytest.fail(f"La porta {PORT} è occupata: chiudi il server che la usa e rilancia.", pytrace=False)

    def load_test_user(request):
        return user if user and request.cookies.get(TEST_COOKIE[0]) == TEST_COOKIE[1] else None

    before = {user_id: set(presence.tabs_of(user_id)) for user_id in presence.online_users()}
    previous = login_manager._request_callback
    login_manager.request_loader(load_test_user)
    srv = make_server("127.0.0.1", PORT, app, threaded=True)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{PORT}"
    finally:
        srv.shutdown()
        thread.join(timeout=5)
        login_manager._request_callback = previous
        for user_id in presence.online_users():
            for sid in set(presence.tabs_of(user_id)) - before.get(user_id, set()):
                presence.remove(user_id, sid)


class Browser:
    """Chrome o Edge senza finestra, pilotato con il protocollo DevTools.

    `routes` (facoltativo): {"schema dell'indirizzo": funzione(richiesta) -> (codice, dati JSON)}.
    Le richieste che corrispondono a uno schema (per esempio "*/friends/*") le
    intercetta il browser e risponde la funzione, senza passare dal server.
    """

    def __init__(self, path, profile, routes=None):
        self.routes = routes or {}
        self.process = subprocess.Popen(
            [path, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
             "--remote-debugging-port=0", f"--user-data-dir={profile}", "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        port_file = Path(profile) / "DevToolsActivePort"
        port = wait(lambda: read_devtools_port(port_file), 30, "avvio del browser")
        targets = wait(lambda: self._pages(port), 15, "pagina del browser")
        self.ws = websocket.create_connection(targets[0]["webSocketDebuggerUrl"], timeout=30,
                                              suppress_origin=True)
        self.next_id = 0
        patterns = [*FONT_ORIGINS, *self.routes]
        self.send("Fetch.enable", patterns=[{"urlPattern": pattern} for pattern in patterns])

    @staticmethod
    def _pages(port):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=5) as response:
                return [t for t in json.load(response) if t["type"] == "page"]
        except OSError:
            return None

    def _post(self, method, **params):
        """Manda un comando senza aspettare la risposta (che poi send() ignora)."""
        self.next_id += 1
        self.ws.send(json.dumps({"id": self.next_id, "method": method, "params": params}))
        return self.next_id

    def send(self, method, **params):
        waiting = self._post(method, **params)
        while True:
            message = json.loads(self.ws.recv())
            if message.get("method") == "Fetch.requestPaused":
                self._intercept(message["params"])
            elif message.get("id") == waiting:
                if "error" in message:
                    raise RuntimeError(f"{method}: {message['error']}")
                return message.get("result", {})

    def _intercept(self, paused):
        url = paused["request"]["url"]
        if url.startswith(("https://fonts.googleapis.com/", "https://fonts.gstatic.com/")):
            self._serve_font(paused)
            return
        for pattern, handler in self.routes.items():
            if _matches(pattern, url):
                status, data = handler(paused["request"])
                self._fulfill(paused["requestId"], status, "application/json", json.dumps(data).encode("utf-8"))
                return
        self._post("Fetch.continueRequest", requestId=paused["requestId"])

    def _fulfill(self, request_id, status, content_type, body):
        self._post("Fetch.fulfillRequest", requestId=request_id, responseCode=status,
                   responseHeaders=[{"name": "Content-Type", "value": content_type},
                                    {"name": "Access-Control-Allow-Origin", "value": "*"}],
                   body=base64.b64encode(body).decode("ascii"))

    def _serve_font(self, paused):
        """Risponde a una richiesta a Google Fonts con la copia salvata (scaricata la prima volta)."""
        request = paused["request"]
        key = hashlib.sha256(f"{request['url']} {request['headers'].get('User-Agent', '')}".encode()).hexdigest()
        body, kind = FONT_CACHE / key, FONT_CACHE / f"{key}.type"
        try:
            if not body.is_file():
                download = urllib.request.Request(request["url"], headers={
                    "User-Agent": request["headers"].get("User-Agent", ""),
                    "Accept": request["headers"].get("Accept", "*/*"),
                })
                with urllib.request.urlopen(download, timeout=120) as response:
                    data = response.read()
                    content_type = response.headers.get("Content-Type", "application/octet-stream")
                FONT_CACHE.mkdir(exist_ok=True)
                kind.write_text(content_type, encoding="utf-8")
                body.write_bytes(data)   # per ultimo: un file a metà non resta nella copia
            self._fulfill(paused["requestId"], 200, kind.read_text(encoding="utf-8"), body.read_bytes())
        except OSError:
            # Senza rete: il font manca e la pagina usa quelli di riserva
            self._post("Fetch.failRequest", requestId=paused["requestId"], errorReason="InternetDisconnected")

    def js(self, expression):
        result = self.send("Runtime.evaluate", expression=expression, returnByValue=True, awaitPromise=True)
        if "exceptionDetails" in result:
            raise AssertionError(f"Errore JS: {result['exceptionDetails']}")
        return result["result"].get("value")

    def wait_js(self, expression, what, timeout=15):
        return wait(lambda: self.js(expression), timeout, what)

    def click(self, selector):
        self.js(f"document.querySelector({json.dumps(selector)}).click()")

    def key(self, name, code, key_code):
        for kind in ("keyDown", "keyUp"):
            self.send("Input.dispatchKeyEvent", type=kind, key=name, code=code, windowsVirtualKeyCode=key_code)

    def open(self, url, width, height, ready="true", timeout=15):
        """Apre `url` a width×height con "riduci movimento" e aspetta che `ready` (JS) sia vero."""
        self.send("Emulation.setDeviceMetricsOverride", width=width, height=height, deviceScaleFactor=1, mobile=False)
        self.send("Emulation.setEmulatedMedia", features=[{"name": "prefers-reduced-motion", "value": "reduce"}])
        self.send("Page.navigate", url=url)
        self.wait_js(f"document.readyState === 'complete' && document.fonts.status === 'loaded' && ({ready})",
                     f"pagina {url} a {width}x{height}", timeout)

    def close(self):
        try:
            self.ws.close()
        finally:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()


def _matches(pattern, url):
    """Schema con * come in Fetch.enable ("*/friends/*")."""
    return fnmatch.fnmatchcase(url, pattern)
