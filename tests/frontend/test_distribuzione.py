"""P70 (terzo lotto): mescolata e distribuzione a inizio mano.

Controlla quanto chiesto dopo la prova sul telefono (SCALETTA.md, P70) e deciso da
Christian: a ogni mano nuova le carte restano nascoste finché si vedono l'ultima
presa e il riepilogo; poi il mazzo si mescola e le carte partono una alla volta, a
giro dal giocatore dopo il mazziere; fino alla fine un tocco sulle proprie carte non
gioca niente; un ridisegno a metà non fa ripartire l'animazione; alla prima vista e
con "riduci movimento" niente distribuzione.

Il tavolo si apre nella prova (/game/prova?demo=1v1) in Chrome o Edge senza finestra
(tests/browser.py), che apre le pagine con "riduci movimento": per le animazioni lo
si spegne. Le viste arrivano con l'evento del browser "demo:state". Non serve MySQL.
Se né Chrome né Edge sono installati i controlli nel browser si saltano.
"""

import copy
import json
import re
import time
from pathlib import Path

import pytest

from app import create_app
from tests.browser import TEST_COOKIE, Browser, FakeUser, find_browser, running_server

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "app" / "static"
PHONE = (360, 640)
CLOSING = {"winner_seat": 1, "cards": [
    {"seat": 0, "card": {"suit": "spade", "rank": 4}}, {"seat": 1, "card": {"suit": "spade", "rank": 1}}]}


def test_durata_della_mescolata_uguale_nel_css_e_nella_pagina():
    game = (STATIC / "js" / "pages" / "game.js").read_text(encoding="utf-8")
    css = (STATIC / "css" / "components" / "trick.css").read_text(encoding="utf-8")
    ms = int(re.search(r"const SHUFFLE_MS = (\d+);", game).group(1))
    seconds = float(re.search(r"animation: deck-riffle ([\d.]+)s", css).group(1))
    assert ms == round(seconds * 1000)


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


def _open(browser, server, motion=True):
    browser.open(f"{server}/game/prova?demo=1v1", *PHONE, "document.querySelector('[data-mode]') !== null")
    if motion:
        browser.send("Emulation.setEmulatedMedia", features=[{"name": "prefers-reduced-motion", "value": "no-preference"}])


def _send_state(browser, view):
    browser.js("document.querySelector('[data-table]').dispatchEvent("
               f"new CustomEvent('demo:state', {{ detail: {json.dumps(view)} }}))")


def _status(browser):
    return browser.js("document.querySelector('[data-table-status]').textContent")


def _real_click(browser, selector):
    point = browser.js(f"""(() => {{
      const b = document.querySelector({json.dumps(selector)}).getBoundingClientRect();
      return {{ x: b.left + b.width / 2, y: b.top + b.height / 2 }};
    }})()""")
    for kind in ("mousePressed", "mouseReleased"):
        browser.send("Input.dispatchMouseEvent", type=kind, x=point["x"], y=point["y"], button="left", clickCount=1)


def _new_hand():
    """Mano 4 del 1v1: tocca a Mario, 5 carte a testa; la mano 3 l'ha chiusa Turi.
    Il mazziere è Mario (posto 0), quindi la prima carta va a Turi."""
    base = json.loads((STATIC / "dev" / "vista_1v1.json").read_text(encoding="utf-8"))
    view = copy.deepcopy(base)
    view["version"] += 1
    view["hand_number"] = 4
    view["dealer_seat"] = 0
    view["players"][1]["cards_in_hand"] = 5
    view["deck_count"] = 30
    view["trick"] = {"leader_seat": 0, "cards": []}
    view["last_trick"] = None
    view["sings"] = []
    view["trump"] = None
    view["last_hand"] = {"hand_number": 3, "last_trick": CLOSING, "teams": [
        {"team": 0, "card_points": 48, "sing_points": 20, "hand_total": 68},
        {"team": 1, "card_points": 72, "sing_points": 40, "hand_total": 112}]}
    return view


