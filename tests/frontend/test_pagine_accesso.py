"""P125, P126 e passo 4 della migrazione: le pagine di accesso e registrazione (SPA).

Dal passo 4 le due pagine le disegna React (frontend/src/pages/LoginPage.tsx e
RegisterPage.tsx) e i dati vanno a /api/auth/login e /api/auth/register. Qui si
controlla, in Chrome o Edge senza finestra (tests/browser.py, saltato se nessuno dei
due è installato), che si comportino come le pagine Jinja di prima:
- "Accedi" e "Amici" aprono la finestra "Accedi o registrati per giocare";
- un doppio clic (due clic a 0,15 s) manda una sola richiesta;
- senza connessione il modulo non parte e compare "Nessuna connessione";
- (P126) a ogni misura di schermo il riquadro entra sotto la navbar, senza scorrere;
- gli errori dei campi compaiono sotto il campo giusto, gli altri in basso;
- le regole della password sotto il campo sono quelle del server (forms.PASSWORD_HINT);
- dal link "Registrati" / "Accedi" si passa all'altra pagina senza ricaricare.

Il server dei test non arriva mai alle rotte vere: un `before_request` conta i POST a
/api/auth/ e risponde da sé (dopo 1,5 s, così il secondo clic arriva mentre il primo
aspetta), quindi la suite non ha bisogno del database. Le pagine della SPA vengono dal
build che tests/conftest.py prepara (tests/spa.py).
"""

import threading
import time

import pytest

from app import create_app
from app.blueprints.auth.forms import PASSWORD_HINT
from tests.browser import Browser, find_browser, running_server
from tests.spa import needs_spa

SCREENS = [(360, 640), (375, 667), (390, 844), (412, 915),
           (1024, 768), (1280, 720), (1366, 768), (1920, 1080)]
PAGES = {"login": "/auth/login", "register": "/auth/register"}
API = {"login": "/api/auth/login", "register": "/api/auth/register"}
FORM = {"login": "[data-login-form]", "register": "[data-register-form]"}
ANSWER_SECONDS = 1.5
RECEIVED = "/_prova/ricevuto"
PROMPT_TITLE = "Accedi o registrati per giocare"
OPEN_TITLE = "document.querySelector('dialog[open] .dialog__title')?.textContent ?? ''"
# Risposte finte del server, scelte dallo username scritto nel modulo
FIELD_ERROR = {"ok": False, "error": {"code": "invalid_data", "message": "Scegli una password.",
                                      "fields": {"password": ["Scegli una password."],
                                                 "username": ["Lo username deve avere da 3 a 20 caratteri."]}}}
LOGIN_ERROR = {"ok": False, "error": {"code": "not_allowed", "message": "Nome utente o password non validi."}}


@pytest.fixture(scope="module")
def server():
    if not find_browser():
        pytest.skip("Chrome o Edge non installato")
    needs_spa()
    app = create_app("testing")
    posts = []
    lock = threading.Lock()

    @app.before_request
    def fake_answers():
        from flask import request
        if request.path == RECEIVED:
            return '<!doctype html><p data-received>ricevuto</p>'
        if request.method == "POST" and request.path in API.values():
            username = (request.get_json(silent=True) or {}).get("username")
            if username == "errore-campi":
                return FIELD_ERROR, 400
            if username == "errore-login":
                return LOGIN_ERROR, 403
            with lock:
                posts.append(request.path)
            time.sleep(ANSWER_SECONDS)
            return {"ok": True, "data": {"redirect": RECEIVED}}
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


def _open(browser, server, page, width=360, height=640):
    url = server[0]
    browser.open(f"{url}{PAGES[page]}", width, height, f"document.querySelector('{FORM[page]}') !== null")


def _mouse_click(browser, selector):
    """Clic vero del mouse al centro dell'elemento (non element.click())."""
    box = browser.js(f"""(() => {{ const r = document.querySelector('{selector}').getBoundingClientRect();
      return {{ x: r.left + r.width / 2, y: r.top + r.height / 2 }}; }})()""")
    for kind in ("mousePressed", "mouseReleased"):
        browser.send("Input.dispatchMouseEvent", type=kind, x=box["x"], y=box["y"], button="left", clickCount=1)


def _type(browser, selector, text):
    """Scrive nella casella come la tastiera (React legge l'evento input, non value)."""
    browser.js(f"document.querySelector({selector!r}).focus()")
    browser.send("Input.insertText", text=text)


@pytest.mark.parametrize("page", PAGES)
def test_accedi_e_amici_aprono_la_finestra(server, browser, page):
    _open(browser, server, page)
    for button in (".navbar__account", ".navbar__friends"):
        browser.click(button)
        browser.wait_js(f"{OPEN_TITLE} === {PROMPT_TITLE!r}", f"finestra da {button}")
        assert "CC BY-SA 3.0" in browser.js("document.querySelector('dialog[open] [data-credits]').textContent")
        browser.click("dialog[open] .icon-btn")
        browser.wait_js("!document.querySelector('dialog[open]')", "finestra chiusa")


@pytest.mark.parametrize("page", PAGES)
def test_doppio_clic_una_richiesta_sola(server, browser, page):
    _reset(server)
    _open(browser, server, page)
    submit = f"{FORM[page]} button[type=submit]"
    # Il secondo clic di un doppio clic arriva dopo 0,15 s, mentre il primo aspetta la risposta
    browser.js(f"""(() => {{ const b = document.querySelector('{submit}');
      b.click(); setTimeout(() => b.click(), 150); }})()""")
    browser.wait_js("document.querySelector('[data-received]') !== null", "risposta del server")
    assert _posts(server, API[page]) == 1


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
    assert _posts(server, API["login"]) == 0

    # Tornata la connessione, il modulo parte
    browser.send("Network.emulateNetworkConditions", offline=False, latency=0,
                 downloadThroughput=-1, uploadThroughput=-1)
    browser.wait_js("navigator.onLine === true", "browser online")
    browser.click("dialog[open] .dialog__actions .btn")
    browser.wait_js("!document.querySelector('dialog[open]')", "avviso chiuso")
    _mouse_click(browser, submit)
    browser.wait_js("document.querySelector('[data-received]') !== null", "risposta del server")
    assert _posts(server, API["login"]) == 1


