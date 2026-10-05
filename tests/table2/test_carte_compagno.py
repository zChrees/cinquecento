"""P93: carte del compagno scoperte e consiglio al tavolo (D46).

Controlla il "Fatto quando" di SCALETTA.md (P93): quando la vista ha le carte del
compagno (partner_hand, P92) il suo ventaglio in alto si scopre (un po' più grande
di quello coperto) e per un momento c'è la scritta "Mazzo finito: ora vedi le carte
di …"; il ventaglio non copre la presa né avatar e nome del compagno, che si sposta
(scelta di Christian del 04/10); toccando una sua carta gliela consigli (segnata,
"premuta" per i lettori di schermo) e toccandola di nuovo il consiglio si toglie;
il consiglio ricevuto (advice) segna la carta nella tua mano con "consiglio di …".
Il segno non è solo un colore (la carta è spostata, e c'è la scritta).

Il tavolo si apre nella prova (/game/prova?demo=2v2) in Chrome o Edge senza
finestra (tests/browser.py), con le viste di app/static/dev/ mandate con l'evento del
browser "demo:state"; nella prova il consiglio non va al server. Non serve MySQL.
"""

import copy
import json
import time
from pathlib import Path

import pytest

from app import create_app
from tests.browser import TEST_COOKIE, Browser, FakeUser, find_browser, running_server

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "app" / "static"
PHONE = (360, 640)
SIZES = [(360, 640), (390, 844), (768, 1024), (1024, 768), (1280, 720), (1440, 900)]
MATE = [{"suit": "denari", "rank": rank} for rank in (1, 3, 7)] + [{"suit": "spade", "rank": 10}, {"suit": "bastoni", "rank": 2}]


def _view(mode):
    return json.loads((STATIC / "dev" / f"vista_{mode}.json").read_text(encoding="utf-8"))


def _endgame(base):
    """La stessa vista a mazzo finito con la briscola, ma ancora senza le carte del compagno."""
    view = copy.deepcopy(base)
    view["trump"] = "coppe"
    view["deck_count"] = 0
    return view


def _with_mate(view, cards=MATE, advice=None):
    view = copy.deepcopy(view)
    view["version"] += 1
    view["partner_hand"] = cards
    view["advice"] = advice
    return view


def test_eventi_nel_posto_dei_nomi():
    events = (STATIC / "js" / "core" / "events.js").read_text(encoding="utf-8")
    assert "GAME_ADVISE: 'game:advise'" in events and "GAME_ADVICE: 'game:advice'" in events
    game = (STATIC / "js" / "pages" / "game.js").read_text(encoding="utf-8")
    assert "EVENTS.GAME_ADVISE" in game and "on(EVENTS.GAME_ADVICE, onAdvice)" in game


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


def _open(browser, server, size=PHONE):
    browser.open(f"{server}/game/prova?demo=2v2", *size, "document.querySelector('[data-mode]') !== null")


def _send(browser, view):
    browser.js("document.querySelector('[data-table]').dispatchEvent("
               f"new CustomEvent('demo:state', {{ detail: {json.dumps(view)} }}))")


def _mate_cards(browser):
    return browser.js("[...document.querySelectorAll('[data-revealed-seat=\"2\"] .card')]"
                      ".map((c) => ({ suit: c.dataset.suit, rank: +c.dataset.rank }))")


RECTS = r"""((selector) => [...document.querySelectorAll(selector)].map((e) => {
  const b = e.getBoundingClientRect(); return { l: b.left, t: b.top, r: b.right, b: b.bottom };
}))"""


def _overlap(a, b):
    return a["l"] < b["r"] and a["r"] > b["l"] and a["t"] < b["b"] and a["b"] > b["t"]


def test_carte_del_compagno_solo_con_partner_hand(browser, server):
    base = _endgame(_view("2v2"))
    _open(browser, server)
    _send(browser, base)
    assert browser.js("document.querySelector('[data-revealed-hand]')") is None
    _send(browser, _with_mate(base))
    assert _mate_cards(browser) == MATE
    # Il compagno non ha più il ventaglio coperto; gli avversari sì, coperti
    sides = browser.js("[...document.querySelectorAll('[data-edge-hand]')].map((e) => e.dataset.edgeHand).sort()")
    assert sides == ["left", "right"]
    assert browser.js("document.querySelectorAll('[data-edge-hand] .card__face').length") == 0
    # Le sue carte sono pulsanti per consigliare, con il nome del compagno
    labels = browser.js("[...document.querySelectorAll('[data-advise-card]')].map((c) => c.getAttribute('aria-label'))")
    assert labels[0] == "Consiglia a Salvo: Asso di denari" and len(labels) == 5
    # Tornate a null (mano nuova), il ventaglio torna coperto
    view = _with_mate(base, None)
    _send(browser, view)
    assert browser.js("document.querySelector('[data-revealed-hand]')") is None


