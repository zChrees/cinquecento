"""P76: presa con le carte a croce, senza coprirsi, e la carta che vince evidenziata.

Controlla il "Fatto quando" di SCALETTA.md (P76): su telefono e computer le carte
della presa (in corso e appena chiusa, P57) non si coprono e il tavolo non scorre;
la carta evidenziata è sempre quella di trick.winning_seat (P75) e il segno si
sposta quando una carta nuova la supera; il segno non è solo un colore (la carta è
sollevata e più grande, e i lettori di schermo sentono "Sta vincendo").

Il tavolo si apre nella prova (/game/prova?demo=1v1 o 2v2) in Chrome o Edge senza
finestra (tests/browser.py), con le viste di app/static/dev/ mandate con l'evento
del browser "demo:state". Non serve MySQL; sta nella suite table3 (P121: prima in api, poi
vicina al limite di tempo).
"""

import copy
import json
from pathlib import Path

import pytest

from app import create_app
from tests.browser import TEST_COOKIE, Browser, FakeUser, find_browser, running_server

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "app" / "static"
PHONE = (360, 640)
SIZES = [(360, 640), (390, 844), (768, 1024), (1024, 768), (1280, 720), (1440, 900)]


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


def _dispatch(browser, view):
    browser.js(f"document.querySelector('[data-table]').dispatchEvent(new CustomEvent('demo:state', "
               f"{{ detail: {json.dumps(view)} }}))")


def _with_trick(base, version, cards, winning_seat):
    view = copy.deepcopy(base)
    view["version"] = version
    view["trick"] = {"leader_seat": cards[0]["seat"] if cards else base["trick"]["leader_seat"],
                     "cards": cards, "winning_seat": winning_seat}
    return view


def _cards(base, ranks):
    """Una carta per giocatore, nell'ordine dei posti, finché bastano i valori."""
    seats = [player["seat"] for player in base["players"]]
    return [{"seat": seat, "card": {"suit": "spade", "rank": rank}} for seat, rank in zip(seats, ranks)]


def _closed(base, version, cards, winner):
    """Vista subito dopo la chiusura della presa: presa vuota e last_trick nuova (P57)."""
    view = _with_trick(base, version, [], None)
    view["last_trick"] = {"winner_seat": winner, "cards": cards}
    return view


RECTS = r"""((selector) => [...document.querySelectorAll(selector)].map((e) => {
  const b = e.getBoundingClientRect(); return { l: b.left, t: b.top, r: b.right, b: b.bottom };
}))"""


def _overlap(a, b):
    return a["l"] < b["r"] and a["r"] > b["l"] and a["t"] < b["b"] and a["b"] > b["t"]


def _check_apart(browser, selector, count, where):
    cards = browser.js(f"{RECTS}({json.dumps(selector)})")
    assert len(cards) == count, where
    # Le carte restano leggibili: anche nel 2v2 a 360 px almeno 44 px (senza contare la rotazione)
    widths = browser.js(f"[...document.querySelectorAll({json.dumps(selector)})].map((c) => c.offsetWidth)")
    assert min(widths) >= 44, (where, widths)
    for i, a in enumerate(cards):
        for b in cards[i + 1:]:
            assert not _overlap(a, b), (where, "due carte della presa si coprono", a, b)