def test_errori_sotto_i_campi_giusti(server, browser):
    _open(browser, server, "register", 390, 844)
    _type(browser, "#username", "errore-campi")
    browser.click("[data-register-submit]")
    browser.wait_js("document.querySelectorAll('.field__error').length === 2", "errori dei campi")
    errors = browser.js("""[...document.querySelectorAll('.field--error')].map((f) => ({
      id: f.querySelector('input').id, invalid: f.querySelector('input').getAttribute('aria-invalid'),
      text: f.querySelector('.field__error').textContent, role: f.querySelector('.field__error').role }))""")
    assert errors == [
        {"id": "username", "invalid": "true", "text": "Lo username deve avere da 3 a 20 caratteri.", "role": "alert"},
        {"id": "password", "invalid": "true", "text": "Scegli una password.", "role": "alert"},
    ]
    assert browser.js("document.querySelector('[data-register-submit]').disabled") is False


def test_credenziali_sbagliate_in_basso(server, browser):
    _open(browser, server, "login", 390, 844)
    _type(browser, "#username", "errore-login")
    browser.click("[data-login-submit]")
    browser.wait_js("document.querySelector('[data-flash-kind=\"error\"]') !== null", "messaggio in basso")
    flash = browser.js("""(() => { const f = document.querySelector('[data-flash-kind="error"]');
      return { text: f.textContent.trim(), role: f.role }; })()""")
    assert flash == {"text": "error" + "Nome utente o password non validi.", "role": "alert"}
    assert browser.js("document.querySelectorAll('.field__error').length") == 0


def test_etichette_e_regole_della_password(server, browser):
    _open(browser, server, "login", 390, 844)
    labels = browser.js("[...document.querySelectorAll('.field__label')].map((l) => [l.htmlFor, l.textContent])")
    assert labels == [["username", "Nome utente o email"], ["password", "Password"]]
    assert browser.js("document.title") == "Accedi · Cinquecento"

    _open(browser, server, "register", 390, 844)
    labels = browser.js("[...document.querySelectorAll('.field__label')].map((l) => [l.htmlFor, l.textContent])")
    assert labels == [["username", "Username"], ["email", "Email"], ["password", "Password"],
                      ["confirm", "Ripeti la password"]]
    # Le regole sono quelle che il server controlla davvero (P61), e solo la password le ha
    hint = browser.js("""(() => { const h = document.querySelector('[data-field-hint="password"]');
      return { id: h.id, text: h.textContent, count: document.querySelectorAll('.field__hint').length,
               described: document.getElementById('password').getAttribute('aria-describedby') }; })()""")
    assert hint == {"id": "password-hint", "text": PASSWORD_HINT, "count": 1, "described": "password-hint"}
    assert browser.js("document.title") == "Registrati · Cinquecento"


def test_da_una_pagina_all_altra_senza_ricaricare(server, browser):
    _open(browser, server, "login", 390, 844)
    browser.js("window.__stessaPagina = true")
    assert browser.js("document.querySelector('.auth__switch a').getAttribute('href')") == "/auth/register"
    browser.click(".auth__switch a")
    browser.wait_js("document.querySelector('[data-register-form]') !== null", "pagina di registrazione")
    assert browser.js("location.pathname") == "/auth/register"
    assert browser.js("window.__stessaPagina") is True  # niente caricamento nuovo: è la SPA
    browser.click(".auth__switch a")
    browser.wait_js("document.querySelector('[data-login-form]') !== null", "di nuovo l'accesso")
    assert browser.js("window.__stessaPagina") is True


# Il riquadro, il pulsante e il collegamento sotto devono stare dentro lo schermo, e la
# pagina (che scorre solo come ultima risorsa, layout.css) non deve avere niente da scorrere.
MEASURE = """(() => {
  const page = document.querySelector('main.page');
  const bottom = (s) => document.querySelector(s).getBoundingClientRect().bottom;
  const heights = [...document.querySelectorAll('.auth .input, .auth button[type=submit]')]
    .map((e) => e.getBoundingClientRect().height);
  return { overflow: page.scrollHeight - page.clientHeight, screen: innerHeight,
           panel: bottom('.auth'), submit: bottom('.auth button[type=submit]'),
           link: bottom('.auth__switch a'), smallest: Math.min(...heights) };
})()"""


@pytest.mark.parametrize("page", PAGES)
def test_il_modulo_entra_senza_scorrere(server, browser, page):
    # Un browser solo per le otto misure: aprire Chrome per ognuna allungava la suite di 30 s.
    problems = []
    for width, height in SCREENS:
        browser.open(f"{server[0]}{PAGES[page]}", width, height,
                     f"document.querySelector('{FORM[page]}') !== null && document.fonts.status === 'loaded'")
        m = browser.js(MEASURE)
        if m["overflow"] > 0:
            problems.append(f"{width}x{height}: la pagina scorre di {m['overflow']} px")
        if max(m["panel"], m["submit"], m["link"]) > m["screen"]:
            problems.append(f"{width}x{height}: riquadro fuori dallo schermo {m}")
        if m["smallest"] < 44:
            problems.append(f"{width}x{height}: caselle e pulsante sotto i 44 px ({m['smallest']})")
    assert not problems, "; ".join(problems)
