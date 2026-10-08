"""P125: script delle pagine di accesso e registrazione (js/pages/auth.js).

Prima di P125 le due pagine non avevano uno script: "Accedi" e "Amici" della navbar
non aprivano niente, un doppio clic sul pulsante del modulo mandava due richieste e
il modulo partiva anche senza connessione. Qui si controlla, in Chrome o Edge senza
finestra (tests/browser.py, saltato se nessuno dei due è installato):
- "Accedi" e "Amici" aprono la finestra "Accedi o registrati per giocare";
- un doppio clic (due clic a 0,15 s) manda una sola richiesta;
- senza connessione il modulo non parte e compare "Nessuna connessione".

Il server dei test non arriva mai alle rotte vere: un `before_request` conta i POST
e risponde da sé dopo 1,5 s (così il secondo clic arriva mentre il primo aspetta),
quindi la suite non ha bisogno del database.
"""

import threading
import time

import pytest

from app import create_app
from tests.browser import Browser, find_browser, running_server

PAGES = {"login": "/auth/login", "register": "/auth/register"}
FORM = {"login": "[data-login-form]", "register": "[data-register-form]"}
ANSWER_SECONDS = 1.5
PROMPT_TITLE = "Accedi o registrati per giocare"
OPEN_TITLE = "document.querySelector('dialog[open] .dialog__title')?.textContent ?? ''"


@pytest.fixture(scope="module")
def server():
    if not find_browser():
        pytest.skip("Chrome o Edge non installato")
    app = create_app("testing")
    posts = []
    lock = threading.Lock()

    @app.before_request
    def count_posts():
        from flask import request
        if request.method == "POST" and request.path in PAGES.values():
            with lock:
                posts.append(request.path)
            time.sleep(ANSWER_SECONDS)
            return '<!doctype html><p data-received>ricevuto</p>'
        return None

    with running_server(app) as url:
        yield url, posts, lock


@pytest.fixture
def browser(tmp_path):
    b = Browser(find_browser(), tmp_path / "chrome")
    try:
        yield b
    finally:
        b.close()


def _posts(server, path):
    _, posts, lock = server
    with lock:
        return posts.count(path)


def _reset(server):
    _, posts, lock = server
    with lock:
        posts.clear()


def _open(browser, server, page):
    url = server[0]
    browser.open(f"{url}{PAGES[page]}", 360, 640, f"document.querySelector('{FORM[page]}') !== null")


def _mouse_click(browser, selector):
    """Clic vero del mouse al centro dell'elemento (non element.click())."""
    box = browser.js(f"""(() => {{ const r = document.querySelector('{selector}').getBoundingClientRect();
      return {{ x: r.left + r.width / 2, y: r.top + r.height / 2 }}; }})()""")
    for kind in ("mousePressed", "mouseReleased"):
        browser.send("Input.dispatchMouseEvent", type=kind, x=box["x"], y=box["y"], button="left", clickCount=1)


@pytest.mark.parametrize("page", PAGES)
def test_accedi_e_amici_aprono_la_finestra(server, browser, page):
    _open(browser, server, page)
    for button in (".navbar__account", ".navbar__friends"):
        browser.click(button)
        browser.wait_js(f"{OPEN_TITLE} === {PROMPT_TITLE!r}", f"finestra da {button}")
        browser.click("dialog[open] .icon-btn")
        browser.wait_js("!document.querySelector('dialog[open]')", "finestra chiusa")


@pytest.mark.parametrize("page", PAGES)
def test_doppio_clic_una_richiesta_sola(server, browser, page):
    _reset(server)
    _open(browser, server, page)
    submit = f"{FORM[page]} button[type=submit]"
    # Il secondo clic di un doppio clic arriva dopo 0,15 s, mentre il primo aspetta la risposta.
    # Con la pagina: un clic su un pulsante spento non fa niente. (Input.dispatchMouseEvent qui
    # non va: aspetta la fine della navigazione, quindi il secondo clic finirebbe sulla risposta.)
    browser.js(f"""(() => {{ const b = document.querySelector('{submit}');
      b.click(); setTimeout(() => b.click(), 150); }})()""")
    browser.wait_js("document.querySelector('[data-received]') !== null", "risposta del server")
    assert _posts(server, PAGES[page]) == 1


def test_senza_connessione_il_modulo_non_parte(server, browser):
    _reset(server)
    _open(browser, server, "login")
    submit = f"{FORM['login']} button[type=submit]"
    browser.send("Network.enable")
    browser.send("Network.emulateNetworkConditions", offline=True, latency=0,
                 downloadThroughput=-1, uploadThroughput=-1)
    browser.wait_js("navigator.onLine === false", "browser offline")
    _mouse_click(browser, submit)
    browser.wait_js(f"{OPEN_TITLE} === 'Nessuna connessione'", "avviso senza connessione")
    assert browser.js(f"document.querySelector('{submit}').disabled") is False
    assert _posts(server, PAGES["login"]) == 0

    # Tornata la connessione, il modulo parte
    browser.send("Network.emulateNetworkConditions", offline=False, latency=0,
                 downloadThroughput=-1, uploadThroughput=-1)
    browser.wait_js("navigator.onLine === true", "browser online")
    browser.click("dialog[open] .dialog__actions .btn")
    browser.wait_js("!document.querySelector('dialog[open]')", "avviso chiuso")
    _mouse_click(browser, submit)
    browser.wait_js("document.querySelector('[data-received]') !== null", "risposta del server")
    assert _posts(server, PAGES["login"]) == 1
