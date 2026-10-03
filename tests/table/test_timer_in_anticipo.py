"""P91: i momenti del tavolo finiscono anche se setTimeout scatta in anticipo.

In Chrome setTimeout a volte scatta poco prima del tempo chiesto (misurato: fino a
circa 0,7 ms, 6 timer su 200). game.js controlla la fine di lanci, pescate,
distribuzione e pausa delle frasi con performance.now(): un timer in anticipo
trovava il momento ancora in corso, e i segni restavano sul tavolo (pulsante delle
frasi spento compreso) fino alla vista successiva; per questo
test_animazioni_in_fila.py falliva a volte ("pescate finite"). Qui ogni timer della
pagina scatta apposta EARLY_MS prima (meno del margine TIMER_SLACK_MS di game.js, ma
abbastanza da battere il ritardo normale di Chrome), così il caso non dipende dalla
fortuna.

Il tavolo si apre nella prova (/game/prova?demo=1v1) in Chrome o Edge senza finestra
(tests/browser.py), con le viste mandate con l'evento "demo:state". Non serve MySQL.
"""

import copy
import json
import re
import time
from pathlib import Path

import pytest

from app import create_app
from app.realtime import table_phrases
from tests.browser import TEST_COOKIE, Browser, FakeUser, find_browser, running_server

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "app" / "static"
GAME = (STATIC / "js" / "pages" / "game.js").read_text(encoding="utf-8")
THROW_MS = int(re.search(r"const THROW_MS = (\d+);", GAME).group(1))
DRAW_MS = int(re.search(r"const DRAW_MS = (\d+);", GAME).group(1))
PAUSE_MS = int(re.search(r"const PHRASE_PAUSE_MS = (\d+);", GAME).group(1))
BUBBLE_MS = int(re.search(r"const BUBBLE_MS = (\d+);", GAME).group(1))
SLACK_MS = int(re.search(r"const TIMER_SLACK_MS = (\d+);", GAME).group(1))
EARLY_MS = 10

EARLY_TIMERS = f"""(() => {{
  const original = window.setTimeout;
  window.setTimeout = (fn, ms, ...args) => original(fn, Math.max(0, (Number(ms) || 0) - {EARLY_MS}), ...args);
}})();"""

SPADE_10 = {"suit": "spade", "rank": 10}


@pytest.fixture(scope="module")
def server():
    with running_server(create_app("testing"), FakeUser("Mario", 12)) as url:
        yield url


@pytest.fixture
def browser(server, tmp_path):
    b = Browser(find_browser(), tmp_path / "chrome")
    b.send("Network.setCookie", name=TEST_COOKIE[0], value=TEST_COOKIE[1], url=server)
    b.send("Page.enable")  # senza, lo script qui sotto non entra nelle pagine
    b.send("Page.addScriptToEvaluateOnNewDocument", source=EARLY_TIMERS)
    yield b
    b.close()


def _view():
    return json.loads((STATIC / "dev" / "vista_1v1.json").read_text(encoding="utf-8"))


def _open(browser, server, motion=True):
    browser.open(f"{server}/game/prova?demo=1v1", 1280, 720, "document.querySelector('[data-mode]') !== null")
    if motion:
        browser.send("Emulation.setEmulatedMedia",
                     features=[{"name": "prefers-reduced-motion", "value": "no-preference"}])
        assert browser.js("matchMedia('(prefers-reduced-motion: reduce)').matches") is False


def _send(browser, view):
    browser.js("document.querySelector('[data-table]').dispatchEvent("
               f"new CustomEvent('demo:state', {{ detail: {json.dumps(view)} }}))")


def _played(base):
    """Mario gioca il 10 di spade sulla carta di Turi: la presa resta aperta (vista finta)."""
    view = copy.deepcopy(base)
    view["version"] = base["version"] + 1
    view["hand"] = [c for c in base["hand"] if c != SPADE_10]
    view["trick"] = {"leader_seat": 1, "cards": base["trick"]["cards"] + [{"seat": 0, "card": SPADE_10}],
                     "winning_seat": 1}
    view["legal"] = {"play": [], "sing": []}
    return view


def test_i_timer_della_pagina_scattano_in_anticipo(browser, server):
    # Il test ha senso solo se il trucco funziona: un timer da 50 ms scatta prima dei 50 ms
    assert EARLY_MS < SLACK_MS
    _open(browser, server, motion=False)
    times = browser.js("""Promise.all([...Array(10)].map(() => new Promise((done) => {
      const t0 = performance.now(); setTimeout(() => done(performance.now() - t0), 50); })))""")
    assert min(times) < 50, times


def test_il_lancio_finisce(browser, server):
    base = _view()
    _open(browser, server)
    _send(browser, _played(base))
    assert browser.js("document.querySelector('[data-trick] [data-thrown]') !== null")
    browser.wait_js("document.querySelector('[data-trick] [data-thrown]') === null", "lancio finito",
                    THROW_MS / 1000 + 0.25)


def test_la_pescata_finisce(browser, server):
    base = _view()
    _open(browser, server)
    # Mario chiude la presa con il 10 di spade, prende e pesca; poi pesca Turi
    closed = copy.deepcopy(base)
    closed["version"] = base["version"] + 1
    closed["trick"] = {"leader_seat": 0, "cards": [], "winning_seat": None}
    closed["last_trick"] = {"winner_seat": 0, "cards": base["trick"]["cards"] + [{"seat": 0, "card": SPADE_10}]}
    closed["hand"] = [c for c in base["hand"] if c != SPADE_10] + [{"suit": "denari", "rank": 2}]
    closed["deck_count"] = base["deck_count"] - 2
    closed["legal"] = {"play": [], "sing": []}
    _send(browser, closed)
    assert browser.js("document.querySelector('[data-drawn], [data-drawing]') !== null")
    browser.wait_js("document.querySelector('[data-thrown], [data-drawn], [data-drawing]') === null",
                    "pescate finite", (THROW_MS + 2 * DRAW_MS) / 1000 + 0.25)


def test_il_pulsante_delle_frasi_si_riaccende(browser, server):
    _open(browser, server, motion=False)
    browser.js("document.querySelector('[data-table]').dispatchEvent(new CustomEvent('demo:phrases', "
               f"{{ detail: {json.dumps(table_phrases.phrases_event())} }}))")
    browser.click("[data-phrases-button]")
    browser.click("[data-phrase-code='mizzica']")
    start = time.monotonic()
    assert browser.js("document.querySelector('[data-phrases-button]').disabled") is True
    # Si riaccende alla fine della pausa, non quando il fumetto sparisce e la pagina si ridisegna
    browser.wait_js("!document.querySelector('[data-phrases-button]').disabled", "pulsante di nuovo attivo",
                    BUBBLE_MS / 1000)
    assert time.monotonic() - start < (PAUSE_MS + BUBBLE_MS) / 2000
