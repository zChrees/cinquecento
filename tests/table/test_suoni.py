"""P103: suoni al tavolo.

I suoni si creano nel browser con Web Audio (core/sounds.js, nessun file audio): la CSP
non cambia. Ogni suono che parte manda sul documento l'evento "cinquecento:sound" con
il suo nome, anche quando il browser non lo fa sentire: i test ascoltano quello.
Controlla che ogni momento abbia il suo suono, nello stesso momento della sua
animazione (lancio e pescate in fila, presa raccolta quando le carte scivolano via,
"tocca a te" dopo le pause e il ticchettio degli ultimi 5 secondi); che con
l'interruttore spento (pagina delle impostazioni, scelta nel browser) non suoni niente,
anche dopo aver ricaricato la pagina; che il tavolo funzioni anche senza Web Audio.

Il tavolo si apre nella prova (/game/prova?demo=1v1) in Chrome o Edge senza finestra
(tests/browser.py), con "riduci movimento" spento dove servono le animazioni; le viste
arrivano con gli eventi del browser "demo:state" e "demo:sang". Non serve MySQL.
"""

import copy
import itertools
import json
import time
from pathlib import Path

import pytest

from app import create_app
from tests.browser import (
    TEST_COOKIE,
    Browser,
    FakeUser,
    find_browser,
    running_server,
    wait,
)

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "app" / "static"
PHONE = (360, 640)

LISTEN = """(() => {
  window.__sounds = [];
  const start = performance.now();
  document.addEventListener('cinquecento:sound', (e) => window.__sounds.push([e.detail.name, Math.round(performance.now() - start)]));
})()"""


def test_niente_file_audio():
    # Tutto sintetizzato: nessun file da scaricare (né licenze, né CSP media-src)
    audio = [p for p in STATIC.rglob("*") if p.suffix.lower() in {".mp3", ".ogg", ".wav", ".m4a", ".webm", ".opus"}]
    assert audio == []
    sounds = (STATIC / "js" / "core" / "sounds.js").read_text(encoding="utf-8")
    assert "new Audio(" not in sounds and "fetch(" not in sounds


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
    view = json.loads((STATIC / "dev" / "vista_1v1.json").read_text(encoding="utf-8"))
    view["version"] += 1
    return view


def _open(browser, server, motion=True):
    browser.open(f"{server}/game/prova?demo=1v1", *PHONE, "document.querySelector('[data-mode]') !== null")
    if motion:
        browser.send("Emulation.setEmulatedMedia", features=[{"name": "prefers-reduced-motion", "value": "no-preference"}])
    browser.js(LISTEN)


def _dispatch(browser, name, detail):
    browser.js(f"document.querySelector('[data-table]').dispatchEvent(new CustomEvent({json.dumps(name)}, "
               f"{{ detail: {json.dumps(detail)} }}))")


def _sounds(browser):
    return browser.js("window.__sounds")


def _wait_sound(browser, name, timeout=8):
    wait(lambda: any(s == name for s, _ in _sounds(browser)), timeout, f"suono {name}")


def _not_my_turn(view):
    view["turn"] = {**view["turn"], "seat": 1}
    view["legal"] = {"play": [], "sing": [], "lay_down": False}
    return view


def _closed_by_me(base, seconds_left):
    """Mario (posto 0) chiude la presa con il 10 di spade e prende; poi si pesca e tocca a lui."""
    view = copy.deepcopy(base)
    view["version"] += 1
    played = {"suit": "spade", "rank": 10}
    view["last_trick"] = {"winner_seat": 0, "cards": base["trick"]["cards"] + [{"seat": 0, "card": played}]}
    view["trick"] = {"leader_seat": 0, "cards": [], "winning_seat": None}
    view["hand"] = [c for c in base["hand"] if c != played] + [{"suit": "denari", "rank": 2}]
    view["deck_count"] = base["deck_count"] - 2
    view["turn"] = {**base["turn"], "seat": 0, "seconds_left": seconds_left}
    return view


