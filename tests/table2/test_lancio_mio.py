"""P99: il lancio della propria carta, più realistico; P107: anche quello degli avversari.

La tua carta parte dal suo posto nella mano, si solleva, vola ad arco verso il centro
girando un po' e si posa con un piccolo assestamento, in 0,55 s (MY_THROW_MS di
game.js, card-throw-mine di trick.css); le carte degli avversari restano come prima
(card-throw, 0,4 s). Il server (P94) continua a usare 0,4 s per la sua pausa: scelta di
Christian del 05/10/2026 (al massimo 0,15 s di differenza quando chiudi tu la presa).
P107: la carta di un avversario fa lo stesso movimento in 0,4 s, partendo dal suo
ventaglio coperto (grande come le sue carte e girata come il ventaglio).

Il tavolo si apre nella prova (/game/prova?demo=1v1) in Chrome o Edge senza finestra,
con "riduci movimento" spento; le viste arrivano con l'evento del browser
"demo:state". Per guardare il volo a un tempo preciso i timer della pagina si fermano
(niente ridisegno a fine lancio) e l'animazione si mette in pausa. Non serve MySQL.
"""

import copy
import json
import re
from pathlib import Path

import pytest

from app import create_app
from tests.browser import TEST_COOKIE, Browser, FakeUser, find_browser, running_server

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "app" / "static"
GAME = (STATIC / "js" / "pages" / "game.js").read_text(encoding="utf-8")
TRICK_CSS = (STATIC / "css" / "components" / "trick.css").read_text(encoding="utf-8")
MY_THROW_MS = int(re.search(r"const MY_THROW_MS = (\d+);", GAME).group(1))
THROW_MS = int(re.search(r"const THROW_MS = (\d+);", GAME).group(1))
SIZES = [(360, 640), (1280, 720)]

MY_CARD = ".trick__card--bottom > [data-thrown]"


def test_durata_del_tuo_lancio_uguale_nel_css_e_nella_pagina():
    rule = TRICK_CSS[TRICK_CSS.index(".trick__card--bottom > .card--thrown {"):]
    seconds = float(re.search(r"animation-duration: ([\d.]+)s", rule[:rule.index("}")]).group(1))
    assert MY_THROW_MS == round(seconds * 1000)
    # Più lento di quello degli avversari, ma non tanto da rallentare il turno da 15 s
    assert THROW_MS < MY_THROW_MS <= 600


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


def _views(index):
    """Una vista con la presa vuota e quella dopo che Mario (posto 0) apre con la carta `index`."""
    base = json.loads((STATIC / "dev" / "vista_1v1.json").read_text(encoding="utf-8"))
    base["version"] += 1
    base["trick"] = {"leader_seat": 0, "cards": [], "winning_seat": None}
    card = base["hand"][index]
    played = copy.deepcopy(base)
    played["version"] += 1
    played["hand"] = [c for c in base["hand"] if c != card]
    played["trick"] = {"leader_seat": 0, "cards": [{"seat": 0, "card": card}], "winning_seat": 0}
    played["turn"]["seat"] = 1
    return base, played, card


def _send(browser, view):
    browser.js("document.querySelector('[data-table]').dispatchEvent("
               f"new CustomEvent('demo:state', {{ detail: {json.dumps(view)} }}))")


def _open(browser, server, size):
    browser.open(f"{server}/game/prova?demo=1v1", *size, "document.querySelector('[data-mode]') !== null")
    browser.send("Emulation.setEmulatedMedia", features=[{"name": "prefers-reduced-motion", "value": "no-preference"}])


def _rect(browser, selector):
    return browser.js(f"""(() => {{
      const b = document.querySelector({json.dumps(selector)}).getBoundingClientRect();
      return {{ x: b.left + b.width / 2, y: b.top + b.height / 2, w: b.width }};
    }})()""")


