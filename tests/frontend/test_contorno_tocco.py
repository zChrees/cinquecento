"""P129: al tocco niente contorno del fuoco.

Quando si apre una finestra la pagina dà il fuoco al primo pulsante (la X, "Annulla"):
su iPhone Safari mostrava il contorno rosso del fuoco finché non si toccava altrove.
Dove non c'è un puntatore che passa sopra (@media (hover: none), il telefono) nessun
elemento ha il contorno; da computer resta, per chi usa la tastiera (scelta di
Christian del 10/10/2026). Il telefono si imita con il tocco di Chrome
(Emulation.setTouchEmulationEnabled), che fa valere (hover: none).
Pagina di accesso in Chrome o Edge senza finestra (tests/browser.py): non serve
né il login né MySQL. Se né Chrome né Edge sono installati i controlli si saltano.
"""

import pytest

from app import create_app
from tests.browser import Browser, find_browser, running_server

# L'elemento con il fuoco (arrivato con Tab, come da tastiera) e com'è disegnato il suo contorno
FOCUSED = """(() => {
  const focused = document.activeElement;
  return { touch: matchMedia('(hover: none)').matches, visible: focused.matches(':focus-visible'),
           outline: getComputedStyle(focused).outlineStyle };
})()"""


@pytest.fixture(scope="module")
def server():
    with running_server(create_app("testing")) as url:
        yield url


@pytest.fixture
def browser(tmp_path):
    b = Browser(find_browser(), tmp_path / "chrome")
    yield b
    b.close()


def _open(browser, server):
    browser.open(f"{server}/auth/login", 390, 844, "document.querySelector('[data-login-submit]') !== null")
    browser.js("document.querySelector('input[name=username]').focus()")
    for _ in range(6):  # Tab fino al primo pulsante (le caselle hanno un loro segno del fuoco)
        browser.key("Tab", "Tab", 9)
        if browser.js("document.activeElement.tagName") == "BUTTON":
            break
    assert browser.js("document.activeElement.tagName") == "BUTTON"


def test_da_computer_il_contorno_del_fuoco_resta(browser, server):
    _open(browser, server)
    assert browser.js(FOCUSED) == {"touch": False, "visible": True, "outline": "solid"}


def test_al_tocco_niente_contorno(browser, server):
    browser.send("Emulation.setTouchEmulationEnabled", enabled=True, maxTouchPoints=5)
    _open(browser, server)
    assert browser.js(FOCUSED) == {"touch": True, "visible": True, "outline": "none"}
