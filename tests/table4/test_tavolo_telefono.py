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
nella suite table4 (P121: prima in api, poi in table3; P139: vicine ai 240 s).
"""

import copy
import json
from pathlib import Path

import pytest

from app import create_app
from tests.browser import TEST_COOKIE, Browser, FakeUser, find_browser, running_server
from tests.table_ui import table_path

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "app" / "static"
SMALL = [(320, 568), (360, 640), (390, 844), (412, 915), (768, 1024)]  # P116: niente 844×390 (avviso "Gira il telefono")
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
    browser.open(f"{server}{table_path('prova', demo=mode)}", *size, "document.querySelector('[data-leave]') !== null")
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


# --- P131: nomi lunghi, canto e fumetto insieme ----------------------------------------

LONGEST = "W" * 20  # USERNAME_MAX di config.py, con la lettera più larga

# Coppie di cose che si toccano tra nome, canti, fumetto, carte cantate, "Frasi",
# avatar e i tuoi punti (le cose dello stesso tipo si confrontano solo per i canti)
OVERLAPS = r"""(() => {
  const parts = [['nome', '.seat__name'], ['canti', '.sing-badge'], ['fumetto', '[data-phrase-bubble]'],
    ['cantate', '[data-sang-seat]'], ['frasi', '[data-phrases-button]'], ['avatar', '.seat__avatar .avatar'],
    ['punti', '.table__me-side .hand-points']];
  const boxes = [];
  for (const [name, selector] of parts) {
    for (const node of document.querySelectorAll(selector)) {
      const r = node.getBoundingClientRect();
      if (r.width && r.height) boxes.push({ name, seat: node.closest('[data-seat]')?.dataset.seat ?? '-', r, node });
    }
  }
  const hits = [];
  for (let i = 0; i < boxes.length; i++) {
    for (let j = i + 1; j < boxes.length; j++) {
      const a = boxes[i], b = boxes[j];
      if (a.node.contains(b.node) || b.node.contains(a.node) || (a.name === b.name && a.name !== 'canti')) continue;
      const w = Math.min(a.r.right, b.r.right) - Math.max(a.r.left, b.r.left);
      const h = Math.min(a.r.bottom, b.r.bottom) - Math.max(a.r.top, b.r.top);
      if (w > 0.5 && h > 0.5) hits.push(`${a.name}[${a.seat}] e ${b.name}[${b.seat}]`);
    }
  }
  return { hits, names: boxes.filter((b) => b.name === 'nome').length,
           truncated: [...document.querySelectorAll('.seat__name')].every((n) => n.scrollWidth > n.clientWidth) };
})()"""


def _dispatch(browser, name, detail):
    browser.js(f"document.querySelector('[data-table]').dispatchEvent(new CustomEvent({json.dumps(name)}, "
               f"{{ detail: {json.dumps(detail)} }}))")


@pytest.mark.parametrize("mode", ["1v1", "2v2"])
@pytest.mark.parametrize("width", [360, 375, 390])
def test_nomi_lunghi_canto_e_fumetto_non_si_toccano(browser, server, mode, width):
    # P131: con un nome lungo i tuoi canti finivano sopra "Frasi" e l'avatar sopra i punti;
    # le tue carte cantate stavano sotto il tuo fumetto; il nome in alto sotto il suo fumetto
    view = _crowded(mode)
    for player in view["players"]:
        player["username"] = LONGEST[:-1] + str(player["seat"])
    view["sings"] = [{"seat": 0, "suit": "coppe", "points": 40}, {"seat": 0, "suit": "bastoni", "points": 20},
                     {"seat": 1, "suit": "spade", "points": 20}]
    browser.open(f"{server}{table_path('prova', demo=mode)}", width, 740, "document.querySelector('[data-leave]') !== null")
    _dispatch(browser, "demo:state", view)
    _dispatch(browser, "demo:phrases", {"phrases": [{"code": "bravo", "text": "Bella giocata, complimenti!"}]})
    _dispatch(browser, "demo:sang", {"seat": 0, "suit": "denari", "points": 20, "show_seconds": 30,
                                     "cards": [{"suit": "denari", "rank": 10}, {"suit": "denari", "rank": 9}]})
    for player in view["players"]:
        _dispatch(browser, "demo:phrase", {"seat": player["seat"], "code": "bravo"})
    found = browser.js(OVERLAPS)
    assert found["names"] == len(view["players"])
    assert found["hits"] == []
    assert found["truncated"]  # i nomi si accorciano con i puntini