@pytest.mark.parametrize("mode", ["1v1", "2v2"])
def test_le_carte_della_presa_non_si_coprono(browser, server, mode):
    base = _view(mode)
    players = len(base["players"])
    full = _cards(base, (3, 1, 10, 7))
    version = base["version"]
    # La pagina si apre una volta sola; per ogni misura cambia solo lo schermo
    _open(browser, server, mode)
    for size in SIZES:
        browser.send("Emulation.setDeviceMetricsOverride", width=size[0], height=size[1], deviceScaleFactor=1, mobile=False)
        browser.wait_js(f"innerWidth === {size[0]} && innerHeight === {size[1]}", f"schermo {size}", 5)
        # Presa in corso, piena quanto può (una carta in meno dei giocatori)
        version += 1
        _dispatch(browser, _with_trick(base, version, full[:players - 1], full[1]["seat"]))
        _check_apart(browser, "[data-trick] .card", players - 1, (mode, size, "presa in corso"))
        scroll = browser.js("[document.scrollingElement.scrollHeight <= innerHeight, "
                            "document.scrollingElement.scrollWidth <= innerWidth]")
        assert scroll == [True, True], (mode, size, "il tavolo scorre")
        # Presa appena chiusa, con tutte le carte (P57)
        version += 1
        _dispatch(browser, _closed(base, version, full[:players], full[1]["seat"]))
        _check_apart(browser, "[data-last-trick] .card", players, (mode, size, "presa chiusa"))


@pytest.mark.parametrize("mode", ["1v1", "2v2"])
def test_evidenziata_la_carta_di_winning_seat(browser, server, mode):
    base = _view(mode)
    _open(browser, server, mode)
    # La vista d'esempio ha già una presa con winning_seat (P75)
    winning = base["trick"]["winning_seat"]
    marked = browser.js("[...document.querySelectorAll('[data-trick] [data-winning]')].map((e) => +e.dataset.trickSeat)")
    assert marked == [winning]

    # Il segno non è solo un colore: la carta è sollevata e più grande delle altre
    look = browser.js("""(() => {
      const style = (e) => { const s = getComputedStyle(e.querySelector('.card')); return { translate: s.translate, scale: s.scale }; };
      return { winner: style(document.querySelector('[data-trick] [data-winning]')),
               others: [...document.querySelectorAll('[data-trick] .trick__card:not([data-winning])')].map(style) };
    })()""")
    assert look["winner"]["translate"] not in ("none", "0px") and look["winner"]["scale"] not in ("none", "1")
    for other in look["others"]:
        assert other["translate"] in ("none", "0px") and other["scale"] in ("none", "1")
    label = browser.js("document.querySelector('[data-trick]').getAttribute('aria-label')")
    assert "Sta vincendo:" in label

    # Nel 2v2 una carta nuova supera quella che vinceva: il segno si sposta
    # (nel 1v1 la presa in corso ha al massimo una carta)
    if mode == "2v2":
        cards = base["trick"]["cards"]
        other = next(c["seat"] for c in cards if c["seat"] != winning)
        _dispatch(browser, _with_trick(base, base["version"] + 1, cards, other))
        assert browser.js("[...document.querySelectorAll('[data-trick] [data-winning]')].map((e) => +e.dataset.trickSeat)") \
            == [other]

    # Presa vuota: niente segno
    _dispatch(browser, _with_trick(base, base["version"] + 2, [], None))
    assert browser.js("document.querySelector('[data-trick] [data-winning], [data-trick] .trick__card--winner')") is None
    assert "Sta vincendo" not in browser.js("document.querySelector('[data-trick]').getAttribute('aria-label')")


def test_presa_chiusa_evidenziata_allo_stesso_modo(browser, server):
    base = _view("2v2")
    _open(browser, server, "2v2")
    full = _cards(base, (3, 1, 10, 7))
    _dispatch(browser, _with_trick(base, base["version"] + 1, full[:3], full[1]["seat"]))
    _dispatch(browser, _closed(base, base["version"] + 2, full, full[1]["seat"]))
    look = browser.js("""(() => {
      const w = document.querySelector('[data-last-trick] .trick__card--winner');
      const s = getComputedStyle(w.querySelector('.card'));
      return { seat: +w.dataset.trickSeat, translate: s.translate, scale: s.scale,
               count: document.querySelectorAll('[data-last-trick] .trick__card--winner').length };
    })()""")
    assert look["seat"] == full[1]["seat"] and look["count"] == 1
    assert look["translate"] not in ("none", "0px") and look["scale"] not in ("none", "1")
