"""P34: rifinitura mobile e accessibilità.

Controlla le correzioni trovate con un controllo di accessibilità di tutte le pagine
(axe-core, lanciato a mano fuori dal progetto il 29/09/2026) e dai riepiloghi:
- ogni pagina ha un solo titolo principale (<h1>), anche dove si vede solo il logo;
- le icone dei canti accanto al nome hanno un ruolo, così l'etichetta si legge;
- al tavolo si gioca una carta con la sola tastiera (Tab e Invio);
- dopo un ricaricamento con il pannello amici aperto, "indietro" chiude di nuovo il
  pannello riaperto (prima la cronologia teneva lo stato vecchio).

Le pagine si aprono in Chrome o Edge senza finestra (tests/browser.py), con un utente
di prova collegato e senza MySQL: il pannello amici si apre anche se la lista non
arriva. Se né Chrome né Edge sono installati i controlli nel browser si saltano.
"""

import pytest

from app import create_app
from tests.browser import TEST_COOKIE, Browser, FakeUser, find_browser, running_server

PHONE = (360, 640)
ENTER = chr(13)  # il carattere che il tasto Invio scrive


@pytest.fixture(scope="module")
def server():
    with running_server(create_app("testing"), FakeUser("Mario", 12)) as url:
        yield url


@pytest.fixture
def browser(server, tmp_path):
    b = Browser(find_browser(), tmp_path / "chrome")
    yield b
    b.close()


def _login(browser, server):
    browser.send("Network.setCookie", name=TEST_COOKIE[0], value=TEST_COOKIE[1], url=server)


@pytest.mark.parametrize("path, logged", [
    ("/", True), ("/game/prova?demo=1v1", True), ("/profile/settings", True),
    ("/auth/login", False), ("/auth/register", False),
])
def test_un_solo_titolo_principale(browser, server, path, logged):
    if logged:
        _login(browser, server)
    browser.open(server + path, *PHONE)
    assert browser.js("location.pathname") == path.split("?")[0]
    assert browser.js("[...document.querySelectorAll('h1')].map((h) => h.textContent.trim().length > 0)") == [True]


def test_icone_dei_canti_con_ruolo(browser, server):
    _login(browser, server)
    browser.open(f"{server}/game/prova?demo=1v1", *PHONE, "document.querySelector('.sing-badge') !== null")
    badge = browser.js("""(() => { const b = document.querySelector('.sing-badge');
      return { role: b.getAttribute('role'), label: b.getAttribute('aria-label') }; })()""")
    assert badge == {"role": "img", "label": "Ha cantato 40 a coppe"}


def test_una_carta_giocata_con_la_tastiera(browser, server):
    _login(browser, server)
    browser.open(f"{server}/game/prova?demo=1v1", *PHONE, "document.querySelector('[data-mode]') !== null")
    for _ in range(30):
        browser.key("Tab", "Tab", 9)
        if browser.js("document.activeElement.matches('.table__mine .hand button.card:not([disabled])')"):
            break
    else:
        pytest.fail("con Tab non si arriva alle carte della mano")
    card = browser.js("document.activeElement.getAttribute('aria-label')")
    # Invio come da una tastiera vera: con il carattere "a capo" il browser preme il pulsante
    browser.send("Input.dispatchKeyEvent", type="keyDown", key="Enter", code="Enter", windowsVirtualKeyCode=13, text=ENTER)
    browser.send("Input.dispatchKeyEvent", type="keyUp", key="Enter", code="Enter", windowsVirtualKeyCode=13)
    status = browser.js("document.querySelector('[data-table-status]').textContent")
    assert card.startswith("Gioca ") and status.startswith("Prova: hai scelto")


def test_indietro_chiude_il_pannello_dopo_un_ricaricamento(browser, server):
    _login(browser, server)
    browser.open(f"{server}/", *PHONE, "document.querySelector('[data-friends-button]') !== null")
    # Come dopo un ricaricamento con la chat aperta: la cronologia ricorda ancora il pannello
    browser.js("history.replaceState({ friendsPanel: 'chat' }, '')")
    browser.send("Page.reload")
    browser.wait_js("document.readyState === 'complete' && document.querySelector('[data-friends-button]') !== null",
                    "pagina ricaricata")
    browser.wait_js("history.state === null || !history.state.friendsPanel", "stato vecchio tolto", 5)
    browser.click("[data-friends-button]")
    assert browser.js("document.getElementById('friends').open") is True
    browser.js("history.back()")
    browser.wait_js("!document.getElementById('friends').open", "pannello chiuso con indietro", 5)
