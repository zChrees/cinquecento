"""P72: i punti della mano in corso al tavolo (D44).

Controlla il "Fatto quando" di SCALETTA.md (P72) con le scelte di D44: i tuoi punti
(nel 2v2 quelli della tua squadra) stanno sopra la tua mano, accanto al seme della
briscola; quelli degli avversari una volta sola, a sinistra dell'avatar
dell'avversario in alto (1v1) o sopra il giocatore a sinistra (2v2); il numero cambia con
la vista (hand_points, P67); sul telefono si vede solo il numero, da 1024 px in su
"N punti"; a fine mano, finché si vedono l'ultima presa e il riepilogo, restano i
punti della mano appena chiusa (last_hand), poi quelli della mano nuova; le
etichette non coprono ventagli, giocatori, presa, mazzo o mano, e il tavolo non
scorre alle misure di docs/prototipo/LEGGIMI.md.

Sta nella suite `api`, come test_grafica_tavolo.py, per il tempo della suite
`frontend`. Il tavolo si apre nella prova (/game/prova?demo=1v1 o 2v2) in Chrome o
Edge senza finestra (tests/browser.py); il test gli manda viste e frasi con gli
eventi del browser "demo:state" e "demo:phrases". Non serve MySQL. Se né Chrome né
Edge sono installati i controlli nel browser si saltano.
"""

import copy
import json
from pathlib import Path

import pytest

from app import create_app
from app.realtime import table_phrases
from tests.browser import TEST_COOKIE, Browser, FakeUser, find_browser, running_server

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "app" / "static"
PHONE = (360, 640)
DESKTOP = (1440, 900)
SIZES = [(360, 640), (375, 667), (390, 844), (412, 915), (768, 1024), (1280, 720), (1440, 900)]


def _view(mode):
    return json.loads((STATIC / "dev" / f"vista_{mode}.json").read_text(encoding="utf-8"))


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


def _open(browser, server, mode, size=PHONE):
    browser.open(f"{server}/game/prova?demo={mode}", *size, "document.querySelector('[data-mode]') !== null")
    _dispatch(browser, "demo:phrases", table_phrases.phrases_event())


def _dispatch(browser, name, detail):
    browser.js(f"document.querySelector('[data-table]').dispatchEvent(new CustomEvent({json.dumps(name)}, "
               f"{{ detail: {json.dumps(detail)} }}))")


def _resize(browser, size):
    browser.send("Emulation.setDeviceMetricsOverride", width=size[0], height=size[1], deviceScaleFactor=1, mobile=False)
    browser.wait_js(f"innerWidth === {size[0]} && innerHeight === {size[1]}", f"schermo {size}", 5)


POINTS = """[...document.querySelectorAll('[data-hand-points]')].map((p) => ({
  total: p.dataset.handPoints, team: p.dataset.team, text: p.innerText.trim(),
  label: p.getAttribute('aria-label'),
  where: p.closest('.table__me-side') ? 'me' : p.closest('.seat').dataset.position,
}))"""


def _points(browser):
    return {p["where"]: p for p in browser.js(POINTS)}


def test_1v1_i_tuoi_punti_e_quelli_dell_avversario(browser, server):
    view = _view("1v1")
    mine = next(p["total"] for p in view["hand_points"] if p["team"] == 0)
    theirs = next(p["total"] for p in view["hand_points"] if p["team"] == 1)
    _open(browser, server, "1v1")
    points = _points(browser)
    assert set(points) == {"me", "top"}
    assert (points["me"]["total"], points["me"]["team"]) == (str(mine), "0")
    assert (points["top"]["total"], points["top"]["team"]) == (str(theirs), "1")
    # Sul telefono solo il numero; il lettore di schermo legge la frase intera
    assert points["me"]["text"] == str(mine) and points["top"]["text"] == str(theirs)
    assert points["me"]["label"] == f"I tuoi punti in questa mano: {mine}"
    assert points["top"]["label"] == f"Punti di Turi in questa mano: {theirs}"
    # I tuoi accanto al seme della briscola, nella riga sopra la mano
    assert browser.js("document.querySelector('.table__me-side [data-trump-badge]') !== null")


def test_2v2_una_volta_sola_accanto_al_giocatore_a_sinistra(browser, server):
    view = _view("2v2")
    ours = next(p["total"] for p in view["hand_points"] if p["team"] == 0)
    theirs = next(p["total"] for p in view["hand_points"] if p["team"] == 1)
    _open(browser, server, "2v2")
    points = _points(browser)
    assert len(browser.js(POINTS)) == 2
    assert set(points) == {"me", "left"}
    assert (points["me"]["total"], points["me"]["team"]) == (str(ours), "0")
    assert (points["left"]["total"], points["left"]["team"]) == (str(theirs), "1")
    assert points["me"]["label"] == f"Punti della tua squadra in questa mano: {ours}"
    assert points["left"]["label"] == f"Punti degli avversari in questa mano: {theirs}"