def _at(browser, ms):
    """Rettangolo della tua carta in volo a `ms` dall'inizio del lancio."""
    browser.js(f"document.querySelector('{MY_CARD}').getAnimations().forEach((a) => {{ a.pause(); a.currentTime = {ms} + a.effect.getTiming().delay; }})")
    return _rect(browser, MY_CARD)


@pytest.mark.parametrize("size", SIZES)
@pytest.mark.parametrize("index", [0, 4])
def test_la_tua_carta_parte_dalla_mano_e_si_posa_al_suo_posto(browser, server, size, index):
    _open(browser, server, size)
    base, played, card = _views(index)
    _send(browser, base)
    start = _rect(browser, f".table__mine .hand > .card[data-suit='{card['suit']}'][data-rank='{card['rank']}']")
    browser.js("window.setTimeout = () => 0")  # niente ridisegno a fine lancio
    _send(browser, played)
    style = browser.js(f"(() => {{ const s = getComputedStyle(document.querySelector('{MY_CARD}')); return [s.animationName, s.animationDuration]; }})()")
    assert style == ["card-throw", f"{MY_THROW_MS / 1000:g}s"]
    # All'inizio è dove stava nella mano, grande uguale
    first = _at(browser, 0)
    assert abs(first["x"] - start["x"]) <= 4 and abs(first["y"] - start["y"]) <= 4, (first, start)
    assert first["w"] == pytest.approx(start["w"], rel=0.1)
    # Si solleva prima di partire
    lifted = _at(browser, 0.18 * MY_THROW_MS)
    assert lifted["y"] < first["y"] - 8
    # A metà volo l'arco: in orizzontale ha già fatto più strada che in verticale
    end = _at(browser, MY_THROW_MS - 1)
    mid = _at(browser, 0.55 * MY_THROW_MS)
    if abs(start["x"] - end["x"]) > 40:
        done_x = (start["x"] - mid["x"]) / (start["x"] - end["x"])
        done_y = (start["y"] - mid["y"]) / (start["y"] - end["y"])
        assert done_x > done_y, (done_x, done_y)
    # Alla fine è al suo posto nella presa, sopra le carte della mano
    browser.js(f"document.querySelector('{MY_CARD}').getAnimations().forEach((a) => a.finish())")
    rest = _rect(browser, MY_CARD)
    assert abs(end["x"] - rest["x"]) <= 4 and abs(end["y"] - rest["y"]) <= 4, (end, rest)
    assert browser.js("getComputedStyle(document.querySelector('.trick__card--bottom')).zIndex") == "30"


def test_la_carta_dell_avversario_vola_come_prima(browser, server):
    _open(browser, server, SIZES[0])
    base, played, _ = _views(0)
    _send(browser, base)
    browser.js("window.setTimeout = () => 0")
    answer = copy.deepcopy(played)
    answer["version"] += 1
    answer["trick"]["cards"].append({"seat": 1, "card": {"suit": "coppe", "rank": 3}})
    answer["trick"]["winning_seat"] = 0
    _send(browser, answer)
    style = browser.js("""(() => {
      const s = getComputedStyle(document.querySelector('.trick__card--top > [data-thrown]'));
      return [s.animationName, s.animationDuration];
    })()""")
    assert style == ["card-throw", f"{THROW_MS / 1000:g}s"]


def test_lancio_senza_la_carta_nella_mano_arriva_dal_basso(browser, server):
    # Per esempio la prima vista dopo un rientro: la carta non era nella mano disegnata
    _open(browser, server, SIZES[0])
    base, played, _ = _views(0)
    base["hand"] = played["hand"]
    _send(browser, base)
    browser.js("window.setTimeout = () => 0")
    _send(browser, played)
    first = _at(browser, 17)
    slot = _rect(browser, ".trick__card--bottom")
    assert first["y"] - slot["y"] > 100


# --- P107: il lancio degli avversari -------------------------------------------------