def test_presa_chiusa_lancio_pescate_presa_e_tocca_a_te(browser, server):
    base = _not_my_turn(_view())
    _open(browser, server)
    _dispatch(browser, "demo:state", base)
    browser.js("window.__sounds.length = 0")
    _dispatch(browser, "demo:state", _closed_by_me(base, 5.5))
    _wait_sound(browser, "last_tick", 12)
    sounds = _sounds(browser)
    names = [name for name, _ in sounds]
    at = {name: ms for name, ms in reversed(sounds)}  # la prima volta di ogni suono
    assert names[:3] == ["throw", "draw", "draw"], sounds
    # Il lancio subito, le pescate a fine volo (0,55 s, P99) e una dopo l'altra (0,5 s)
    draws = [ms for name, ms in sounds if name == "draw"]
    assert at["throw"] < 150 and 450 <= draws[0] <= 750 and 400 <= draws[1] - draws[0] <= 600, sounds
    # La presa raccolta quando le carte scivolano via (1,1 s)
    assert 1000 <= at["trick"] <= 1350, sounds
    # Tocca a te solo a pause finite (ultima presa 1,5 s, pescate fino a circa 1,55 s)
    assert 1450 <= at["turn"] <= 1900, sounds
    # Ultimi 5 secondi: 4 tic e l'ultimo diverso, un secondo l'uno dall'altro
    ticks = [ms for name, ms in sounds if name in ("tick", "last_tick")]
    assert names.count("tick") == 4 and names[-1] == "last_tick", sounds
    assert all(900 <= b - a <= 1100 for a, b in itertools.pairwise(ticks)), sounds
    assert 400 <= ticks[0] - at["turn"] <= 700, sounds


def test_un_canto_non_ripete_tocca_a_te(browser, server):
    base = _view()  # è il turno di Mario, con il 20 a spade da cantare
    _open(browser, server)
    _dispatch(browser, "demo:state", _not_my_turn(copy.deepcopy(base)))
    _dispatch(browser, "demo:state", {**base, "version": base["version"] + 2})
    _wait_sound(browser, "turn")
    sang = copy.deepcopy(base)
    sang["version"] += 3
    sang["sings"] = base["sings"] + [{"seat": 0, "suit": "spade", "points": 20}]
    sang["legal"] = {**base["legal"], "sing": []}
    _dispatch(browser, "demo:sang", {"seat": 0, "suit": "spade", "points": 20, "cards": [
        {"suit": "spade", "rank": 10}, {"suit": "spade", "rank": 9}], "show_seconds": 3})
    _dispatch(browser, "demo:state", sang)
    _wait_sound(browser, "sing")
    time.sleep(0.5)
    assert [name for name, _ in _sounds(browser)].count("turn") == 1


def test_fine_mano_mescolata_e_distribuzione(browser, server):
    base = _view()
    _open(browser, server)
    _dispatch(browser, "demo:state", _not_my_turn(copy.deepcopy(base)))
    browser.js("window.__sounds.length = 0")
    new_hand = copy.deepcopy(base)
    new_hand["version"] += 1
    new_hand["hand_number"] += 1
    new_hand["last_hand"] = {**base["last_hand"], "hand_number": base["hand_number"]}
    new_hand["trick"] = {"leader_seat": 1, "cards": [], "winning_seat": None}
    _dispatch(browser, "demo:state", new_hand)
    _wait_sound(browser, "hand_end", 4)
    browser.click("[data-hand-summary-close]")  # "Ok" chiude il riepilogo: parte la distribuzione
    _wait_sound(browser, "shuffle", 3)
    # Un suono per carta distribuita: le tue e quelle dell'avversario
    cards = len(new_hand["hand"]) + sum(p["cards_in_hand"] for p in new_hand["players"] if p["seat"] != 0)
    wait(lambda: [n for n, _ in _sounds(browser)].count("deal") == cards, 4, "carte distribuite")
    names = [name for name, _ in _sounds(browser)]
    assert names.index("trick") < names.index("hand_end") < names.index("shuffle") < names.index("deal")


