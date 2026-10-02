"""P89: rating dei giocatori al tavolo, da computer.

Controlla il "Fatto quando" di SCALETTA.md (P89): a 1280×720 e 1440×900 (e da
1024 px) ogni giocatore umano ha il suo rating accanto al nome, preso dal campo
rating della vista (P88); il rating provvisorio ha la pillola tratteggiata, e i
lettori di schermo sentono "provvisorio"; senza rating (CPU, null) niente pillola;
sul telefono non si vede; il tavolo non scorre. Che il rating non tocchi le altre
parti del tavolo lo controlla test_tavolo_da_computer (test_grafica_tavolo.py),
che misura le etichette dei giocatori con il rating dentro.

Il tavolo si apre nella prova (/game/prova?demo=1v1 o 2v2) in Chrome o Edge senza
finestra (tests/browser.py), con le viste di app/static/dev/ mandate con l'evento
del browser "demo:state". Non serve MySQL.
"""

import copy
import json
from pathlib import Path

import pytest

from app import create_app
from tests.browser import TEST_COOKIE, Browser, FakeUser, find_browser, running_server

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "app" / "static"

PILLS = r"""[...document.querySelectorAll('.seat')].map((seat) => {
  const pill = seat.querySelector('.seat__title [data-rating]');
  const name = seat.querySelector('.seat__name').getBoundingClientRect();
  if (!pill) return { seat: +seat.dataset.seat, pill: null };
  const b = pill.getBoundingClientRect(); const s = getComputedStyle(pill);
  return { seat: +seat.dataset.seat, pill: { value: +pill.dataset.rating, text: pill.textContent,
    visible: b.width > 0, provisional: pill.hasAttribute('data-provisional'), border: s.borderTopStyle,
    title: pill.title, besideName: b.left >= name.right && b.top < name.bottom && b.bottom > name.top } };
})"""


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


def _open(browser, server, mode, size):
    browser.open(f"{server}/game/prova?demo={mode}", *size, "document.querySelector('[data-mode]') !== null")


def _dispatch(browser, view):
    browser.js(f"document.querySelector('[data-table]').dispatchEvent(new CustomEvent('demo:state', "
               f"{{ detail: {json.dumps(view)} }}))")


@pytest.mark.parametrize("mode", ["1v1", "2v2"])
@pytest.mark.parametrize("size", [(1024, 768), (1280, 720), (1440, 900)], ids=lambda s: f"{s[0]}x{s[1]}")
def test_da_computer_il_rating_accanto_al_nome(browser, server, mode, size):
    base = _view(mode)
    _open(browser, server, mode, size)
    pills = {item["seat"]: item["pill"] for item in browser.js(PILLS)}
    assert set(pills) == {player["seat"] for player in base["players"]}
    for player in base["players"]:
        pill, rating = pills[player["seat"]], player["rating"]
        assert pill is not None and pill["visible"] and pill["besideName"], (player["username"], pill)
        assert pill["value"] == rating["value"] and str(rating["value"]) in pill["text"]
        assert pill["provisional"] is rating["provisional"]
        # Provvisorio: bordo tratteggiato (non solo un colore) e la parola per chi non vede
        assert pill["border"] == ("dashed" if rating["provisional"] else "solid")
        assert ("provvisorio" in pill["text"]) is rating["provisional"]
        assert ("provvisorio" in pill["title"]) is rating["provisional"]
    assert browser.js("document.scrollingElement.scrollHeight <= innerHeight "
                      "&& document.scrollingElement.scrollWidth <= innerWidth")


def test_gli_esempi_hanno_un_rating_provvisorio():
    """Così il test qui sopra prova davvero tutti e due i casi."""
    ratings = [player["rating"] for mode in ("1v1", "2v2") for player in _view(mode)["players"]]
    assert any(r["provisional"] for r in ratings) and any(not r["provisional"] for r in ratings)


def test_senza_rating_niente_pillola(browser, server):
    base = _view("2v2")
    _open(browser, server, "2v2", (1280, 720))
    # La CPU (P68, P88) e chi non ha il rating hanno rating null
    view = copy.deepcopy(base)
    view["version"] += 1
    view["players"][1]["rating"] = None
    _dispatch(browser, view)
    pills = {item["seat"]: item["pill"] for item in browser.js(PILLS)}
    assert pills[1] is None
    assert all(pills[p["seat"]] is not None for p in base["players"] if p["seat"] != 1)


@pytest.mark.parametrize("mode", ["1v1", "2v2"])
@pytest.mark.parametrize("size", [(360, 640), (412, 915), (768, 1024)], ids=lambda s: f"{s[0]}x{s[1]}")
def test_sul_telefono_e_sul_tablet_niente_rating(browser, server, mode, size):
    _open(browser, server, mode, size)
    pills = browser.js(PILLS)
    assert pills and all(item["pill"] is None or not item["pill"]["visible"] for item in pills)
