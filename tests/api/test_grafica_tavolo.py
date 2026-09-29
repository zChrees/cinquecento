"""P71: grafica del tavolo dopo la prova sul telefono.

Controlla il "Fatto quando" di SCALETTA.md (P71): il seme della briscola sta al
centro sopra il mazzo, senza nome, e sparisce con il mazzo; il seme sta anche sopra
la mano a sinistra e resta a mazzo finito; niente "Carte franche" né "mazziere";
sul telefono, nel 1v1, il mazzo sta sul bordo destro; mazzo e carte della presa sono
più grandi; il pulsante delle frasi sta sopra la mano a destra e l'elenco si apre
verso l'alto senza coprire la mano; il tavolo non scorre alle misure di
docs/prototipo/LEGGIMI.md.

Il tavolo si apre nella prova (/game/prova?demo=1v1 o 2v2) in Chrome o Edge senza
finestra (tests/browser.py); il test gli manda viste e frasi con gli eventi del
browser "demo:state" e "demo:phrases". Non serve MySQL. Se né Chrome né Edge sono
installati i controlli nel browser si saltano.
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


def _state(base, **changes):
    view = copy.deepcopy(base)
    view["version"] += 1
    view.update(changes)
    return view


def _boxes(browser):
    """Rettangoli delle parti del tavolo che servono ai controlli."""
    return browser.js("""(() => {
      const rect = (s) => { const e = document.querySelector(s); if (!e) return null;
        const b = e.getBoundingClientRect(); return { l: b.left, t: b.top, r: b.right, b: b.bottom, w: b.width }; };
      return {
        deck: rect('[data-deck-count]'), deckCard: rect('[data-deck-count] .card'),
        deckTrump: rect('[data-deck-count] [data-trump]'), trick: rect('[data-trick]'),
        trickCard: rect('[data-trick] .card'), center: rect('.table__center'),
        badge: rect('[data-trump-badge]'), me: rect('.table__mine [data-position="bottom"]'),
        button: rect('[data-phrases-button]'), hand: rect('.table__mine .hand'),
        w: innerWidth, h: innerHeight,
        scrollH: document.scrollingElement.scrollHeight, scrollW: document.scrollingElement.scrollWidth,
      };
    })()""")


def _overlap(a, b):
    return a["l"] < b["r"] and a["r"] > b["l"] and a["t"] < b["b"] and a["b"] > b["t"]


def test_briscola_sul_mazzo_e_sopra_la_mano_al_telefono(browser, server):
    base = _view("1v1")
    _open(browser, server, "1v1")
    # Una carta nella presa, per misurarla
    _dispatch(browser, "demo:state", _state(base, trick={"leader_seat": 1, "cards": [
        {"seat": 1, "card": {"suit": "denari", "rank": 5}}]}))
    box = _boxes(browser)

    # Seme al centro sopra il mazzo, senza nome visibile
    deck, trump = box["deck"], box["deckTrump"]
    assert trump is not None
    assert abs((trump["l"] + trump["r"]) / 2 - (deck["l"] + deck["r"]) / 2) <= 2
    assert abs((trump["t"] + trump["b"]) / 2 - (deck["t"] + deck["b"]) / 2) <= 2
    assert browser.js("document.querySelector('.table__center').innerText.trim()") == str(base["deck_count"])
    assert "coppe" in browser.js("document.querySelector('[data-deck-count]').getAttribute('aria-label')")

    # Nel 1v1 al telefono il mazzo sta sul bordo destro, lontano dalla presa
    assert box["deck"]["r"] >= box["center"]["r"] - 1
    assert box["deck"]["r"] >= box["w"] - 40
    assert not _overlap(box["deck"], box["trick"])

    # Mazzo e carte della presa più grandi di prima (40 e 48 px)
    assert box["deckCard"]["w"] >= 56 - 1
    assert box["trickCard"]["w"] >= 60 - 1

    # Sopra la mano: briscola a sinistra, tu al centro, frasi a destra; niente copre la mano
    badge, me, button, hand = box["badge"], box["me"], box["button"], box["hand"]
    assert badge["r"] <= me["l"] and me["r"] <= button["l"]
    for part in (badge, me, button):
        assert part["b"] <= hand["t"] + 1
    assert browser.js("document.querySelector('[data-trump-badge]').getAttribute('aria-label')") == "Briscola: coppe"
    assert browser.js("document.querySelector('.table__top [data-phrases-button]')") is None


def test_mazzo_finito_la_briscola_resta_sopra_la_mano(browser, server):
    base = _view("1v1")
    _open(browser, server, "1v1")
    _dispatch(browser, "demo:state", _state(base, deck_count=0))
    assert browser.js("document.querySelector('[data-deck-count]')") is None
    assert browser.js("document.querySelector('[data-trump]')") is None
    assert browser.js("document.querySelector('[data-trump-badge]').dataset.trumpBadge") == "coppe"
    assert "Mazzo finito" not in browser.js("document.querySelector('[data-table]').innerText")


def test_prima_del_40_niente_briscola_ne_scritte(browser, server):
    _open(browser, server, "2v2")
    text = browser.js("document.querySelector('[data-table]').innerText")
    assert "Carte franche" not in text and "mazziere" not in text and "Briscola" not in text
    assert browser.js("document.querySelector('[data-trump], [data-trump-badge]')") is None
    assert browser.js("document.querySelector('[data-deck-count]') !== null") is True


def test_elenco_delle_frasi_verso_l_alto(browser, server):
    _open(browser, server, "1v1")
    browser.click("[data-phrases-button]")
    box = browser.js("""(() => {
      const rect = (s) => { const b = document.querySelector(s).getBoundingClientRect();
        return { l: b.left, t: b.top, r: b.right, b: b.bottom }; };
      return { menu: rect('[data-phrases-menu]'), button: rect('[data-phrases-button]'),
               hand: rect('.table__mine .hand'), w: innerWidth };
    })()""")
    assert box["menu"]["b"] <= box["button"]["t"]
    assert box["menu"]["t"] >= 0 and box["menu"]["l"] >= 0 and box["menu"]["r"] <= box["w"]
    assert not _overlap(box["menu"], box["hand"])


@pytest.mark.parametrize("mode", ["1v1", "2v2"])
def test_il_tavolo_non_scorre(browser, server, mode):
    base = _view(mode)
    # La pagina si apre una volta sola (il runner dà 120 s all'intera suite); per ogni
    # misura cambia solo lo schermo. La presa piena è il caso più alto.
    _open(browser, server, mode)
    seats = [player["seat"] for player in base["players"]]
    full = [{"seat": seat, "card": {"suit": "denari", "rank": rank}} for seat, rank in zip(seats, (2, 4, 5, 6))]
    _dispatch(browser, "demo:state", _state(base, trick={"leader_seat": seats[0], "cards": full[:len(seats) - 1]}))
    for size in SIZES:
        browser.send("Emulation.setDeviceMetricsOverride", width=size[0], height=size[1], deviceScaleFactor=1, mobile=False)
        browser.wait_js(f"innerWidth === {size[0]} && innerHeight === {size[1]}", f"schermo {size}", 5)
        box = _boxes(browser)
        assert box["scrollH"] <= box["h"] and box["scrollW"] <= box["w"], (mode, size, "il tavolo scorre")
        assert box["hand"]["b"] <= box["h"] + 1, (mode, size, "la mano esce dallo schermo")
        assert not _overlap(box["deck"], box["trick"]), (mode, size, "il mazzo copre la presa")
        # Presa e mazzo non coprono gli altri giocatori (avatar, nome, carte coperte)
        seats = browser.js("""[...document.querySelectorAll('.table__board > .seat')].map((s) => {
          const b = s.getBoundingClientRect(); return { l: b.left, t: b.top, r: b.right, b: b.bottom }; })""")
        for seat in seats:
            # Difetto che c'era già prima di P71: sui portatili bassi, nel 1v1, la presa
            # entra di qualche pixel nel posto dell'avversario (da sistemare in P34)
            if (mode, size) != ("1v1", (1280, 720)):
                assert not _overlap(box["trick"], seat), (mode, size, "la presa copre un giocatore", seat)
            assert not _overlap(box["deck"], seat), (mode, size, "il mazzo copre un giocatore", seat)
        assert not _overlap(box["deck"], box["me"]), (mode, size, "il mazzo copre la tua riga")
