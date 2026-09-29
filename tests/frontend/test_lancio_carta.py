"""P70 (primo lotto): lancio della carta e carte che diventano bianche per un attimo.

Controlla quanto chiesto dopo la prova sul telefono (SCALETTA.md, P70): la carta
appena giocata vola al suo posto sul tavolo; finché vola, un tocco sulle proprie
carte non gioca niente; un ridisegno a metà volo non fa ripartire l'animazione, né
l'uscita della presa chiusa; a ogni ridisegno le immagini delle carte sono le stesse
(un'immagine nuova, finché il browser non l'ha pronta, mostra per un attimo il fondo
bianco della carta); con "riduci movimento" niente lancio e niente attesa.

Il tavolo si apre nella prova (/game/prova?demo=1v1) in Chrome o Edge senza finestra
(tests/browser.py), che apre le pagine con "riduci movimento": qui lo si spegne per
vedere le animazioni. Le viste arrivano con l'evento del browser "demo:state". Non
serve MySQL. Se né Chrome né Edge sono installati i controlli nel browser si saltano.
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
PHONE = (360, 640)
TURI_CARD = {"suit": "coppe", "rank": 3}


def test_durata_del_lancio_uguale_nel_css_e_nella_pagina():
    game = (STATIC / "js" / "pages" / "game.js").read_text(encoding="utf-8")
    css = (STATIC / "css" / "components" / "trick.css").read_text(encoding="utf-8")
    ms = int(re.search(r"const THROW_MS = (\d+);", game).group(1))
    seconds = float(re.search(r"animation: card-throw ([\d.]+)s", css).group(1))
    assert ms == round(seconds * 1000)


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


def _view():
    return json.loads((STATIC / "dev" / "vista_1v1.json").read_text(encoding="utf-8"))


def _open(browser, server, motion=True):
    browser.open(f"{server}/game/prova?demo=1v1", *PHONE, "document.querySelector('[data-mode]') !== null")
    if motion:
        browser.send("Emulation.setEmulatedMedia", features=[{"name": "prefers-reduced-motion", "value": "no-preference"}])
        assert browser.js("matchMedia('(prefers-reduced-motion: reduce)').matches") is False


def _send_state(browser, view):
    browser.js("document.querySelector('[data-table]').dispatchEvent("
               f"new CustomEvent('demo:state', {{ detail: {json.dumps(view)} }}))")


def _status(browser):
    return browser.js("document.querySelector('[data-table-status]').textContent")


def _real_click(browser, selector):
    """Un clic vero del mouse al centro di `selector`."""
    point = browser.js(f"""(() => {{
      const b = document.querySelector({json.dumps(selector)}).getBoundingClientRect();
      return {{ x: b.left + b.width / 2, y: b.top + b.height / 2 }};
    }})()""")
    for kind in ("mousePressed", "mouseReleased"):
        browser.send("Input.dispatchMouseEvent", type=kind, x=point["x"], y=point["y"], button="left", clickCount=1)


def _turi_plays(browser):
    """Presa vuota con il turno di Turi, poi Turi gioca il 3 di coppe e tocca a Mario."""
    base = _view()
    empty = copy.deepcopy(base)
    empty["version"] += 1
    empty["trick"] = {"leader_seat": 1, "cards": []}
    empty["turn"] = {"seat": 1, "seconds_total": 30, "seconds_left": 30.0}
    empty["legal"] = {"play": [], "sing": []}
    _send_state(browser, empty)
    played = copy.deepcopy(base)
    played["version"] += 2
    _send_state(browser, played)


def _thrown_progress(browser):
    """A che punto è il lancio in corso (da 0 a 1), o None se nessuna carta vola.
    Con il ritardo negativo di Trick.js conta il progresso, non currentTime."""
    return browser.js("""(() => {
      const card = document.querySelector('[data-trick] [data-thrown]');
      const running = card && card.getAnimations().find((a) => a.animationName === 'card-throw');
      return running ? running.effect.getComputedTiming().progress : null;
    })()""")


def test_la_carta_giocata_vola_al_suo_posto(browser, server):
    _open(browser, server)
    _turi_plays(browser)
    flying = browser.js("""(() => { const c = document.querySelector('[data-trick] [data-thrown]');
      return c && { suit: c.dataset.suit, rank: c.dataset.rank, seat: c.closest('[data-trick-seat]').dataset.trickSeat }; })()""")
    assert flying == {"suit": "coppe", "rank": "3", "seat": "1"}
    assert _thrown_progress(browser) is not None
    # Finito il lancio la carta resta ferma al suo posto
    browser.wait_js("document.querySelector('[data-trick] [data-thrown]') === null", "lancio finito", 3)
    assert browser.js("document.querySelector('[data-trick]').dataset.count") == "1"


def test_durante_il_lancio_le_carte_non_si_giocano(browser, server):
    _open(browser, server)
    _turi_plays(browser)
    assert browser.js("document.querySelector('[data-trick] [data-thrown]') !== null")
    _real_click(browser, ".table__mine .hand button.card")
    assert _status(browser) == ""
    browser.wait_js("document.querySelector('[data-trick] [data-thrown]') === null", "lancio finito", 3)
    _real_click(browser, ".table__mine .hand button.card")
    assert _status(browser).startswith("Prova: hai scelto")


def test_un_ridisegno_a_meta_volo_non_fa_ripartire_il_lancio(browser, server):
    _open(browser, server)
    _turi_plays(browser)
    time.sleep(0.2)
    # Un fumetto ridisegna tutto il tavolo
    browser.js("document.querySelector('[data-table]').dispatchEvent(new CustomEvent('demo:phrases', "
               "{ detail: { phrases: [{ code: 'ciao', text: 'Ciao!' }] } }))")
    browser.js("document.querySelector('[data-table]').dispatchEvent(new CustomEvent('demo:phrase', "
               "{ detail: { seat: 1, code: 'ciao' } }))")
    assert browser.js("document.querySelector('[data-phrase-bubble]') !== null")
    # Dopo 0,2 s su 0,4 il lancio è a metà strada o più, non di nuovo all'inizio
    progress = _thrown_progress(browser)
    assert progress is None or progress >= 0.35, progress


def test_la_presa_chiusa_non_riparte_dopo_un_ridisegno(browser, server):
    _open(browser, server)
    base = _view()
    closed = copy.deepcopy(base)
    closed["version"] += 1
    closed["hand"] = [card for card in closed["hand"] if card != {"suit": "coppe", "rank": 7}]
    closed["players"][0]["cards_in_hand"] = len(closed["hand"])
    closed["last_trick"] = {"winner_seat": 0, "cards": [{"seat": 1, "card": TURI_CARD},
                                                        {"seat": 0, "card": {"suit": "coppe", "rank": 7}}]}
    closed["trick"] = {"leader_seat": 0, "cards": []}
    _send_state(browser, closed)
    # La carta che ha chiuso la presa (il 7 di Mario) vola; quella di Turi era già lì
    thrown = browser.js("[...document.querySelectorAll('[data-last-trick] [data-thrown]')].map((c) => c.dataset.rank)")
    assert thrown == ["7"]
    time.sleep(0.7)
    browser.js("document.querySelector('[data-table]').dispatchEvent(new CustomEvent('demo:phrases', "
               "{ detail: { phrases: [{ code: 'ciao', text: 'Ciao!' }] } }))")
    # L'uscita verso chi ha preso comincia 1,1 s dopo che la presa si vede, non 1,1 s dopo il ridisegno
    delay = browser.js("parseFloat(document.querySelector('[data-last-trick] .trick__card').style.animationDelay)")
    # (su un PC lento il ridisegno arriva più tardi: conta che non sia tornato a 1100)
    assert delay <= 450, delay


def test_a_ogni_ridisegno_le_immagini_delle_carte_restano_le_stesse(browser, server):
    _open(browser, server)
    browser.js("document.querySelectorAll('[data-table] img.card__face, [data-table] img.card__back')"
               ".forEach((img) => { img.dataset.vecchia = 'si'; })")
    base = _view()
    later = copy.deepcopy(base)
    later["version"] += 1
    later["turn"]["seconds_left"] = 20.0
    _send_state(browser, later)
    counts = browser.js("""(() => {
      const imgs = [...document.querySelectorAll('[data-table] img.card__face, [data-table] img.card__back')];
      return { all: imgs.length, old: imgs.filter((img) => img.dataset.vecchia === 'si').length };
    })()""")
    assert counts["all"] > 5 and counts["old"] == counts["all"], counts


def test_con_riduci_movimento_niente_lancio_ne_attesa(browser, server):
    _open(browser, server, motion=False)
    _turi_plays(browser)
    assert browser.js("document.querySelector('[data-thrown]')") is None
    _real_click(browser, ".table__mine .hand button.card")
    assert _status(browser).startswith("Prova: hai scelto")