@pytest.mark.parametrize("mode", ["1v1", "2v2"])
def test_sul_computer_n_punti(browser, server, mode):
    _open(browser, server, mode, DESKTOP)
    points = browser.js(POINTS)
    assert len(points) == 2
    for p in points:
        assert p["text"] == f"{p['total']} punti", p
    _resize(browser, (768, 1024))
    points = browser.js(POINTS)
    assert len(points) == 2
    for p in points:
        assert p["text"] == p["total"], p


def test_i_punti_salgono_con_la_vista(browser, server):
    view = _view("1v1")
    _open(browser, server, "1v1")
    later = copy.deepcopy(view)
    later["version"] += 1
    later["hand_points"] = [{"team": 0, "total": 61}, {"team": 1, "total": 47}]
    _dispatch(browser, "demo:state", later)
    points = _points(browser)
    assert (points["me"]["total"], points["top"]["total"]) == ("61", "47")


def test_a_fine_mano_restano_i_punti_della_mano_chiusa(browser, server):
    base = _view("1v1")
    _open(browser, server, "1v1")
    new_hand = copy.deepcopy(base)
    new_hand["version"] += 1
    new_hand["hand_number"] += 1
    new_hand["last_trick"] = None
    new_hand["trick"] = {"leader_seat": 0, "cards": []}
    new_hand["sings"] = []
    new_hand["trump"] = None
    new_hand["hand_points"] = [{"team": 0, "total": 0}, {"team": 1, "total": 0}]
    new_hand["last_hand"] = {"hand_number": base["hand_number"], "teams": [
        {"team": 0, "card_points": 48, "sing_points": 20, "hand_total": 68},
        {"team": 1, "card_points": 72, "sing_points": 40, "hand_total": 112}],
        "last_trick": {"winner_seat": 1, "cards": [
            {"seat": 0, "card": {"suit": "spade", "rank": 4}}, {"seat": 1, "card": {"suit": "spade", "rank": 1}}]}}
    _dispatch(browser, "demo:state", new_hand)

    # Ultima presa della mano: i punti della mano appena chiusa
    assert browser.js("document.querySelector('[data-last-trick]') !== null")
    points = _points(browser)
    assert (points["me"]["total"], points["top"]["total"]) == ("68", "112")
    # Riepilogo: ancora quelli
    browser.wait_js("document.querySelector('[data-hand-summary]') !== null", "riepilogo", 6)
    points = _points(browser)
    assert (points["me"]["total"], points["top"]["total"]) == ("68", "112")
    # Chiuso il riepilogo, la mano nuova parte da zero
    browser.click("[data-hand-summary-close]")
    points = _points(browser)
    assert (points["me"]["total"], points["top"]["total"]) == ("0", "0")


RECTS = """(() => {
  const rect = (e) => { const b = e.getBoundingClientRect(); return { l: b.left, t: b.top, r: b.right, b: b.bottom }; };
  const all = (s) => [...document.querySelectorAll(s)].map(rect);
  return {
    points: all('[data-hand-points]'),
    others: all('[data-edge-hand] > .card, .seat__avatar, .seat__label, [data-trump-badge], [data-phrases-button], '
      + '[data-trick], [data-deck-count], .table__mine .hand, [data-scoreboard], [data-leave]'),
    w: innerWidth, h: innerHeight,
    scrollH: document.scrollingElement.scrollHeight, scrollW: document.scrollingElement.scrollWidth,
  };
})()"""


def _overlap(a, b):
    return a["l"] < b["r"] - 1 and a["r"] > b["l"] + 1 and a["t"] < b["b"] - 1 and a["b"] > b["t"] + 1


@pytest.mark.parametrize("mode", ["1v1", "2v2"])
def test_i_punti_non_coprono_niente(browser, server, mode):
    _open(browser, server, mode)
    for size in SIZES:
        _resize(browser, size)
        box = browser.js(RECTS)
        assert box["scrollH"] <= box["h"] and box["scrollW"] <= box["w"], (mode, size, "il tavolo scorre")
        assert len(box["points"]) == 2, (mode, size)
        for point in box["points"]:
            assert point["l"] >= 0 and point["t"] >= 0 and point["r"] <= box["w"] and point["b"] <= box["h"], \
                (mode, size, point, "fuori dallo schermo")
            for other in box["others"]:
                assert not _overlap(point, other), (mode, size, point, other)