DEAL = """(() => {
  const hand = [...document.querySelectorAll('.table__mine .hand > .card')];
  const fan = document.querySelector('[data-edge-hand="top"]');
  return {
    mineDealt: hand.filter((c) => 'dealt' in c.dataset).length,
    mineVisible: hand.filter((c) => getComputedStyle(c).opacity !== '0').length,
    fanDealing: 'dealing' in fan.dataset,
    fanVisible: [...fan.children].filter((c) => getComputedStyle(c).opacity !== '0').length,
    shuffling: document.querySelector('[data-shuffling]') !== null,
    mineDelays: hand.map((c) => parseFloat(c.style.animationDelay)),
    fanDelays: [...fan.children].map((c) => parseFloat(c.style.animationDelay)),
  };
})()"""


def test_carte_nascoste_fino_alla_fine_del_riepilogo(browser, server):
    _open(browser, server)
    _send_state(browser, _new_hand())
    state = browser.js(DEAL)
    assert state["mineDealt"] == 5 and state["fanDealing"]
    assert state["mineVisible"] == 0 and state["fanVisible"] == 0
    assert not state["shuffling"]
    browser.wait_js("document.querySelector('[data-hand-summary]') !== null", "riepilogo", 6)
    assert browser.js(DEAL)["mineVisible"] == 0


def test_mescolata_poi_una_carta_alla_volta_dal_giocatore_dopo_il_mazziere(browser, server):
    _open(browser, server)
    _send_state(browser, _new_hand())
    browser.wait_js("document.querySelector('[data-hand-summary-close]') !== null", "riepilogo", 6)
    _real_click(browser, "[data-hand-summary-close]")
    state = browser.js(DEAL)
    assert state["shuffling"]
    # La prima carta va a Turi (dopo il mazziere Mario), poi a Mario, e così via: 80 ms l'una dall'altra
    turi, mario = state["fanDelays"], state["mineDelays"]
    assert abs((mario[0] - turi[0]) - 80) <= 2
    assert abs((turi[1] - mario[0]) - 80) <= 2
    assert abs((mario[4] - turi[0]) - 80 * 9) <= 2
    # Durante la distribuzione un tocco sulle proprie carte non gioca niente
    browser.wait_js("getComputedStyle(document.querySelector('.table__mine .hand > .card')).opacity === '1'",
                    "prima carta arrivata", 3)
    _real_click(browser, ".table__mine .hand > .card")
    assert _status(browser) == ""
    browser.wait_js("document.querySelector('[data-dealt], [data-dealing], [data-shuffling]') === null",
                    "distribuzione finita", 4)
    _real_click(browser, ".table__mine .hand > .card")
    assert _status(browser).startswith("Prova: hai scelto")


def test_un_ridisegno_a_meta_non_fa_ripartire_la_mescolata(browser, server):
    _open(browser, server)
    _send_state(browser, _new_hand())
    browser.wait_js("document.querySelector('[data-hand-summary-close]') !== null", "riepilogo", 6)
    _real_click(browser, "[data-hand-summary-close]")
    time.sleep(0.3)
    browser.js("document.querySelector('[data-table]').dispatchEvent(new CustomEvent('demo:phrases', "
               "{ detail: { phrases: [{ code: 'ciao', text: 'Ciao!' }] } }))")
    progress = browser.js("""(() => {
      const half = document.querySelector('.deck__half');
      const a = half && half.getAnimations().find((x) => x.animationName === 'deck-riffle');
      return a ? a.effect.getComputedTiming().progress : null; })()""")
    # Dopo 0,3 s su 0,6 la mescolata è almeno a un terzo, non di nuovo all'inizio
    assert progress is None or progress >= 0.3, progress


def test_alla_prima_vista_niente_distribuzione(browser, server):
    _open(browser, server)
    assert browser.js("document.querySelector('[data-dealt], [data-dealing], [data-shuffling]')") is None


def test_con_riduci_movimento_niente_distribuzione(browser, server):
    _open(browser, server, motion=False)
    _send_state(browser, _new_hand())
    assert browser.js("document.querySelector('[data-dealt], [data-dealing], [data-shuffling]')") is None
    assert browser.js(DEAL)["mineVisible"] == 5