def _opponent_views(mode, seat):
    """La presa vuota e quella in cui `seat` apre con l'Asso di spade."""
    base = json.loads((STATIC / "dev" / f"vista_{mode}.json").read_text(encoding="utf-8"))
    base["version"] += 1
    base["trick"] = {"leader_seat": seat, "cards": [], "winning_seat": None}
    played = copy.deepcopy(base)
    played["version"] += 1
    played["trick"] = {"leader_seat": seat, "cards": [{"seat": seat, "card": {"suit": "spade", "rank": 1}}], "winning_seat": seat}
    for player in played["players"]:
        if player["seat"] == seat:
            player["cards_in_hand"] -= 1
    return base, played


@pytest.mark.parametrize("size", SIZES)
@pytest.mark.parametrize(("mode", "seat", "side"), [("1v1", 1, "top"), ("2v2", 1, "right"), ("2v2", 3, "left")])
def test_la_carta_dell_avversario_parte_dal_suo_ventaglio(browser, server, size, mode, seat, side):
    browser.open(f"{server}/game/prova?demo={mode}", *size, "document.querySelector('[data-mode]') !== null")
    browser.send("Emulation.setEmulatedMedia", features=[{"name": "prefers-reduced-motion", "value": "no-preference"}])
    base, played = _opponent_views(mode, seat)
    _send(browser, base)
    fan = browser.js(f"""(() => {{ const f = document.querySelector('[data-edge-hand="{side}"]'); const b = f.getBoundingClientRect();
      return {{ x: b.left + b.width / 2, y: b.top + b.height / 2, w: f.offsetWidth }}; }})()""")
    browser.js("window.setTimeout = () => 0")  # niente ridisegno a fine lancio
    _send(browser, played)
    card = f".trick__card--{side} > [data-thrown]"
    style = browser.js(f"(() => {{ const s = getComputedStyle(document.querySelector('{card}')); return [s.animationName, s.animationDuration]; }})()")
    assert style == ["card-throw", f"{THROW_MS / 1000:g}s"]

    def at(ms):
        browser.js(f"document.querySelector('{card}').getAnimations().forEach((a) => {{ a.pause(); a.currentTime = {ms} + a.effect.getTiming().delay; }})")
        return browser.js(f"""(() => {{ const e = document.querySelector('{card}'); const b = e.getBoundingClientRect();
          return {{ x: b.left + b.width / 2, y: b.top + b.height / 2 }}; }})()""")

    # All'inizio è dove sta il ventaglio, grande come le sue carte
    first = at(0)
    assert abs(first["x"] - fan["x"]) <= 4 and abs(first["y"] - fan["y"]) <= 4, (first, fan)
    scale = browser.js(f"parseFloat(getComputedStyle(document.querySelector('{card}')).getPropertyValue('--from-scale'))")
    slot = browser.js(f"document.querySelector('{card}').offsetWidth")
    assert scale * slot * browser.js(f"parseFloat(getComputedStyle(document.querySelector('{card}')).scale) || 1") == pytest.approx(fan["w"], rel=0.05)
    # Poi si stacca verso il centro e alla fine è al suo posto
    lifted = at(0.18 * THROW_MS)
    toward = (lambda a, b: abs(a["x"] - browser.js("innerWidth") / 2) + abs(a["y"] - browser.js("innerHeight") / 2)
              < abs(b["x"] - browser.js("innerWidth") / 2) + abs(b["y"] - browser.js("innerHeight") / 2))
    assert toward(lifted, first), (lifted, first)
    end = at(THROW_MS - 1)
    browser.js(f"document.querySelector('{card}').getAnimations().forEach((a) => a.finish())")
    rest = browser.js(f"""(() => {{ const b = document.querySelector('{card}').getBoundingClientRect();
      return {{ x: b.left + b.width / 2, y: b.top + b.height / 2 }}; }})()""")
    assert abs(end["x"] - rest["x"]) <= 4 and abs(end["y"] - rest["y"]) <= 4, (end, rest)

