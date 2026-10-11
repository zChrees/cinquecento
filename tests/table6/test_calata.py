"""P85: "Cala le carte" al tavolo (D45).

Controlla il "Fatto quando" di SCALETTA.md (P85): il pulsante compare solo quando la
vista lo permette (legal.lay_down) e, premuto, manda la richiesta una volta sola;
quando qualcuno cala (last_hand.laid_down, P84) le carte di tutti si vedono per
LAID_DOWN_MS prima del riepilogo: i ventagli degli altri entrano scoperti nel tavolo,
interi e dentro lo schermo (scelta di Christian del 04/10), la tua mano è quella del
momento della calata e al centro c'è "<nome> cala le carte"; se la calata chiude la
partita, dopo le carte calate arriva il riquadro finale. LAID_DOWN_MS è uguale alla
pausa del server (LAID_DOWN_SECONDS di app/realtime/room.py, P94).

Il tavolo si apre nella prova (/game/prova?demo=1v1 o 2v2) in Chrome o Edge senza
finestra (tests/browser.py), con le viste di app/static/dev/ mandate con l'evento del
browser "demo:state". Non serve MySQL.
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
GAME_JS = (STATIC / "js" / "pages" / "game.js").read_text(encoding="utf-8")
ROOM_PY = (ROOT / "app" / "realtime" / "room.py").read_text(encoding="utf-8")
PHONE = (360, 640)
DESKTOP = (1280, 720)


def _view(mode):
    return json.loads((STATIC / "dev" / f"vista_{mode}.json").read_text(encoding="utf-8"))


def test_durata_uguale_alla_pausa_del_server():
    page = int(re.search(r"const LAID_DOWN_MS = (\d+);", GAME_JS).group(1))
    server = float(re.search(r"^LAID_DOWN_SECONDS = ([\d.]+)", ROOM_PY, re.MULTILINE).group(1))
    assert page == server * 1000


def test_evento_nel_posto_dei_nomi():
    events = (STATIC / "js" / "core" / "events.js").read_text(encoding="utf-8")
    assert "GAME_LAY_DOWN: 'game:lay_down'" in events
    assert "EVENTS.GAME_LAY_DOWN" in GAME_JS


# --- Nel browser -------------------------------------------------------------------


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


def _send(browser, view):
    browser.js("document.querySelector('[data-table]').dispatchEvent("
               f"new CustomEvent('demo:state', {{ detail: {json.dumps(view)} }}))")


# Carte che nessuno ha in mano negli esempi: le mani calate degli altri
SPARE = [{"suit": suit, "rank": rank} for suit in ("bastoni", "denari", "spade", "coppe") for rank in (2, 4, 5, 6, 7)]


def _laid_hands(base, seat_count):
    mine = base["hand"][:seat_count]
    spare = [card for card in SPARE if card not in base["hand"]]
    hands = []
    for player in base["players"]:
        if player["seat"] == base["you"]["seat"]:
            hands.append({"seat": player["seat"], "cards": mine})
        else:
            hands.append({"seat": player["seat"], "cards": spare[:seat_count]})
            spare = spare[seat_count:]
    return hands


def _laid_view(base, who, count=3, *, finished=False):
    """La vista subito dopo che `who` ha calato con `count` carte a testa (P84)."""
    view = copy.deepcopy(base)
    view["version"] += 1
    view["last_hand"] = {
        "hand_number": base["hand_number"],  # la mano appena finita: quella in corso nella vista di prima
        "teams": [{"team": t, "card_points": 60, "sing_points": 0, "hand_total": 60} for t in (0, 1)],
        "last_trick": base["last_trick"],
        "laid_down": {"seat": who, "hands": _laid_hands(base, count), "sings": []},
    }
    view["trick"] = {"leader_seat": who, "cards": [], "winning_seat": None}
    if finished:
        view["status"] = "finished"
        view["turn"] = None
        view["legal"] = {"play": [], "sing": [], "lay_down": False}
        view["result"] = {"reason": "score", "winner_team": 0, "abandoned_seats": [], "scores": base["scores"]}
    else:
        view["hand_number"] += 1
        view["last_trick"] = None
        view["sings"] = []
    return view


def _start(base):
    """La vista di partenza: la mano prima, con un last_hand di una mano ancora precedente."""
    view = copy.deepcopy(base)
    view["last_hand"] = None
    return view


def test_pulsante_solo_con_lay_down(browser, server):
    base = _view("1v1")
    _open(browser, server, "1v1")
    assert browser.js("document.querySelector('[data-lay-down-button]')") is None
    view = copy.deepcopy(base)
    view["version"] += 1
    view["legal"]["lay_down"] = True
    _send(browser, view)
    assert browser.js("document.querySelector('[data-lay-down-button]').textContent").endswith("Cala le carte")
    browser.click("[data-lay-down-button]")
    assert "vuoi calare le carte" in browser.js("document.querySelector('[data-table-status]').textContent")
    view = copy.deepcopy(view)
    view["version"] += 1
    view["legal"]["lay_down"] = False
    _send(browser, view)
    assert browser.js("document.querySelector('[data-lay-down-button]')") is None


RECTS = r"""((selector) => [...document.querySelectorAll(selector)].map((e) => {
  const b = e.getBoundingClientRect(); return { l: b.left, t: b.top, r: b.right, b: b.bottom };
}))"""


def _cards_of(browser, selector):
    return browser.js(f"[...document.querySelectorAll({json.dumps(selector)})]"
                      ".map((c) => ({ suit: c.dataset.suit, rank: +c.dataset.rank }))")


@pytest.mark.parametrize("mode", ["1v1", "2v2"])
@pytest.mark.parametrize("size", [PHONE, DESKTOP], ids=["telefono", "computer"])
def test_carte_calate_poi_riepilogo(browser, server, mode, size):
    base = _start(_view(mode))
    me = base["you"]["seat"]
    who = next(p["seat"] for p in base["players"] if p["seat"] != me)
    _open(browser, server, mode, size)
    _send(browser, base)
    laid = _laid_view(base, who)
    _send(browser, laid)

    name = next(p["username"] for p in base["players"] if p["seat"] == who)
    assert browser.js("document.querySelector('[data-laid-down] .laid-down__text').textContent") == f"{name} cala le carte"
    # I ventagli degli altri sono scoperti, con le carte giuste
    hands = {h["seat"]: h["cards"] for h in laid["last_hand"]["laid_down"]["hands"]}
    for player in base["players"]:
        seat = player["seat"]
        if seat == me:
            continue
        assert _cards_of(browser, f"[data-revealed-seat='{seat}'] .card") == hands[seat], (mode, size, seat)
    assert browser.js("document.querySelectorAll('[data-edge-hand]').length") == 0
    # La tua mano è quella del momento della calata, e non si gioca
    assert _cards_of(browser, ".table__mine .hand .card") == hands[me]
    assert browser.js("document.querySelectorAll('.table__mine .hand button').length") == 0
    # Le carte scoperte si vedono intere: dentro lo schermo (finita l'entrata di 0,3 s)
    time.sleep(0.4)
    rects = browser.js(f"{RECTS}('[data-revealed-hand] .card')")
    width, height = size
    for r in rects:
        assert r["l"] >= 0 and r["t"] >= 0 and r["r"] <= width and r["b"] <= height, (mode, size, r)
    scroll = browser.js("[document.scrollingElement.scrollHeight <= innerHeight, "
                        "document.scrollingElement.scrollWidth <= innerWidth]")
    assert scroll == [True, True], (mode, size, "il tavolo scorre")
    assert browser.js("document.querySelector('[data-hand-summary]')") is None

    # Dopo LAID_DOWN_MS: via le carte calate, arriva il riepilogo
    browser.wait_js("document.querySelector('[data-laid-down]') === null && "
                    "document.querySelector('[data-hand-summary]') !== null", "riepilogo dopo la calata", 6)
    assert browser.js("document.querySelectorAll('[data-revealed-hand]').length") == 0


def test_calata_tua_dice_hai_calato(browser, server):
    base = _start(_view("1v1"))
    _open(browser, server, "1v1")
    _send(browser, base)
    _send(browser, _laid_view(base, base["you"]["seat"]))
    assert browser.js("document.querySelector('[data-laid-down] .laid-down__text').textContent") == "Hai calato le carte"


def test_calata_che_chiude_la_partita(browser, server):
    base = _start(_view("1v1"))
    _open(browser, server, "1v1")
    _send(browser, base)
    _send(browser, _laid_view(base, 1, finished=True))
    assert browser.js("document.querySelector('[data-laid-down]') !== null")
    assert browser.js("document.querySelector('[data-result]')") is None
    browser.wait_js("document.querySelector('[data-laid-down]') === null && "
                    "document.querySelector('[data-result]') !== null", "riquadro finale dopo la calata", 6)


def test_nessuna_carta_vola_con_la_calata(browser, server):
    """Con una calata last_hand.last_trick è una presa già vista: non si rilancia."""
    base = _start(_view("1v1"))
    _open(browser, server, "1v1")
    browser.send("Emulation.setEmulatedMedia", features=[{"name": "prefers-reduced-motion", "value": "no-preference"}])
    _send(browser, base)
    time.sleep(0.5)  # finiscono i lanci della vista di partenza
    _send(browser, _laid_view(base, 1))
    assert browser.js("document.querySelectorAll('[data-thrown]').length") == 0
