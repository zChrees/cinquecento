"""P90: tavolo sul telefono, niente tabellone e "Esci" che non si sovrappone.

Sotto 1024 px il tabellone in alto non c'è (il punteggio della partita si legge nel
riepilogo di fine mano) ed "Esci" è un tondo con la sola icona, con la scritta solo
per i lettori di schermo: così non arriva mai alle carte coperte dell'avversario in
alto. Prima di P90, a 360 px e con 5 carte all'avversario, tra "Esci" e il ventaglio
restavano 7 px, e a 320 px "Esci" copriva una carta.

I rettangoli si misurano alle misure di LEGGIMI.md (più 320×568), nel 1v1 e nel 2v2,
con 5 carte agli avversari e nomi lunghi: tra "Esci" e il ventaglio restano almeno
24 px, un margine anche per il carattere più grande del telefono. Il tavolo
si apre nella prova (/game/prova?demo=…) in Chrome o Edge senza finestra
(tests/browser.py); le viste arrivano con l'evento del browser "demo:state". Non
serve MySQL. Se né Chrome né Edge sono installati i controlli si saltano. Il file sta
nella suite api perché la suite frontend è vicina ai 240 s.
"""

import copy
import json
from pathlib import Path

import pytest

from app import create_app
from tests.browser import TEST_COOKIE, Browser, FakeUser, find_browser, running_server

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "app" / "static"
SMALL = [(320, 568), (360, 640), (390, 844), (412, 915), (768, 1024), (844, 390)]
NAMES = ["Christian", "Giuseppe", "Salvatore", "Rosalia"]

# Elementi visibili (immagini, pulsanti, testi) che toccano il rettangolo di "Esci"
TOUCHING_LEAVE = r"""(() => {
  const button = document.querySelector('[data-leave]');
  const leave = button.getBoundingClientRect();
  const hit = [];
  for (const e of document.querySelectorAll('body *')) {
    if (button.contains(e) || e.contains(button)) continue;
    const style = getComputedStyle(e);
    if (style.visibility === 'hidden' || style.display === 'none') continue;
    const leaf = e.tagName === 'IMG' || e.tagName === 'BUTTON'
      || [...e.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim());
    if (!leaf) continue;
    const r = e.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    if (r.left < leave.right && r.right > leave.left && r.top < leave.bottom && r.bottom > leave.top) {
      hit.push(`${e.tagName}.${e.className}`);
    }
  }
  return hit;
})()"""

# Distanza in px tra "Esci" e la carta più vicina del ventaglio in alto (null se non c'è)
GAP_TO_TOP_FAN = r"""(() => {
  const leave = document.querySelector('[data-leave]').getBoundingClientRect();
  const cards = [...document.querySelectorAll('[data-edge-hand="top"] .card')];
  if (!cards.length) return null;
  return Math.min(...cards.map((c) => {
    const r = c.getBoundingClientRect();
    const dx = Math.max(r.left - leave.right, leave.left - r.right, 0);
    const dy = Math.max(r.top - leave.bottom, leave.top - r.bottom, 0);
    return Math.max(dx, dy);
  }));
})()"""


@pytest.fixture(scope="module")
def server():
    with running_server(create_app("testing"), FakeUser("Mario", 12)) as url:
        yield url


@pytest.fixture(scope="module")
def browser(server, tmp_path_factory):
    b = Browser(find_browser(), tmp_path_factory.mktemp("chrome"))
    b.send("Network.setCookie", name=TEST_COOKIE[0], value=TEST_COOKIE[1], url=server)
    yield b
    b.close()


def _view(mode):
    return json.loads((STATIC / "dev" / f"vista_{mode}.json").read_text(encoding="utf-8"))


def _crowded(mode):
    """La vista di prova con 5 carte a ogni avversario e nomi lunghi."""
    view = _view(mode)
    view["version"] += 1
    for i, player in enumerate(view["players"]):
        player["username"] = NAMES[i]
        if player["seat"] != view["you"]["seat"]:
            player["cards_in_hand"] = 5
    return view


def _open(browser, server, mode, size):
    browser.open(f"{server}/game/prova?demo={mode}", *size, "document.querySelector('[data-leave]') !== null")
    browser.js("document.querySelector('[data-table]').dispatchEvent("
               f"new CustomEvent('demo:state', {{ detail: {json.dumps(_crowded(mode))} }}))")


def _leave(browser):
    return browser.js("""(() => { const b = document.querySelector('[data-leave]');
      const r = b.getBoundingClientRect(); const t = b.querySelector('.table__leave-text').getBoundingClientRect();
      return { width: r.width, height: r.height, text: b.textContent.replace('logout', '').trim(), textWidth: t.width }; })()""")


def _scoreboard_shown(browser):
    return browser.js("document.querySelector('[data-scoreboard]').getClientRects().length > 0")


@pytest.mark.parametrize("mode", ["1v1", "2v2"])
@pytest.mark.parametrize("size", SMALL, ids=lambda s: f"{s[0]}x{s[1]}")
def test_sotto_1024_niente_tabellone_e_esci_libero(browser, server, mode, size):
    _open(browser, server, mode, size)
    assert _scoreboard_shown(browser) is False
    leave = _leave(browser)
    assert leave["width"] <= 48 and leave["height"] >= 44   # tondo, comodo da toccare
    assert leave["text"] == "Esci" and leave["textWidth"] <= 1   # la scritta c'è, ma solo per i lettori di schermo
    assert browser.js(TOUCHING_LEAVE) == []
    gap = browser.js(GAP_TO_TOP_FAN)
    if gap is not None:
        assert gap >= 24


@pytest.mark.parametrize("mode", ["1v1", "2v2"])
def test_da_computer_tabellone_e_scritta_esci(browser, server, mode):
    _open(browser, server, mode, (1280, 720))
    assert _scoreboard_shown(browser) is True
    leave = _leave(browser)
    assert leave["textWidth"] > 1 and leave["width"] > 60


def test_il_riepilogo_mostra_il_punteggio_sul_telefono(browser, server):
    _open(browser, server, "1v1", (360, 640))
    view = copy.deepcopy(_crowded("1v1"))
    view["version"] += 1
    view["hand_number"] += 1
    view["last_trick"] = None
    view["trick"] = {"leader_seat": 0, "cards": []}
    view["last_hand"] = {"hand_number": view["hand_number"] - 1, "teams": [
        {"team": 0, "card_points": 48, "sing_points": 20, "hand_total": 68},
        {"team": 1, "card_points": 72, "sing_points": 40, "hand_total": 112}]}
    view["scores"] = [{"team": 0, "total": 273}, {"team": 1, "total": 247}]
    browser.js("document.querySelector('[data-table]').dispatchEvent("
               f"new CustomEvent('demo:state', {{ detail: {json.dumps(view)} }}))")
    browser.wait_js("document.querySelector('[data-hand-summary]') !== null", "riepilogo di fine mano")
    total = browser.js("""(() => { const row = document.querySelector('[data-hand-summary] .hand-summary__total');
      return row && row.getClientRects().length > 0 ? row.textContent : null; })()""")
    assert total is not None and "273" in total and "247" in total
