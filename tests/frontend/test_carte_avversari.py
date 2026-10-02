"""P70 (secondo lotto): carte degli avversari dal bordo dello schermo e pescata.

Controlla quanto chiesto dopo la prova sul telefono (SCALETTA.md, P70): le carte
coperte degli avversari sono un ventaglio agganciato al bordo dello schermo dal
loro lato, per metà fuori; quello in alto sta dietro la barra con "Esci" e il
punteggio; i ventagli non coprono avatar e nomi, né presa, mazzo e la tua mano;
dopo una presa ognuno pesca a turno partendo da chi ha preso: la carta arriva nel
ventaglio dell'avversario, o nella tua mano; un ridisegno a metà non fa ripartire
la pescata; con "riduci movimento" niente animazioni.

Il tavolo si apre nella prova (/game/prova?demo=1v1 o 2v2) in Chrome o Edge senza
finestra (tests/browser.py), che apre le pagine con "riduci movimento": per le
animazioni lo si spegne. Le viste arrivano con l'evento del browser "demo:state".
Non serve MySQL. Se né Chrome né Edge sono installati i controlli nel browser si
saltano.
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
SIZES = [(360, 640), (390, 844), (412, 915), (768, 1024), (1280, 720), (1440, 900)]
NEW_CARD = {"suit": "denari", "rank": 2}


def test_durata_della_pescata_uguale_nel_css_e_nella_pagina():
    game = (STATIC / "js" / "pages" / "game.js").read_text(encoding="utf-8")
    css = (STATIC / "css" / "components" / "hand.css").read_text(encoding="utf-8")
    ms = int(re.search(r"const DRAW_MS = (\d+);", game).group(1))
    for name in ("card-draw", "card-room", "card-draw-mine"):
        seconds = float(re.search(rf"animation: {name} ([\d.]+)s", css).group(1))
        assert ms == round(seconds * 1000), name


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


def _view(mode):
    return json.loads((STATIC / "dev" / f"vista_{mode}.json").read_text(encoding="utf-8"))


def _open(browser, server, mode, size=PHONE, motion=False):
    browser.open(f"{server}/game/prova?demo={mode}", *size, "document.querySelector('[data-mode]') !== null")
    if motion:
        browser.send("Emulation.setEmulatedMedia", features=[{"name": "prefers-reduced-motion", "value": "no-preference"}])


def _send_state(browser, view):
    browser.js("document.querySelector('[data-table]').dispatchEvent("
               f"new CustomEvent('demo:state', {{ detail: {json.dumps(view)} }}))")


def _overlap(a, b):
    return a["l"] < b["r"] - 1 and a["r"] > b["l"] + 1 and a["t"] < b["b"] - 1 and a["b"] > b["t"] + 1


RECTS = """(() => {
  const rect = (e) => { const b = e.getBoundingClientRect(); return { l: b.left, t: b.top, r: b.right, b: b.bottom }; };
  const all = (s) => [...document.querySelectorAll(s)].map(rect);
  return {
    fans: [...document.querySelectorAll('[data-edge-hand]')].map((f) => ({
      side: f.dataset.edgeHand, count: Number(f.dataset.count), cards: f.children.length, box: rect(f),
      cardBoxes: [...f.children].map(rect) })),
    seats: all('.table__board > .seat .seat__avatar, .table__board > .seat .seat__label'),
    others: all('[data-trick], [data-deck-count], .table__me, .table__mine .hand'),
    w: innerWidth, h: innerHeight,
    scrollH: document.scrollingElement.scrollHeight, scrollW: document.scrollingElement.scrollWidth,
  };
})()"""


def test_ventaglio_in_alto_dietro_la_barra(browser, server):
    _open(browser, server, "1v1")
    box = browser.js(RECTS)
    assert [(f["side"], f["count"], f["cards"]) for f in box["fans"]] == [("top", 4, 4)]
    fan = box["fans"][0]["box"]
    assert fan["t"] < 0 < fan["b"], "il ventaglio in alto deve uscire per metà dal bordo"
    # Niente più carte coperte sotto il nome
    assert browser.js("document.querySelector('.seat .hand--hidden')") is None
    # La barra sta sopra: al centro del punteggio si tocca il punteggio, non le carte.
    # Da computer: sotto 1024 px il tabellone non c'è (P90)
    _open(browser, server, "1v1", (1280, 720))
    on_top = browser.js("""(() => { const b = document.querySelector('[data-scoreboard]').getBoundingClientRect();
      return document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2).closest('.table__top') !== null; })()""")
    assert on_top is True


def test_ventagli_ai_lati_nel_2v2(browser, server):
    _open(browser, server, "2v2")
    box = browser.js(RECTS)
    sides = {f["side"]: f for f in box["fans"]}
    assert set(sides) == {"left", "top", "right"}
    assert sides["left"]["box"]["l"] < 0 < sides["left"]["box"]["r"]
    assert sides["right"]["box"]["l"] < box["w"] < sides["right"]["box"]["r"]
    view = _view("2v2")
    # Sinistra = posto 3 (5 carte), in alto il compagno (posto 2), destra = posto 1
    assert sides["left"]["count"] == view["players"][3]["cards_in_hand"]
    assert sides["right"]["count"] == view["players"][1]["cards_in_hand"]


@pytest.mark.parametrize("mode", ["1v1", "2v2"])
def test_i_ventagli_non_coprono_niente(browser, server, mode):
    _open(browser, server, mode)
    for size in SIZES:
        browser.send("Emulation.setDeviceMetricsOverride", width=size[0], height=size[1], deviceScaleFactor=1, mobile=False)
        browser.wait_js(f"innerWidth === {size[0]} && innerHeight === {size[1]}", f"schermo {size}", 5)
        box = browser.js(RECTS)
        assert box["scrollH"] <= box["h"] and box["scrollW"] <= box["w"], (mode, size, "il tavolo scorre")
        for fan in box["fans"]:
            for card in fan["cardBoxes"]:
                for part in box["seats"] + box["others"]:
                    assert not _overlap(card, part), (mode, size, fan["side"], card, part)


def _trick_closed_with_draws():
    """1v1: Mario chiude la presa con il 7 di coppe e prende; poi pescano Mario e Turi."""
    base = _view("1v1")
    closed = copy.deepcopy(base)
    closed["version"] += 1
    closed["hand"] = [card for card in base["hand"] if card != {"suit": "coppe", "rank": 7}] + [NEW_CARD]
    closed["players"][0]["cards_in_hand"] = 5
    closed["players"][1]["cards_in_hand"] = 5
    closed["deck_count"] = base["deck_count"] - 2
    closed["last_trick"] = {"winner_seat": 0, "cards": [
        {"seat": 1, "card": {"suit": "coppe", "rank": 3}}, {"seat": 0, "card": {"suit": "coppe", "rank": 7}}]}
    closed["trick"] = {"leader_seat": 0, "cards": []}
    return closed


def _draw_state(browser):
    return browser.js("""(() => {
      const mine = document.querySelector('.table__mine .hand [data-drawn]');
      const fan = document.querySelector('[data-edge-hand="top"]');
      const last = fan.lastElementChild;
      const progress = (e, name) => {
        const a = e && e.getAnimations().find((x) => x.animationName === name);
        return a ? a.effect.getComputedTiming().progress : null; };
      return {
        mine: mine && `${mine.dataset.suit}-${mine.dataset.rank}`,
        mineDelay: mine && parseFloat(mine.style.animationDelay),
        fanDrawing: 'drawing' in fan.dataset,
        lastDrawn: last.classList.contains('card--drawn'),
        lastDelay: parseFloat(last.style.animationDelay),
        roomMaking: [...fan.children].slice(0, -1).every((c) => c.classList.contains('card--making-room')),
        lastProgress: progress(last, 'card-draw'),
      };
    })()""")


def test_pescata_prima_chi_ha_preso_poi_gli_altri(browser, server):
    _open(browser, server, "1v1", motion=True)
    _send_state(browser, _trick_closed_with_draws())
    state = _draw_state(browser)
    assert state["mine"] == "denari-2"            # la tua carta nuova vola nella mano
    assert state["fanDrawing"] and state["lastDrawn"] and state["roomMaking"]
    # Ha preso Mario: pesca per primo, Turi subito dopo (ritardo positivo = tocca dopo)
    assert state["mineDelay"] <= 0 < state["lastDelay"] <= 150
    browser.wait_js("document.querySelector('[data-drawn], [data-drawing]') === null", "pescate finite", 3)
    assert browser.js("document.querySelector('[data-edge-hand=\"top\"]').dataset.count") == "5"


def test_un_ridisegno_a_meta_non_fa_ripartire_la_pescata(browser, server):
    _open(browser, server, "1v1", motion=True)
    _send_state(browser, _trick_closed_with_draws())
    time.sleep(0.35)
    browser.js("document.querySelector('[data-table]').dispatchEvent(new CustomEvent('demo:phrases', "
               "{ detail: { phrases: [{ code: 'ciao', text: 'Ciao!' }] } }))")
    state = _draw_state(browser)
    # Turi ha cominciato a 0,15 s: dopo 0,35 s la sua pescata è avanti, non di nuovo all'inizio
    assert state["lastProgress"] is None or state["lastProgress"] >= 0.2, state
    assert state["lastDelay"] < 0, state


def test_con_riduci_movimento_niente_pescata_animata(browser, server):
    _open(browser, server, "1v1")
    _send_state(browser, _trick_closed_with_draws())
    assert browser.js("document.querySelector('[data-drawn], [data-drawing]')") is None
    assert browser.js("document.querySelector('[data-edge-hand=\"top\"]').dataset.count") == "5"
