"""P119: un'animazione non fa lampeggiare il resto del tavolo.

Il tavolo si ridisegna tutto a ogni vista (P70). Prima di P119, a ogni lancio,
pescata o frase: le carte del canto (e le scritte delle carte calate e delle carte
del compagno) rifacevano l'entrata da trasparenti, e le immagini degli avatar e
della briscola nell'angolo erano nuove, quindi per un attimo vuote. Ora le entrate
riprendono dal tempo già passato e le immagini sono le stesse del disegno di prima
(reuseCardImages di Card.js).

Controlla fotogramma per fotogramma, nel 1v1 e nel 2v2, sul telefono e da computer,
mentre arrivano un canto, un lancio e altri ridisegni: le carte del canto restano
piene, avatar e briscola tengono le stesse immagini. Il tavolo si apre nella prova
(/game/prova?demo=…) in Chrome o Edge senza finestra, con "riduci movimento" spento.
Non serve MySQL.
"""

import copy
import json
import time
from pathlib import Path

import pytest

from app import create_app
from tests.browser import TEST_COOKIE, Browser, FakeUser, find_browser, running_server

ROOT = Path(__file__).resolve().parents[2]
DEV = ROOT / "app" / "static" / "dev"
SIZES = {"telefono": (390, 844), "computer": (1440, 900)}

# Registra a ogni fotogramma: identità degli elementi (un numero per nodo), opacità e
# animazioni in corso delle carte del canto, delle immagini di avatar e briscola
WATCH = """(() => {
  const ids = new WeakMap(); let next = 1;
  const id = (e) => { if (!ids.has(e)) ids.set(e, next++); return ids.get(e); };
  window.__frames = [];
  const t0 = performance.now();
  const tick = () => {
    const sang = [...document.querySelectorAll('.sang__cards')];
    __frames.push({
      sang: sang.map((e) => ({opacity: getComputedStyle(e).opacity,
        restarted: e.getAnimations().some((a) => a.animationName === 'sang-in' && a.currentTime < 250)})),
      avatars: [...document.querySelectorAll('.seat .avatar img')].map(id),
      trump: [...document.querySelectorAll('[data-trump-badge] img')].map(id),
    });
    if (performance.now() - t0 < 2500) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
})()"""


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


def _send(browser, name, detail):
    browser.js(f"document.querySelector('[data-table]').dispatchEvent(new CustomEvent({json.dumps(name)}, "
               f"{{ detail: {json.dumps(detail)} }}))")


def _views(mode):
    """Una vista con la briscola (coppe) in cui tocca a un avversario, e la stessa dopo il suo lancio."""
    view = json.loads((DEV / f"vista_{mode}.json").read_text(encoding="utf-8"))
    view["version"] += 1
    view["sings"] = [{"seat": 1, "suit": "coppe", "points": 40}]
    view["trump"] = "coppe"
    n = len(view["players"])
    thrower = (view["trick"]["cards"][-1]["seat"] + 1) % n
    if thrower == 0:   # tocca a Mario: gioca prima l'avversario dopo di lui
        thrower = 1
        view["trick"] = {"leader_seat": 1, "cards": [], "winning_seat": None}
    view["turn"] = {**view["turn"], "seat": thrower}
    view["legal"] = {"play": [], "sing": [], "lay_down": False}
    thrown = copy.deepcopy(view)
    thrown["version"] += 1
    thrown["trick"] = {**view["trick"], "cards": view["trick"]["cards"] + [{"seat": thrower, "card": {"suit": "bastoni", "rank": 5}}],
                       "winning_seat": thrower}
    for player in thrown["players"]:
        if player["seat"] == thrower:
            player["cards_in_hand"] -= 1
    thrown["turn"] = {**view["turn"], "seat": (thrower + 1) % n}
    return view, thrown


@pytest.mark.parametrize("size", SIZES, ids=list(SIZES))
@pytest.mark.parametrize("mode", ["1v1", "2v2"])
def test_canto_avatar_e_briscola_non_lampeggiano(browser, server, mode, size):
    view, thrown = _views(mode)
    browser.open(f"{server}/game/prova?demo={mode}", *SIZES[size], "document.querySelector('[data-cards-ready]') !== null", 30)
    browser.send("Emulation.setEmulatedMedia", features=[{"name": "prefers-reduced-motion", "value": "no-preference"}])
    _send(browser, "demo:state", view)
    _send(browser, "demo:sang", {"seat": 1, "suit": "spade", "points": 20, "show_seconds": 5, "cards": [
        {"suit": "spade", "rank": 10}, {"suit": "spade", "rank": 9}]})
    time.sleep(0.5)   # l'entrata delle carte del canto (0,3 s) è finita
    browser.js(WATCH)
    time.sleep(0.2)
    _send(browser, "demo:state", thrown)   # un lancio: il tavolo si ridisegna più volte
    time.sleep(0.3)
    _send(browser, "demo:phrases", {"phrases": [{"code": "ciao", "text": "Ciao!"}]})   # e un altro ridisegno
    time.sleep(0.5)
    _send(browser, "demo:phrase", {"seat": 1, "code": "ciao", "text": "Ciao!"})
    browser.wait_js("window.__frames.length > 0 && performance.now() > 0", "fotogrammi", 3)
    time.sleep(1.6)
    frames = browser.js("window.__frames")
    assert len(frames) > 30, len(frames)
    # Le carte del canto ci sono sempre, piene, e la loro entrata non riparte
    assert all(f["sang"] and all(s["opacity"] == "1" and not s["restarted"] for s in f["sang"]) for f in frames), \
        [f["sang"] for f in frames if not f["sang"] or any(s["opacity"] != "1" or s["restarted"] for s in f["sang"])][:3]
    # Le immagini di avatar e briscola sono sempre le stesse
    avatars = {tuple(f["avatars"]) for f in frames}
    trump = {tuple(f["trump"]) for f in frames}
    assert len(avatars) == 1 and frames[0]["avatars"], avatars
    assert len(trump) == 1 and len(frames[0]["trump"]) == 2, trump
