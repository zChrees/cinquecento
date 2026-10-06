"""P118: mescolata e distribuzione anche alla prima mano della partita.

Controlla il "Fatto quando" di SCALETTA.md (P118) dal lato della pagina: alla prima vista
di una partita appena cominciata (prima mano, nessuna carta giocata né canto, turno ancora
pieno) il mazzo si mescola e le carte arrivano una alla volta, con i suoni; chi ricarica la
pagina nella stessa scheda, o arriva a partita cominciata, non rivede la distribuzione.
Il server che fa partire il primo turno a distribuzione finita è in
tests/sockets/test_turno.py.

Il tavolo si apre nella prova (/game/prova?demo=1v1) in Chrome o Edge senza finestra
(tests/browser.py): la vista di prova la dà il test al posto del file
(app/static/dev/vista_1v1.json), con "riduci movimento" spento prima di aprire la pagina
(la prima vista arriva subito). Non serve MySQL. Se né Chrome né Edge sono installati i
controlli nel browser si saltano.
"""

import copy
import json
from pathlib import Path

import pytest

from app import create_app
from tests.browser import TEST_COOKIE, Browser, FakeUser, find_browser, running_server

ROOT = Path(__file__).resolve().parents[2]
BASE = json.loads((ROOT / "app" / "static" / "dev" / "vista_1v1.json").read_text(encoding="utf-8"))
PHONE = (360, 640)


def fresh_view(game_id="p118-prova", seconds_left=15):
    """Partita appena cominciata: mano 1, 5 carte a testa, mazzo pieno, nessuna carta giocata."""
    view = copy.deepcopy(BASE)
    view.update(game_id=game_id, version=2, hand_number=1, dealer_seat=1, deck_count=30, trump=None,
                sings=[], last_trick=None, last_hand=None,
                trick={"leader_seat": 0, "cards": [], "winning_seat": None})
    view["players"][1]["cards_in_hand"] = 5
    view["turn"] = {"seat": 0, "seconds_total": 15, "seconds_left": seconds_left}
    return view


@pytest.fixture(scope="module")
def server():
    with running_server(create_app("testing"), FakeUser("Mario", 12)) as url:
        yield url


def _browser(server, tmp_path, view):
    b = Browser(find_browser(), tmp_path / "chrome", routes={"*/static/dev/vista_1v1.json*": lambda _: (200, view)})
    b.send("Network.setCookie", name=TEST_COOKIE[0], value=TEST_COOKIE[1], url=server)
    return b


def _open(browser, server):
    """Come Browser.open, ma con le animazioni accese già alla prima vista."""
    browser.send("Emulation.setDeviceMetricsOverride", width=PHONE[0], height=PHONE[1], deviceScaleFactor=1,
                 mobile=False)
    browser.send("Emulation.setEmulatedMedia", features=[{"name": "prefers-reduced-motion", "value": "no-preference"}])
    browser.send("Page.enable")  # addScriptToEvaluateOnNewDocument funziona solo dopo (P91)
    browser.send("Page.addScriptToEvaluateOnNewDocument", source="""
      window.__sounds = window.__sounds || [];
      if (!window.__soundsHeard) {
        window.__soundsHeard = true;
        document.addEventListener('cinquecento:sound', (e) => window.__sounds.push(e.detail.name));
      }""")
    browser.send("Page.navigate", url=f"{server}/game/prova?demo=1v1")
    browser.wait_js("document.readyState === 'complete' && document.querySelector('[data-mode]') !== null",
                    "tavolo di prova")


STATE = """(() => {
  const hand = [...document.querySelectorAll('.table__mine .hand > .card')];
  const fan = document.querySelector('[data-edge-hand="top"]');
  return { dealt: hand.filter((c) => 'dealt' in c.dataset).length, fanDealing: 'dealing' in fan.dataset,
           shuffling: document.querySelector('[data-shuffling]') !== null, sounds: window.__sounds };
})()"""


def test_alla_prima_vista_mescolata_e_distribuzione_poi_non_piu(server, tmp_path):
    browser = _browser(server, tmp_path, fresh_view())
    try:
        _open(browser, server)
        state = browser.js(STATE)
        assert state["shuffling"] and state["fanDealing"] and state["dealt"] == 5, state
        assert state["sounds"][:1] == ["shuffle"]
        # 10 carte, una ogni 80 ms dopo la mescolata: un suono per carta, poi il tavolo è fermo
        browser.wait_js("window.__sounds.filter((s) => s === 'deal').length === 10", "i suoni delle 10 carte")
        browser.wait_js("document.querySelector('.table__mine .hand > .card[data-dealt]') === null",
                        "la fine della distribuzione")
        # Ricaricata nella stessa scheda: la distribuzione non si rivede
        _open(browser, server)
        state = browser.js(STATE)
        assert not state["shuffling"] and not state["fanDealing"] and state["dealt"] == 0, state
        assert "shuffle" not in state["sounds"]
    finally:
        browser.close()


@pytest.mark.parametrize("change", ["tempo_gia_partito", "carta_giocata", "seconda_mano"])
def test_a_partita_cominciata_niente_distribuzione(server, tmp_path, change):
    view = fresh_view(game_id=f"p118-{change}")
    if change == "tempo_gia_partito":
        view["turn"]["seconds_left"] = 11.5
    elif change == "carta_giocata":
        view["trick"] = {"leader_seat": 1, "cards": [{"seat": 1, "card": {"suit": "coppe", "rank": 3}}],
                         "winning_seat": 1}
        view["players"][1]["cards_in_hand"] = 4
    else:
        view["hand_number"] = 2
    browser = _browser(server, tmp_path, view)
    try:
        _open(browser, server)
        state = browser.js(STATE)
        assert not state["shuffling"] and not state["fanDealing"] and state["dealt"] == 0, state
    finally:
        browser.close()
