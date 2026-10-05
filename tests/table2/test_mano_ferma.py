"""P97: le carte della propria mano non "lampeggiano" a ogni vista.

Il tavolo si ridisegna tutto a ogni vista (P70): il pulsante della carta che era sotto
il puntatore nasceva abbassato e si rialzava con la transizione di card.css (0,15 s).
Sul telefono il browser lascia ":hover" sulla carta appena toccata, quindi succedeva
a ogni vista. Ora il sollevamento al passaggio vale solo con un puntatore vero
(@media (hover: hover)) e, da computer, la carta sotto il mouse ridisegnata nasce già
sollevata (card--hover-kept, pages/game.js).

Si controlla, con "riduci movimento" spento, campionando a ogni fotogramma la
posizione delle carte della mano mentre arrivano viste nuove (evento del browser
"demo:state" nella prova /game/prova?demo=1v1). Non serve MySQL. Se né Chrome né Edge
sono installati i controlli nel browser si saltano.
"""

import json
import time
from pathlib import Path

import pytest

from app import create_app
from tests.browser import (
    TEST_COOKIE,
    Browser,
    FakeUser,
    find_browser,
    running_server,
    wait,
)

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "app" / "static"
PHONE = (360, 640)
DESKTOP = (1280, 720)
HAND_CARDS = ".table__mine .hand > .card"

# Registra a ogni fotogramma lo spostamento verticale di ogni carta della mano
SAMPLER = """(() => {
  window.__samples = [];
  const tick = () => {
    const cards = [...document.querySelectorAll('HAND_CARDS')];
    window.__samples.push(cards.map((c) => new DOMMatrix(getComputedStyle(c).transform).m42));
    if (window.__samples.length < 40) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
})()""".replace("HAND_CARDS", HAND_CARDS)


def test_sollevamento_al_passaggio_solo_con_un_puntatore_vero():
    css = (STATIC / "css" / "components" / "card.css").read_text(encoding="utf-8").replace("\r\n", "\n")
    start = css.index("@media (hover: hover) {")
    block = css[start:css.index("}\n}", start)]
    assert "button.card:not(:disabled):hover" in block
    # Fuori dal blocco la regola del passaggio non c'è più
    assert css.count("button.card:not(:disabled):hover") == 1


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


def _open(browser, server, size, touch=False):
    if touch:
        browser.send("Emulation.setTouchEmulationEnabled", enabled=True, maxTouchPoints=5)
    browser.open(f"{server}/game/prova?demo=1v1", *size, "document.querySelector('[data-mode]') !== null")
    browser.send("Emulation.setEmulatedMedia", features=[{"name": "prefers-reduced-motion", "value": "no-preference"}])
    assert browser.js("matchMedia('(hover: hover)').matches") is not touch


def _card_center(browser, index):
    return browser.js(f"""(() => {{
      const b = document.querySelectorAll('{HAND_CARDS}')[{index}].getBoundingClientRect();
      return {{ x: b.left + b.width / 2, y: b.top + b.height / 2 }};
    }})()""")


def _move_mouse(browser, point):
    browser.send("Input.dispatchMouseEvent", type="mouseMoved", x=point["x"], y=point["y"])


def _renders(browser, count):
    """Manda `count` viste nuove e restituisce i campioni di ognuna."""
    view = json.loads((STATIC / "dev" / "vista_1v1.json").read_text(encoding="utf-8"))
    samples = []
    for _ in range(count):
        view["version"] += 1
        browser.js(SAMPLER)
        browser.js("document.querySelector('[data-table]').dispatchEvent("
                   f"new CustomEvent('demo:state', {{ detail: {json.dumps(view)} }}))")
        wait(lambda: browser.js("window.__samples.length") >= 40, 5, "fotogrammi campionati")
        samples.append(browser.js("window.__samples"))
    return samples


def test_carta_sotto_il_mouse_resta_sollevata_a_ogni_vista(browser, server):
    _open(browser, server, DESKTOP)
    last = browser.js(f"document.querySelectorAll('{HAND_CARDS}').length") - 1
    _move_mouse(browser, _card_center(browser, last))
    wait(lambda: browser.js(f"new DOMMatrix(getComputedStyle(document.querySelectorAll('{HAND_CARDS}')[{last}]).transform).m42") < -5,
         3, "carta sollevata dal mouse")
    time.sleep(0.4)  # fine della transizione da 0,15 s
    lifted = browser.js(f"new DOMMatrix(getComputedStyle(document.querySelectorAll('{HAND_CARDS}')[{last}]).transform).m42")
    for frames in _renders(browser, 3):
        for row in frames:
            # La carta sotto il mouse non si abbassa mai, le altre non si muovono
            assert row[last] == pytest.approx(lifted, abs=0.01)
            assert all(y == 0 for y in row[:last])


def test_carta_ridisegnata_si_abbassa_quando_il_mouse_esce(browser, server):
    _open(browser, server, DESKTOP)
    _move_mouse(browser, _card_center(browser, 0))
    _renders(browser, 1)
    assert browser.js("document.querySelectorAll('.card--hover-kept').length") == 1
    _move_mouse(browser, {"x": 640, "y": 300})
    wait(lambda: browser.js(f"new DOMMatrix(getComputedStyle(document.querySelector('{HAND_CARDS}')).transform).m42") == 0,
         3, "carta tornata giù")
    assert browser.js("document.querySelectorAll('.card--hover-kept').length") == 0


def test_sul_telefono_la_carta_toccata_non_si_alza(browser, server):
    _open(browser, server, PHONE, touch=True)
    # Come dopo un tocco: il puntatore resta sopra la carta
    _move_mouse(browser, _card_center(browser, 1))
    time.sleep(0.3)
    for frames in _renders(browser, 2):
        for row in frames:
            assert all(y == 0 for y in row)
