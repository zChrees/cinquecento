"""P69: al tavolo, sul telefono, niente zoom con il doppio tocco né con il tocco lungo.

Controlla che nella pagina del tavolo le regole di css/pages/game.css siano davvero
attive nel browser: il doppio tocco non ingrandisce (touch-action: manipulation, lo
zoom con due dita resta), il testo non si seleziona tenendo premuto, e le immagini
delle carte non ricevono il tocco (niente anteprima o menù "apri immagine"), che va
al pulsante della carta. L'anteprima di iPhone (-webkit-touch-callout) Chrome non la
conosce: si controlla che la regola sia nel file.

Il tavolo si apre nella prova (/game/prova?demo=1v1) in Chrome o Edge senza finestra
(tests/browser.py). Non serve MySQL. Se né Chrome né Edge sono installati i controlli
nel browser si saltano.
"""

from pathlib import Path

import pytest

from app import create_app
from tests.browser import TEST_COOKIE, Browser, FakeUser, find_browser, running_server

ROOT = Path(__file__).resolve().parents[2]
GAME_CSS = ROOT / "app" / "static" / "css" / "pages" / "game.css"
PHONE = (360, 640)


def test_regole_nel_css_del_tavolo():
    css = GAME_CSS.read_text(encoding="utf-8")
    start = css.index(":root:has(.page--game) {")
    block = css[start:css.index("}", start)]
    for rule in ("touch-action: manipulation;", "-webkit-touch-callout: none;", "user-select: none;"):
        assert rule in block, rule
    # Lo zoom con due dita resta: nessuna regola lo spegne
    assert "user-scalable" not in (ROOT / "app" / "templates" / "base.html").read_text(encoding="utf-8")
    assert "pinch-zoom" not in css


@pytest.fixture(scope="module")
def server():
    with running_server(create_app("testing"), FakeUser("Mario", 12)) as url:
        yield url


@pytest.fixture
def browser(server, tmp_path):
    b = Browser(find_browser(), tmp_path / "chrome")
    b.send("Network.setCookie", name=TEST_COOKIE[0], value=TEST_COOKIE[1], url=server)
    yield b
    b.close()


def test_tavolo_senza_zoom_e_senza_selezione(browser, server):
    browser.open(f"{server}/game/prova?demo=1v1", *PHONE, "document.querySelector('[data-mode]') !== null")
    styles = browser.js("""(() => {
      const root = getComputedStyle(document.documentElement);
      const face = document.querySelector('.table__mine .hand .card__face');
      const b = face.getBoundingClientRect();
      const hit = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);
      return {
        touch: root.touchAction,
        select: getComputedStyle(document.querySelector('.seat__name')).userSelect,
        facePointer: getComputedStyle(face).pointerEvents,
        hitIsCardButton: hit !== null && hit.matches('button.card'),
      };
    })()""")
    assert styles == {"touch": "manipulation", "select": "none", "facePointer": "none", "hitIsCardButton": True}


def test_regole_solo_al_tavolo(browser, server):
    # La regola dipende dalla classe del tavolo: senza, la pagina torna come le altre
    browser.open(f"{server}/game/prova?demo=1v1", *PHONE, "document.querySelector('[data-mode]') !== null")
    browser.js("document.querySelector('main').classList.remove('page--game')")
    assert browser.js("getComputedStyle(document.documentElement).touchAction") == "auto"


def test_ogni_elemento_del_tavolo_ha_la_regola(browser, server):
    # P98: touch-action non si eredita e Safari su iPhone guarda l'elemento toccato:
    # la regola deve stare su ogni elemento, anche fuori da <main>
    browser.open(f"{server}/game/prova?demo=1v1", *PHONE, "document.querySelector('[data-mode]') !== null")
    result = browser.js("""(() => {
      const extra = document.body.appendChild(document.createElement('div'));
      const all = [...document.body.querySelectorAll('*')];
      const wrong = all.filter((e) => getComputedStyle(e).touchAction !== 'manipulation');
      extra.remove();
      return { count: all.length, wrong: wrong.map((e) => e.tagName + '.' + e.className).slice(0, 5) };
    })()""")
    assert result["count"] > 50
    assert result["wrong"] == []


def test_regola_su_ogni_elemento_solo_al_tavolo(browser, server):
    browser.open(f"{server}/game/prova?demo=1v1", *PHONE, "document.querySelector('[data-mode]') !== null")
    browser.js("document.querySelector('main').classList.remove('page--game')")
    assert browser.js("getComputedStyle(document.querySelector('.card')).touchAction") == "auto"