def test_calata(browser, server):
    base = _view()
    _open(browser, server)
    _dispatch(browser, "demo:state", _not_my_turn(copy.deepcopy(base)))
    laid = copy.deepcopy(base)
    laid["version"] += 1
    laid["hand_number"] += 1
    laid["last_hand"] = {**base["last_hand"], "hand_number": base["hand_number"], "laid_down": {
        "seat": 1, "sings": [], "hands": [{"seat": 0, "cards": base["hand"][:2]},
                                          {"seat": 1, "cards": [{"suit": "coppe", "rank": 1}, {"suit": "coppe", "rank": 2}]}]}}
    _dispatch(browser, "demo:state", laid)
    _wait_sound(browser, "lay_down", 3)


@pytest.mark.parametrize(("winner", "sound"), [(0, "win"), (1, "lose"), (None, "tie")])
def test_fine_partita(browser, server, winner, sound):
    base = _view()
    _open(browser, server)
    _dispatch(browser, "demo:state", _not_my_turn(copy.deepcopy(base)))
    browser.js("window.__sounds.length = 0")
    final = _not_my_turn(copy.deepcopy(base))
    final["version"] += 1
    final["status"] = "finished"
    final["result"] = {"reason": "score", "winner_team": winner, "abandoned_seats": [], "scores": [{"team": 0, "score": 510}, {"team": 1, "score": 300}]}
    _dispatch(browser, "demo:state", final)
    _wait_sound(browser, sound, 3)
    assert [name for name, _ in _sounds(browser)] == [sound]


def test_suoni_spenti_anche_dopo_aver_ricaricato(browser, server):
    _open(browser, server)
    browser.js("localStorage.setItem('cinquecento.sounds', 'off')")
    _open(browser, server)  # la pagina ricaricata
    assert browser.js("localStorage.getItem('cinquecento.sounds')") == "off"
    base = _not_my_turn(_view())
    _dispatch(browser, "demo:state", base)
    _dispatch(browser, "demo:state", _closed_by_me(base, 5.5))
    _dispatch(browser, "demo:sang", {"seat": 1, "suit": "denari", "points": 40, "cards": [
        {"suit": "denari", "rank": 10}, {"suit": "denari", "rank": 9}], "show_seconds": 3})
    time.sleep(2.5)
    assert _sounds(browser) == []


def test_tavolo_senza_web_audio(browser, server):
    # Un browser senza Web Audio: niente suoni, ma la pagina va avanti
    browser.send("Page.enable")
    browser.send("Page.addScriptToEvaluateOnNewDocument",
                 source="delete window.AudioContext; delete window.webkitAudioContext;")
    _open(browser, server)
    assert browser.js("typeof window.AudioContext") == "undefined"
    base = _not_my_turn(_view())
    _dispatch(browser, "demo:state", base)
    _dispatch(browser, "demo:state", _closed_by_me(base, 15))
    _wait_sound(browser, "turn", 4)
    assert browser.js("document.querySelectorAll('.table__mine .hand > .card').length") == 5
    assert browser.js("document.querySelector('[data-last-trick]') === null")


def test_interruttore_nelle_impostazioni(browser, server):
    ready = "document.querySelector('[data-sounds-toggle]') !== null"
    browser.open(f"{server}/profile/settings", *PHONE, ready)
    toggle = browser.js("""(() => { const t = document.querySelector('[data-sounds-toggle]');
      return { checked: t.checked, role: t.getAttribute('role'), label: t.closest('label').textContent.trim() }; })()""")
    assert toggle == {"checked": True, "role": "switch", "label": "Suoni al tavolo"}  # accesi all'inizio
    browser.click("[data-sounds-toggle]")
    assert browser.js("localStorage.getItem('cinquecento.sounds')") == "off"
    browser.open(f"{server}/profile/settings", *PHONE, ready)
    assert browser.js("document.querySelector('[data-sounds-toggle]').checked") is False
    browser.click("[data-sounds-toggle]")
    assert browser.js("localStorage.getItem('cinquecento.sounds')") == "on"
