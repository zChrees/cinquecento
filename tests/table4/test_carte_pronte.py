"""P79: carte bianche per qualche secondo al tavolo.

Prima di P79 l'immagine di una carta si scaricava solo la prima volta che la carta
compariva (pescata, giocata dall'avversario): con una rete lenta, come dal telefono,
la carta restava bianca finché l'immagine non arrivava. Ora il tavolo, appena si
apre, scarica tutte le immagini delle carte (le 40 facce, il dorso e i quattro assi
"figura" di briscola e canti) e lo segnala con data-cards-ready su [data-table].

Qui la rete del browser è rallentata (ogni richiesta aspetta LATENCY_MS): dopo che
il tavolo ha le carte pronte, ogni carta che compare ha già la sua immagine, subito.
Il tavolo si apre nella prova (/game/prova?demo=1v1) in Chrome o Edge senza finestra
(tests/browser.py); le viste arrivano con l'evento del browser "demo:state". Non
serve MySQL. Se né Chrome né Edge sono installati i controlli si saltano.
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
# P91: 300 ms bastano (un'immagine non scaricata prima è bianca nell'istante in cui la
# vista arriva, con qualunque ritardo); con 800 i due test lenti duravano 15 s l'uno
LATENCY_MS = 300
SUITS = ["denari", "coppe", "spade", "bastoni"]

# Immagini del tavolo che non hanno ancora finito di caricarsi (bianche), contate
# nello stesso momento in cui arriva la vista: niente attese
DISPATCH_AND_COUNT = """((view) => {
  const table = document.querySelector('[data-table]');
  table.dispatchEvent(new CustomEvent('demo:state', { detail: view }));
  const imgs = [...table.querySelectorAll('img')];
  return { total: imgs.length,
           white: imgs.filter((img) => !img.complete || img.naturalWidth === 0).map((img) => img.src) };
})"""


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


def _open_slow(browser, server):
    """Apre la prova con la rete lenta e aspetta che le carte siano pronte."""
    browser.send("Network.enable")
    browser.send("Network.emulateNetworkConditions", offline=False, latency=LATENCY_MS,
                 downloadThroughput=-1, uploadThroughput=-1)
    browser.open(f"{server}/game/prova?demo=1v1", *PHONE, "document.querySelector('[data-mode]') !== null", 60)
    browser.wait_js("document.querySelector('[data-table]').dataset.cardsReady === '1'", "carte pronte", 60)


def _send(browser, view):
    return browser.js(f"{DISPATCH_AND_COUNT}({json.dumps(view)})")


def _views_with_every_card():
    """Viste che, una dopo l'altra, mettono in mano e sul tavolo tutte le 40 carte."""
    cards = [{"suit": suit, "rank": rank} for suit in SUITS for rank in range(1, 11)]
    base = _view()
    views = []
    for i in range(0, len(cards), 8):
        view = copy.deepcopy(base)
        view["version"] = base["version"] + 1 + len(views)
        view["hand"] = cards[i:i + 5]
        view["trick"] = {"leader_seat": 1, "cards": [{"seat": 1, "card": cards[i + 5]}], "winning_seat": 1}
        view["last_trick"] = {"winner_seat": 0, "cards": [{"seat": 0, "card": cards[i + 6]},
                                                          {"seat": 1, "card": cards[i + 7]}]}
        view["legal"] = {"play": [], "sing": []}
        views.append(view)
    return views


def test_carte_nuove_mai_bianche_con_la_rete_lenta(browser, server):
    _open_slow(browser, server)
    for view in _views_with_every_card():
        result = _send(browser, view)
        assert result["total"] > 0
        assert result["white"] == []


def test_briscola_e_canto_mai_bianchi_con_la_rete_lenta(browser, server):
    _open_slow(browser, server)
    for suit in SUITS:
        view = _view()
        view["version"] += 1
        view["trump"] = suit
        view["sings"] = [{"seat": 0, "suit": suit, "points": 40}]
        result = _send(browser, view)
        # P108: la briscola sono Cavallo e Re del seme, nell'angolo
        srcs = browser.js("[...document.querySelectorAll('[data-table] img')].map((img) => img.src)")
        assert any(f"cavallo-{suit}.webp" in src for src in srcs) and any(f"re-{suit}.webp" in src for src in srcs)
        assert result["white"] == []


def test_le_carte_pronte_non_aspettano_la_rete(browser, server):
    """Senza rete lenta il segnale arriva comunque (le immagini sono quelle di P35)."""
    browser.open(f"{server}/game/prova?demo=1v1", *PHONE, "document.querySelector('[data-mode]') !== null")
    browser.wait_js("document.querySelector('[data-table]').dataset.cardsReady === '1'", "carte pronte", 15)