def test_scritta_per_un_momento(browser, server):
    base = _endgame(_view("2v2"))
    _open(browser, server)
    _send(browser, base)
    _send(browser, _with_mate(base))
    assert browser.js("document.querySelector('[data-partner-notice]').textContent") == \
        "Mazzo finito: ora vedi le carte di Salvo"
    start = time.monotonic()
    browser.wait_js("document.querySelector('[data-partner-notice]') === null", "la scritta sparisce", 5)
    assert 1.5 < time.monotonic() - start < 4
    assert _mate_cards(browser) == MATE  # le carte restano scoperte


def test_non_copre_ne_compagno_ne_presa(browser, server):
    base = _endgame(_view("2v2"))
    _open(browser, server)
    _send(browser, base)
    for size in SIZES:
        browser.send("Emulation.setDeviceMetricsOverride", width=size[0], height=size[1], deviceScaleFactor=1, mobile=False)
        browser.wait_js(f"innerWidth === {size[0]} && innerHeight === {size[1]}", f"schermo {size}", 5)
        base["version"] += 2
        _send(browser, base)
        _send(browser, _with_mate(base))
        time.sleep(0.4)  # finita l'entrata del ventaglio
        fan = browser.js(f"{RECTS}('[data-revealed-hand] .card')")
        others = browser.js(f"{RECTS}('.seat--top .seat__avatar, .seat--top .seat__label, [data-trick] .card, .table__leave')")
        for card in fan:
            assert card["l"] >= 0 and card["t"] >= 0 and card["r"] <= size[0], (size, card)
            for other in others:
                assert not _overlap(card, other), (size, "il ventaglio copre qualcosa", card, other)
        scroll = browser.js("[document.scrollingElement.scrollHeight <= innerHeight, "
                            "document.scrollingElement.scrollWidth <= innerWidth]")
        assert scroll == [True, True], (size, "il tavolo scorre")
    # Un po' più grandi del ventaglio coperto degli avversari
    widths = browser.js("[document.querySelector('[data-revealed-hand] .card').offsetWidth, "
                        "document.querySelector('[data-edge-hand] .card').offsetWidth]")
    assert widths[0] > widths[1]


def test_consiglio_dato_si_segna_e_si_toglie(browser, server):
    base = _endgame(_view("2v2"))
    _open(browser, server)
    _send(browser, base)
    _send(browser, _with_mate(base))
    browser.click("[data-advise-card][data-rank='3']")
    marked = browser.js("[...document.querySelectorAll('[data-advised]')].map((c) => [c.dataset.suit, +c.dataset.rank, "
                        "c.getAttribute('aria-pressed'), getComputedStyle(c).translate])")
    assert len(marked) == 1 and marked[0][:3] == ["denari", 3, "true"] and marked[0][3] not in ("none", "0px")
    # Un'altra carta prende il posto della prima
    browser.click("[data-advise-card][data-rank='10']")
    assert browser.js("[...document.querySelectorAll('[data-advised]')].map((c) => +c.dataset.rank)") == [10]
    # La stessa carta toglie il consiglio
    browser.click("[data-advise-card][data-rank='10']")
    assert browser.js("document.querySelector('[data-advised]')") is None
    # Il compagno gioca la carta consigliata: il segno sparisce con la carta
    browser.click("[data-advise-card][data-rank='7']")
    _send(browser, _with_mate(_with_mate(base), [c for c in MATE if c["rank"] != 7]))
    assert browser.js("document.querySelector('[data-advised]')") is None


def test_consiglio_ricevuto_nella_tua_mano(browser, server):
    base = _endgame(_view("2v2"))
    card = base["hand"][2]
    _open(browser, server)
    _send(browser, base)
    _send(browser, _with_mate(base, advice={"seat": 2, "card": card}))
    advised = browser.js("""(() => { const c = document.querySelector('.table__mine .hand [data-advice]');
      return c && { suit: c.dataset.suit, rank: +c.dataset.rank, label: c.getAttribute('aria-label'),
                    text: c.querySelector('.card__advice').textContent }; })()""")
    assert advised["suit"] == card["suit"] and advised["rank"] == card["rank"]
    assert advised["label"].endswith(", consigliata da Salvo")
    assert advised["text"] == "consiglio di Salvo"
    assert browser.js("document.querySelectorAll('.table__mine .hand [data-advice]').length") == 1
    # Consiglio tolto: niente segno
    _send(browser, _with_mate(_with_mate(base), advice=None))
    assert browser.js("document.querySelector('.table__mine .hand [data-advice]')") is None


def test_nel_1v1_niente(browser, server):
    base = _endgame(_view("1v1"))
    browser.open(f"{server}/game/prova?demo=1v1", *PHONE, "document.querySelector('[data-mode]') !== null")
    _send(browser, base)
    assert browser.js("document.querySelector('[data-revealed-hand], [data-partner-notice], [data-advice]')") is None
