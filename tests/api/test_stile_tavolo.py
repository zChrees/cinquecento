"""P87: "Esci", tabellone e punti della mano in vetro scuro.

Controlla il "Fatto quando" di SCALETTA.md (P87): "Esci", il tabellone (da computer)
e i punti della mano hanno lo stile scelto da Christian (vetro scuro: fondo
semitrasparente con i colori --glass di variables.css, sfocatura, bordo sottile,
scritte senza rilievo), si leggono bene (contrasto almeno 4,5:1, calcolato sul
punto più chiaro del panno) e hanno ancora l'etichetta per i lettori di schermo.
Dove stanno lo controllano i test di P74 e P90 (test_grafica_tavolo.py,
test_tavolo_telefono.py), che restano com'erano.

Il tavolo si apre nella prova (/game/prova?demo=1v1 o 2v2) in Chrome o Edge senza
finestra (tests/browser.py). Non serve MySQL.
"""

import re

import pytest

from app import create_app
from tests.browser import TEST_COOKIE, Browser, FakeUser, find_browser, running_server

STYLES = r"""(() => {
  const root = getComputedStyle(document.documentElement);
  const look = (e) => { const s = getComputedStyle(e);
    return { bg: s.backgroundColor, color: s.color, blur: s.backdropFilter, border: s.borderTopStyle,
             shadow: s.textShadow, label: e.getAttribute('aria-label'), text: e.textContent.trim() }; };
  const one = (s) => { const e = document.querySelector(s); return e ? look(e) : null; };
  const probe = document.createElement('div'); probe.style.color = root.getPropertyValue('--glass'); document.body.append(probe);
  const glass = getComputedStyle(probe).color; probe.style.color = root.getPropertyValue('--felt-light');
  const felt = getComputedStyle(probe).color; probe.remove();
  return { glass, felt, leave: one('[data-leave]'), scoreboard: one('[data-scoreboard]'),
           mine: one('.table__me-side [data-hand-points]'),
           others: [...document.querySelectorAll('.seat [data-hand-points]')].map(look),
           scoreTotals: [...document.querySelectorAll('[data-scoreboard] .score__total')].map(look) };
})()"""


def _rgba(text):
    parts = [float(x) for x in re.findall(r"[\d.]+", text)]
    return parts[:3], (parts[3] if len(parts) > 3 else 1.0)


def _over(top, bottom):
    """Il colore `top` (con trasparenza) sopra il colore pieno `bottom`."""
    (rgb, alpha), (under, _) = _rgba(top), _rgba(bottom)
    return [alpha * a + (1 - alpha) * b for a, b in zip(rgb, under)]


def _luminance(rgb):
    def channel(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast(a, b):
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


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


def _check_glass(part, styles, where):
    assert part is not None, where
    assert part["bg"].replace(" ", "") == styles["glass"].replace(" ", ""), (where, part["bg"])
    assert "blur" in part["blur"] and part["border"] == "solid" and part["shadow"] == "none", (where, part)
    # Il testo si legge anche dove il panno è più chiaro (sotto la lampada)
    background = _over(part["bg"], styles["felt"])
    assert _contrast(_rgba(part["color"])[0], background) >= 4.5, (where, part["color"])


@pytest.mark.parametrize("mode", ["1v1", "2v2"])
@pytest.mark.parametrize("size", [(360, 640), (1280, 720)], ids=lambda s: f"{s[0]}x{s[1]}")
def test_vetro_scuro_che_si_legge(browser, server, mode, size):
    browser.open(f"{server}/game/prova?demo={mode}", *size, "document.querySelector('[data-mode]') !== null")
    styles = browser.js(STYLES)
    _check_glass(styles["leave"], styles, (mode, size, "Esci"))
    _check_glass(styles["mine"], styles, (mode, size, "i tuoi punti"))
    assert styles["others"], (mode, size, "punti degli avversari")
    for points in styles["others"]:
        _check_glass(points, styles, (mode, size, "punti degli avversari"))
    # I tuoi punti in giallo, come il tuo totale nel tabellone; quelli degli altri no
    assert styles["mine"]["color"] != styles["others"][0]["color"]
    # Etichette per i lettori di schermo: "Esci" anche quando si vede solo l'icona (P90)
    assert "Esci" in styles["leave"]["text"] or "Esci" in (styles["leave"]["label"] or "")
    assert styles["mine"]["label"]
    if size[0] >= 1024:
        _check_glass(styles["scoreboard"], styles, (mode, size, "tabellone"))
        background = _over(styles["scoreboard"]["bg"], styles["felt"])
        for total in styles["scoreTotals"]:
            assert _contrast(_rgba(total["color"])[0], background) >= 4.5, (mode, "totale del tabellone", total)
