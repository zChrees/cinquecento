"""P110: l'elenco delle frasi aperto non lampeggia quando il tavolo si ridisegna.

Il tavolo si ridisegna tutto a ogni vista e durante le animazioni (lancio, pescate:
P70, P78): l'elenco delle frasi, ricreato, faceva ripartire la sua animazione di
entrata (phrases-in sul telefono, phrases-side-in da computer, che partono da
opacity 0), e lampeggiava più volte mentre un avversario lanciava una carta.

Il tavolo si apre nella prova (/game/prova?demo=1v1) in Chrome o Edge senza finestra
(tests/browser.py), con "riduci movimento" spento; le viste arrivano con "demo:state"
e l'elenco con "demo:phrases". Non serve MySQL.
"""

import copy
import json
import time
from pathlib import Path

import pytest

from app import create_app
from app.realtime import table_phrases
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
PHRASES = table_phrases.phrases_event()

# Conta le entrate dell'elenco che ripartono da capo e la sua opacità più bassa. Un
# elenco ridisegnato manda anche lui "animationstart", ma con il ritardo negativo
# (P110) elapsedTime è già alla fine dell'entrata (0,18 s): non è una ripartenza
WATCH = """(() => {
  window.__menu = { starts: 0, minOpacity: 1 };
  document.addEventListener('animationstart', (e) => {
    if (e.animationName.startsWith('phrases') && e.elapsedTime < 0.15) window.__menu.starts += 1;
  });
  const sample = () => {
    const menu = document.querySelector('[data-phrases-menu]');
    if (menu) window.__menu.minOpacity = Math.min(window.__menu.minOpacity, Number(getComputedStyle(menu).opacity));
    requestAnimationFrame(sample);
  };
  requestAnimationFrame(sample);
})()"""


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


def _dispatch(browser, name, detail):
    browser.js(f"document.querySelector('[data-table]').dispatchEvent(new CustomEvent({json.dumps(name)}, "
               f"{{ detail: {json.dumps(detail)} }}))")


def _waiting():
    """Tocca a Turi (posto 1), che apre la presa: Mario aspetta."""
    view = json.loads((STATIC / "dev" / "vista_1v1.json").read_text(encoding="utf-8"))
    view["version"] += 1
    view["trick"] = {"leader_seat": 1, "cards": [], "winning_seat": None}
    view["players"][1]["cards_in_hand"] = 5
    view["turn"] = {**view["turn"], "seat": 1}
    view["legal"] = {"play": [], "sing": [], "lay_down": False}
    return view


def _turi_plays(base):
    view = copy.deepcopy(base)
    view["version"] += 1
    view["trick"] = {"leader_seat": 1, "cards": [{"seat": 1, "card": {"suit": "coppe", "rank": 3}}], "winning_seat": 1}
    view["players"][1]["cards_in_hand"] = 4
    view["turn"] = {**base["turn"], "seat": 0}
    return view


@pytest.mark.parametrize("size", [(360, 640), (1280, 720)], ids=["telefono", "computer"])
def test_lancio_dell_avversario_con_le_frasi_aperte(browser, server, size):
    browser.open(f"{server}/game/prova?demo=1v1", *size, "document.querySelector('[data-mode]') !== null")
    browser.send("Emulation.setEmulatedMedia", features=[{"name": "prefers-reduced-motion", "value": "no-preference"}])
    _dispatch(browser, "demo:phrases", PHRASES)
    base = _waiting()
    _dispatch(browser, "demo:state", base)
    browser.js(WATCH)
    browser.click("[data-phrases-button]")
    browser.wait_js("document.querySelector('[data-phrases-menu]') !== null", "elenco aperto", 3)
    time.sleep(0.5)  # l'entrata (0,18 s) è finita
    assert browser.js("window.__menu.starts") == 1  # all'apertura l'entrata c'è
    browser.js("window.__menu = { starts: 0, minOpacity: 1 }")
    _dispatch(browser, "demo:state", _turi_plays(base))
    wait(lambda: browser.js("document.querySelector('.card--thrown') !== null"), 3, "carta lanciata")
    time.sleep(1.2)  # lancio (0,4 s) e ridisegni di fine animazione
    menu = browser.js("window.__menu")
    assert browser.js("document.querySelector('[data-phrases-menu]') !== null"), "l'elenco si è chiuso"
    assert menu == {"starts": 0, "minOpacity": 1}, menu


def test_elenco_fatto_scorrere_resta_dov_era(browser, server):
    # Sul telefono l'elenco scorre (P101): un ridisegno non lo riporta in cima
    browser.open(f"{server}/game/prova?demo=1v1", 360, 640, "document.querySelector('[data-mode]') !== null")
    browser.send("Emulation.setEmulatedMedia", features=[{"name": "prefers-reduced-motion", "value": "no-preference"}])
    _dispatch(browser, "demo:phrases", PHRASES)
    base = _waiting()
    _dispatch(browser, "demo:state", base)
    browser.click("[data-phrases-button]")
    browser.wait_js("document.querySelector('[data-phrases-menu]') !== null", "elenco aperto", 3)
    sizes = browser.js("""(() => { const m = document.querySelector('[data-phrases-menu]'); m.scrollTop = 60;
      return { scroll: m.scrollHeight, client: m.clientHeight, top: m.scrollTop }; })()""")
    assert sizes["scroll"] > sizes["client"] and sizes["top"] == 60, sizes  # l'elenco scorre davvero
    _dispatch(browser, "demo:state", _turi_plays(base))
    wait(lambda: browser.js("document.querySelector('.card--thrown') !== null"), 3, "carta lanciata")
    time.sleep(1.2)
    assert browser.js("document.querySelector('[data-phrases-menu]').scrollTop") == 60


FRAMES = """(() => {
  window.__frames = [];
  const start = performance.now();
  const tick = () => {
    const menu = document.querySelector('[data-phrases-menu]');
    if (menu) {
      const r = menu.getBoundingClientRect();
      window.__frames.push({ top: Math.round(r.top), bottom: Math.round(r.bottom),
                             transform: getComputedStyle(menu).transform });
    }
    if (performance.now() - start < 800) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
})()"""


@pytest.mark.parametrize("mode", ["1v1", "2v2"])
def test_sul_telefono_l_elenco_si_apre_al_suo_posto_e_non_si_muove(browser, server, mode):
    # P112: su iPhone l'elenco compariva più in alto, sopra la tua riga, e poi scendeva
    browser.open(f"{server}/game/prova?demo={mode}", 390, 844, "document.querySelector('[data-mode]') !== null")
    browser.send("Emulation.setEmulatedMedia", features=[{"name": "prefers-reduced-motion", "value": "no-preference"}])
    _dispatch(browser, "demo:phrases", PHRASES)
    row = browser.js("document.querySelector('.table__me').getBoundingClientRect().bottom")
    browser.js(FRAMES)
    browser.click("[data-phrases-button]")
    time.sleep(1)
    frames = browser.js("window.__frames")
    assert frames, "elenco non aperto"
    assert {f["top"] for f in frames} == {frames[0]["top"]}, frames  # mai uno spostamento
    assert {f["transform"] for f in frames} == {"none"}, frames  # entrata senza movimento
    assert row < frames[0]["top"] <= row + 10, (row, frames[0])  # subito sotto la tua riga
    assert frames[0]["bottom"] <= 844
