"""P78: animazioni in fila al tavolo.

Controlla il "Fatto quando" di SCALETTA.md (P78): con "riduci movimento" spento,
(1) due lanci vicini non partono insieme: la carta arrivata mentre un'altra vola
aspetta che quella si posi, e fino ad allora non si vede; (2) dopo una presa le
carte si pescano una alla volta (DRAW_MS ciascuna), prima chi ha preso e poi gli
altri in ordine di turno, a partire da quando si è posata la carta che ha chiuso
la presa. Che le durate di game.js e dei CSS coincidano lo controllano i test di
P70 (test_lancio_carta.py, test_carte_avversari.py).

Il tavolo si apre nella prova (/game/prova?demo=2v2) in Chrome o Edge senza
finestra (tests/browser.py), con le viste mandate con l'evento "demo:state".
Non serve MySQL.
"""

import copy
import itertools
import json
import re
import time
from pathlib import Path

import pytest

from app import create_app
from tests.browser import TEST_COOKIE, Browser, FakeUser, find_browser, running_server

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "app" / "static"
GAME = (STATIC / "js" / "pages" / "game.js").read_text(encoding="utf-8")
THROW_MS = int(re.search(r"const THROW_MS = (\d+);", GAME).group(1))
DRAW_MS = int(re.search(r"const DRAW_MS = (\d+);", GAME).group(1))
SLACK = 120  # millisecondi tra l'evento mandato e la lettura nel browser


def _view():
    return json.loads((STATIC / "dev" / "vista_2v2.json").read_text(encoding="utf-8"))


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


def _open(browser, server):
    browser.open(f"{server}/game/prova?demo=2v2", 1280, 720, "document.querySelector('[data-mode]') !== null")
    browser.send("Emulation.setEmulatedMedia", features=[{"name": "prefers-reduced-motion", "value": "no-preference"}])
    assert browser.js("matchMedia('(prefers-reduced-motion: reduce)').matches") is False


def _send(browser, *views):
    """Manda le viste una dopo l'altra, nello stesso momento (come due eventi vicini)."""
    script = "".join(f"document.querySelector('[data-table]').dispatchEvent(new CustomEvent('demo:state', "
                     f"{{ detail: {json.dumps(view)} }}));" for view in views)
    browser.js(f"(() => {{ {script} }})()")


def _with_trick(base, version, seats_cards, turn_seat):
    view = copy.deepcopy(base)
    view["version"] = version
    view["trick"] = {"leader_seat": seats_cards[0][0], "cards": [{"seat": s, "card": c} for s, c in seats_cards],
                     "winning_seat": seats_cards[0][0]}
    view["turn"] = {"seat": turn_seat, "seconds_total": 30, "seconds_left": 30.0}
    view["legal"] = {"play": [], "sing": []}
    return view


THROWS = r"""(() => [...document.querySelectorAll('[data-trick] .trick__card')].map((slot) => {
  const card = slot.querySelector('.card');
  const a = card.getAnimations().find((x) => x.animationName === 'card-throw');
  return { seat: +slot.dataset.trickSeat, delay: card.style.animationDelay ? parseFloat(card.style.animationDelay) : null,
           progress: a ? a.effect.getComputedTiming().progress : null, opacity: +getComputedStyle(card).opacity };
}))()"""

DENARI_7 = {"suit": "denari", "rank": 7}
DENARI_3 = {"suit": "denari", "rank": 3}
BASTONI_2 = {"suit": "bastoni", "rank": 2}


def test_due_lanci_vicini_vanno_in_fila(browser, server):
    base = _view()
    _open(browser, server)
    v = base["version"]
    # Presa con la sola carta di Salvo... poi Giulia e Rosalia giocano quasi insieme
    _send(browser, _with_trick(base, v + 1, [(1, DENARI_7)], 2))
    _send(browser, _with_trick(base, v + 2, [(1, DENARI_7), (2, DENARI_3)], 3),
          _with_trick(base, v + 3, [(1, DENARI_7), (2, DENARI_3), (3, BASTONI_2)], 0))
    cards = {c["seat"]: c for c in browser.js(THROWS)}
    # Il 3 di denari vola subito; il 2 di bastoni aspetta che si posi, e intanto non si vede
    assert cards[2]["delay"] is not None and cards[2]["delay"] <= 0, cards
    assert cards[3]["delay"] is not None and THROW_MS - SLACK <= cards[3]["delay"] <= THROW_MS, cards
    assert cards[3]["opacity"] == 0, cards
    # Quando il primo si è posato parte il secondo
    time.sleep((THROW_MS + 150) / 1000)
    cards = {c["seat"]: c for c in browser.js(THROWS)}
    assert cards[3]["progress"] is not None and cards[3]["progress"] > 0 and cards[3]["opacity"] > 0, cards
    # Alla fine nessuna carta vola più
    browser.wait_js("document.querySelector('[data-trick] [data-thrown]') === null", "lanci finiti", 3)


DRAWS = r"""(() => {
  const delay = (e) => e && e.style.animationDelay ? parseFloat(e.style.animationDelay) : null;
  const fans = {};
  for (const fan of document.querySelectorAll('[data-edge-hand]')) fans[fan.dataset.edgeHand] = delay(fan.lastElementChild);
  return { mine: delay(document.querySelector('.table__mine .hand [data-drawn]')), ...fans };
})()"""


def test_nel_2v2_si_pesca_una_carta_alla_volta(browser, server):
    base = _view()
    _open(browser, server)
    v = base["version"]
    before = _with_trick(base, v + 1, [(1, DENARI_7), (2, DENARI_3), (3, BASTONI_2)], 0)
    for player in before["players"]:
        player["cards_in_hand"] = 5 if player["seat"] == 0 else 4
    # Mario chiude la presa con l'Asso di coppe e prende; poi pescano Mario, Salvo, Giulia, Rosalia
    closed = copy.deepcopy(before)
    closed["version"] = v + 2
    closed["trick"] = {"leader_seat": 0, "cards": [], "winning_seat": None}
    closed["last_trick"] = {"winner_seat": 0, "cards": before["trick"]["cards"] + [
        {"seat": 0, "card": {"suit": "coppe", "rank": 1}}]}
    closed["hand"] = [c for c in before["hand"] if c != {"suit": "coppe", "rank": 1}] + [{"suit": "denari", "rank": 2}]
    closed["deck_count"] = before["deck_count"] - 4
    for player in closed["players"]:
        player["cards_in_hand"] = 5
    _send(browser, before)
    browser.wait_js("document.querySelector('[data-trick] [data-thrown]') === null", "lanci della presa finiti", 3)
    _send(browser, closed)
    delays = browser.js(DRAWS)
    # Posti 1, 2, 3 sono a destra, in alto e a sinistra (vista di Mario, posto 0)
    order = [delays["mine"], delays["right"], delays["top"], delays["left"]]
    assert all(d is not None for d in order), delays
    # La prima pescata aspetta che l'Asso che ha chiuso la presa si posi
    assert THROW_MS - SLACK <= order[0] <= THROW_MS, delays
    # Le altre una dopo l'altra, senza accavallarsi
    for earlier, later in itertools.pairwise(order):
        assert DRAW_MS - 30 <= later - earlier <= DRAW_MS + 30, delays
    browser.wait_js("document.querySelector('[data-drawn], [data-drawing]') === null", "pescate finite",
                    (THROW_MS + 4 * DRAW_MS) / 1000 + 2)
