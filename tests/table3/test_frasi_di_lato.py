"""P80: da computer le frasi del tavolo si aprono in un pannello sul lato destro.

Controlla il "Fatto quando" di SCALETTA.md (P80): a 1280×720 e 1440×900 (e da
1024 px), con l'elenco aperto, la presa, il mazzo, la tua mano e le carte degli
avversari restano visibili e cliccabili; per scelta di Christian, nel 2v2 il
pannello copre solo l'avversario di destra mentre è aperto. Il pannello sta sul
bordo destro, sotto il tabellone e sopra la tua riga; le frasi che non ci stanno
scorrono al suo interno. Sul telefono non cambia niente (test_grafica_tavolo.py,
test_elenco_delle_frasi_verso_l_alto).

Il tavolo si apre nella prova (/game/prova?demo=1v1 o 2v2) in Chrome o Edge senza
finestra (tests/browser.py), con le frasi mandate con l'evento "demo:phrases".
Non serve MySQL.
"""

import json

import pytest

from app import create_app
from app.realtime import table_phrases
from tests.browser import TEST_COOKIE, Browser, FakeUser, find_browser, running_server

PARTS = r"""(() => {
  const R = (s) => [...document.querySelectorAll(s)].map((e) => {
    const b = e.getBoundingClientRect(); return { l: b.left, t: b.top, r: b.right, b: b.bottom }; });
  const parts = {
    trick: R('[data-trick] .card'), deck: R('[data-deck-count] .card'), deckCount: R('.deck__count'), hand: R('.table__mine .hand > .card'),
    mine: R('.table__mine'), scoreboard: R('[data-scoreboard]'), leave: R('[data-leave]'),
    button: R('[data-phrases-button]'), sing: R('[data-sing-button]'), points: R('.table__me-side [data-hand-points]'),
  };
  for (const fan of document.querySelectorAll('[data-edge-hand]')) {
    parts[`fan-${fan.dataset.edgeHand}`] = R(`[data-edge-hand="${fan.dataset.edgeHand}"] > .card`);
  }
  for (const seat of document.querySelectorAll('.seat')) parts[`seat-${seat.dataset.position}`] = R(`.seat[data-seat="${seat.dataset.seat}"]`);
  const menu = document.querySelector('[data-phrases-menu]');
  const m = menu.getBoundingClientRect();
  return { parts, menu: { l: m.left, t: m.top, r: m.right, b: m.bottom },
           scrolls: menu.scrollHeight > menu.clientHeight, overflow: getComputedStyle(menu).overflowY,
           phrases: menu.querySelectorAll('[data-phrase-code]').length, w: innerWidth, h: innerHeight,
           pageScroll: document.scrollingElement.scrollHeight > innerHeight };
})()"""

# Cosa c'è sotto il centro di ogni carta: deve essere la carta, non il pannello
HIT = r"""((selector) => [...document.querySelectorAll(selector)].every((c) => {
  const b = c.getBoundingClientRect(); const hit = document.elementFromPoint((b.left + b.right) / 2, (b.top + b.bottom) / 2);
  return hit !== null && !hit.closest('[data-phrases-menu]');
}))"""


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


def _overlap(a, b):
    return a["l"] < b["r"] and a["r"] > b["l"] and a["t"] < b["b"] and a["b"] > b["t"]


def _open_menu(browser, server, mode, size):
    browser.open(f"{server}/game/prova?demo={mode}", *size, "document.querySelector('[data-mode]') !== null")
    browser.js(f"document.querySelector('[data-table]').dispatchEvent(new CustomEvent('demo:phrases', "
               f"{{ detail: {json.dumps(table_phrases.phrases_event())} }}))")
    browser.click("[data-phrases-button]")
    browser.wait_js("document.querySelector('[data-phrases-menu]') !== null", "elenco delle frasi", 5)


@pytest.mark.parametrize("mode", ["1v1", "2v2"])
@pytest.mark.parametrize("size", [(1024, 768), (1280, 720), (1440, 900)], ids=lambda s: f"{s[0]}x{s[1]}")
def test_da_computer_le_frasi_in_un_pannello_a_destra(browser, server, mode, size):
    _open_menu(browser, server, mode, size)
    box = browser.js(PARTS)
    menu, parts, w = box["menu"], box["parts"], box["w"]
    assert not box["pageScroll"]

    # Sul bordo destro, sotto il tabellone e sopra la tua riga, alto almeno metà schermo
    assert menu["r"] >= w - 100 and menu["l"] >= w / 2, menu
    assert menu["t"] >= parts["scoreboard"][0]["b"]
    assert menu["b"] <= parts["mine"][0]["t"]
    assert menu["b"] - menu["t"] >= box["h"] / 2 - 40

    # Tutte le frasi, e quelle che non ci stanno scorrono dentro il pannello
    assert box["phrases"] == len(table_phrases.phrases_event()["phrases"])
    assert box["overflow"] == "auto"

    # Niente di quello che serve per giocare sta sotto il pannello
    # P100: nel 1v1 il mazzo sta sotto "Frasi" e il pannello aperto lo copre (scelta di
    # Christian del 05/10/2026: la briscola resta nel tondo in alto, P102)
    covered_ok = {"seat-right", "fan-right"} if mode == "2v2" else {"deck", "deckCount"}
    for name, rects in parts.items():
        if name in covered_ok:
            continue
        for rect in rects:
            assert not _overlap(menu, rect), (mode, size, f"il pannello copre {name}")
    visible = ["[data-trick] .card", ".table__mine .hand > .card", '[data-edge-hand="top"] > .card']
    if mode == "2v2":
        visible.append("[data-deck-count] .card")  # nel 1v1 il pannello copre il mazzo (P100)
    for selector in visible:
        assert browser.js(f"{HIT}({json.dumps(selector)})"), (mode, size, f"{selector} non si può cliccare")


def test_una_frase_chiude_il_pannello(browser, server):
    _open_menu(browser, server, "2v2", (1280, 720))
    browser.click("[data-phrases-menu] [data-phrase-code]")
    browser.wait_js("document.querySelector('[data-phrases-menu]') === null", "pannello chiuso", 5)
