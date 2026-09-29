"""P57: momenti del tavolo (ultima presa, riepilogo di fine mano, carte del canto).

Controlla il "Fatto quando" di SCALETTA.md (P57): a 360 px ultima presa,
riepilogo e carte del canto stanno nello schermo e non coprono le carte in mano;
le carte del canto spariscono dopo show_seconds; il testo entra sempre come testo;
i tre momenti hanno i loro marcatori data-*.

Il tavolo si apre nella prova (/game/prova?demo=1v1 o 2v2) in Chrome o Edge senza
finestra (tests/browser.py); il test gli manda viste e canti finti con gli eventi
del browser "demo:state" e "demo:sang", che la pagina accetta solo nella prova.
Le viste partono da app/static/dev/vista_*.json. Non serve MySQL. Se né Chrome né
Edge sono installati i controlli nel browser si saltano.
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


def _view(mode):
    return json.loads((STATIC / "dev" / f"vista_{mode}.json").read_text(encoding="utf-8"))


def _card(suit, rank):
    return {"suit": suit, "rank": rank}


# --- File e pagina -------------------------------------------------------------


def test_css_del_riepilogo_nella_pagina_del_tavolo():
    client = create_app("testing").test_client()
    client.application.config["LOGIN_DISABLED"] = True
    response = client.get("/game/prova?demo=1v1")
    html = response.get_data(as_text=True)
    response.close()
    assert 'href="/static/css/components/hand-summary.css"' in html
    for path in ("/static/css/components/hand-summary.css", "/static/js/components/HandSummary.js"):
        response = client.get(path)
        assert response.status_code == 200, path
        response.close()


def test_componenti_solo_testo():
    for path in ("components/HandSummary.js", "components/Table.js", "components/Trick.js", "pages/game.js"):
        code = (STATIC / "js" / path).read_text(encoding="utf-8")
        for forbidden in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write"):
            assert forbidden not in code, (path, forbidden)


def test_eventi_finti_solo_nella_prova():
    code = (STATIC / "js" / "pages" / "game.js").read_text(encoding="utf-8")
    start = code.index("if (demo) {\n  // Solo nella prova")
    block = code[start:code.index("} else {", start)]
    assert "'demo:state'" in block and "'demo:sang'" in block
    assert code.count("addEventListener('demo:") == 4  # più demo:phrases e demo:phrase (P56)


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


def _open(browser, server, mode, size=PHONE):
    browser.open(f"{server}/game/prova?demo={mode}", *size, "document.querySelector('[data-mode]') !== null")


def _send_state(browser, view):
    browser.js("document.querySelector('[data-table]').dispatchEvent("
               f"new CustomEvent('demo:state', {{ detail: {json.dumps(view)} }}))")


def _send_sang(browser, sang):
    browser.js("document.querySelector('[data-table]').dispatchEvent("
               f"new CustomEvent('demo:sang', {{ detail: {json.dumps(sang)} }}))")


def _exists(browser, selector):
    return browser.js(f"document.querySelector({json.dumps(selector)}) !== null")


def _wait_gone(browser, selector, timeout):
    """Aspetta che `selector` sparisca; restituisce i secondi passati."""
    start = time.monotonic()
    browser.wait_js(f"document.querySelector({json.dumps(selector)}) === null", f"sparisce {selector}", timeout)
    return time.monotonic() - start


def _check_fits(browser, selector):
    """`selector` sta nello schermo, non copre le carte in mano, e la pagina non scorre."""
    box = browser.js(f"""(() => {{
      const rect = (e) => {{ const b = e.getBoundingClientRect(); return {{ l: b.left, t: b.top, r: b.right, b: b.bottom }}; }};
      return {{
        items: [...document.querySelectorAll({json.dumps(selector)})].map(rect),
        hand: rect(document.querySelector('.table__mine .hand')),
        w: innerWidth, h: innerHeight,
        scroll: document.scrollingElement.scrollHeight,
      }};
    }})()""")
    assert box["items"], f"{selector} non c'è"
    assert box["scroll"] <= box["h"], "la pagina scorre"
    hand = box["hand"]
    for item in box["items"]:
        assert item["l"] >= -1 and item["t"] >= -1 and item["r"] <= box["w"] + 1 and item["b"] <= box["h"] + 1, \
            (selector, item, "fuori dallo schermo")
        overlap = item["l"] < hand["r"] and item["r"] > hand["l"] and item["t"] < hand["b"] and item["b"] > hand["t"]
        assert not overlap, (selector, item, hand, "copre la mano")


def _trick_closed_1v1(base, winner=0):
    """Mario (posto 0) risponde con il 7 di coppe al 3 di Turi: la presa si chiude."""
    view = copy.deepcopy(base)
    view["version"] += 1
    view["hand"] = [card for card in view["hand"] if card != _card("coppe", 7)]
    view["players"][0]["cards_in_hand"] = len(view["hand"])
    view["last_trick"] = {"winner_seat": winner, "cards": [
        {"seat": 1, "card": _card("coppe", 3)}, {"seat": 0, "card": _card("coppe", 7)}]}
    view["trick"] = {"leader_seat": winner, "cards": []}
    view["turn"] = {"seat": winner, "seconds_total": 30, "seconds_left": 30.0}
    view["legal"] = {"play": list(view["hand"]) if winner == 0 else [], "sing": []}
    return view


def _new_hand(base, hand_number, closing=None):
    """Comincia la mano hand_number: last_hand è quella appena finita; `closing` è la
    presa che l'ha chiusa (last_hand.last_trick, P58). Senza, la forma di prima di P58."""
    view = copy.deepcopy(base)
    view["version"] += 1
    view["hand_number"] = hand_number
    view["last_trick"] = None
    view["trick"] = {"leader_seat": 0, "cards": []}
    view["sings"] = []
    view["trump"] = None
    view["last_hand"] = {"hand_number": hand_number - 1, "teams": [
        {"team": 0, "card_points": 48, "sing_points": 20, "hand_total": 68},
        {"team": 1, "card_points": 72, "sing_points": 40, "hand_total": 112}]}
    if closing is not None:
        view["last_hand"]["last_trick"] = closing
    view["scores"] = [{"team": 0, "total": 273}, {"team": 1, "total": 247}]
    return view


# Presa che chiude la mano nel 1v1: Turi (posto 1) prende con l'Asso di spade
CLOSING_1V1 = {"winner_seat": 1, "cards": [
    {"seat": 0, "card": _card("spade", 4)}, {"seat": 1, "card": _card("spade", 1)}]}


def test_prima_vista_senza_momenti(browser, server):
    # La vista finta ha già last_trick e last_hand: alla prima vista non si mostrano
    _open(browser, server, "1v1")
    assert not _exists(browser, "[data-last-trick]")
    assert not _exists(browser, "[data-hand-summary]")
    assert not _exists(browser, "[data-sang-seat]")


def test_ultima_presa_per_un_momento(browser, server):
    base = _view("1v1")
    _open(browser, server, "1v1")
    _send_state(browser, _trick_closed_1v1(base))

    closed = browser.js("""(() => {
      const t = document.querySelector('[data-last-trick]');
      return t && { winner: t.dataset.winnerSeat, count: t.dataset.count,
        text: t.querySelector('.trick__winner').textContent,
        winnerCard: t.querySelector('.trick__card--winner').dataset.trickSeat };
    })()""")
    assert closed == {"winner": "0", "count": "2", "text": "Prendi tu", "winnerCard": "0"}
    assert not _exists(browser, "[data-trick]")
    _check_fits(browser, "[data-last-trick]")
    # Mentre si vede la presa chiusa la mano resta giocabile
    assert browser.js("document.querySelectorAll('.table__mine .hand button.card:not([disabled])').length") == 4

    elapsed = _wait_gone(browser, "[data-last-trick]", 6)
    assert elapsed >= 1.0
    assert browser.js("document.querySelector('[data-trick]').dataset.count") == "0"


def test_ultima_presa_sparisce_alla_carta_nuova(browser, server):
    base = _view("1v1")
    _open(browser, server, "1v1")
    closed = _trick_closed_1v1(base, winner=1)
    _send_state(browser, closed)
    assert browser.js("document.querySelector('.trick__winner').textContent") == "Prende Turi"

    later = copy.deepcopy(closed)
    later["version"] += 1
    later["trick"] = {"leader_seat": 1, "cards": [{"seat": 1, "card": _card("denari", 5)}]}
    _send_state(browser, later)
    assert not _exists(browser, "[data-last-trick]")
    assert browser.js("document.querySelector('[data-trick]').dataset.count") == "1"


def test_nome_del_vincitore_come_testo(browser, server):
    base = _view("1v1")
    base["players"][1]["username"] = "<img src=x>"
    _open(browser, server, "1v1")
    _send_state(browser, _trick_closed_1v1(base, winner=1))
    assert browser.js("document.querySelector('.trick__winner').textContent") == "Prende <img src=x>"
    assert browser.js("document.querySelector('.trick__winner').children.length") == 0


def test_riepilogo_di_fine_mano_1v1(browser, server):
    base = _view("1v1")
    _open(browser, server, "1v1")
    _send_state(browser, _new_hand(base, 4))

    summary = browser.js("""(() => {
      const s = document.querySelector('[data-hand-summary]');
      const rows = [...s.querySelectorAll('tr')].map((tr) => [...tr.children].map((c) => c.textContent));
      return { number: s.dataset.handNumber, title: s.querySelector('h2').textContent, rows };
    })()""")
    assert summary["number"] == "3" and summary["title"] == "Mano 3 finita"
    assert summary["rows"] == [
        ["", "Tu", "Turi"],
        ["Carte prese", "48", "72"],
        ["Canti", "20", "40"],
        ["Mano", "68", "112"],
        ["Punteggio", "273", "247"],
    ]
    _check_fits(browser, "[data-hand-summary]")
    # La mano non è coperta e resta giocabile
    assert browser.js("document.querySelectorAll('.table__mine .hand button.card:not([disabled])').length") == 5

    browser.click("[data-hand-summary-close]")
    assert not _exists(browser, "[data-hand-summary]")


def test_fine_mano_prima_l_ultima_presa_poi_il_riepilogo(browser, server):
    # P58: la carta che chiude la mano si vede, poi arriva il riepilogo
    base = _view("1v1")
    _open(browser, server, "1v1")
    _send_state(browser, _new_hand(base, 4, closing=CLOSING_1V1))

    closed = browser.js("""(() => {
      const t = document.querySelector('[data-last-trick]');
      return t && { winner: t.dataset.winnerSeat, count: t.dataset.count,
        text: t.querySelector('.trick__winner').textContent,
        winnerCard: t.querySelector('.trick__card--winner').dataset.trickSeat };
    })()""")
    assert closed == {"winner": "1", "count": "2", "text": "Prende Turi", "winnerCard": "1"}
    assert not _exists(browser, "[data-hand-summary]")
    _check_fits(browser, "[data-last-trick]")

    elapsed = _wait_gone(browser, "[data-last-trick]", 6)
    assert elapsed >= 1.0
    assert _exists(browser, "[data-hand-summary][data-hand-number='3']")


def test_fine_mano_carta_nuova_apre_subito_il_riepilogo(browser, server):
    # La mano nuova non aspetta: alla prima carta la presa sparisce e compare il riepilogo
    base = _view("1v1")
    _open(browser, server, "1v1")
    started = _new_hand(base, 4, closing=CLOSING_1V1)
    _send_state(browser, started)
    assert _exists(browser, "[data-last-trick]")

    later = copy.deepcopy(started)
    later["version"] += 1
    later["trick"] = {"leader_seat": 1, "cards": [{"seat": 1, "card": _card("denari", 5)}]}
    _send_state(browser, later)
    assert not _exists(browser, "[data-last-trick]")
    assert _exists(browser, "[data-hand-summary][data-hand-number='3']")
    assert browser.js("document.querySelector('[data-trick]').dataset.count") == "1"


def test_riepilogo_si_chiude_da_solo(browser, server):
    base = _view("2v2")
    _open(browser, server, "2v2")
    _send_state(browser, _new_hand(base, 2))
    heads = browser.js("[...document.querySelectorAll('[data-hand-summary] thead th')].map((c) => c.textContent)")
    assert heads == ["Noi", "Loro"]
    _check_fits(browser, "[data-hand-summary]")
    elapsed = _wait_gone(browser, "[data-hand-summary]", 10)
    assert elapsed >= 4.0


def test_carte_del_canto_per_show_seconds(browser, server):
    _open(browser, server, "2v2")
    # Un canto per ogni posto: tu in basso, 1 a destra, 2 (compagno) in alto, 3 a sinistra
    suits = ["coppe", "denari", "spade", "bastoni"]
    for seat, suit in enumerate(suits):
        _send_sang(browser, {"seat": seat, "suit": suit, "points": 40 if seat == 0 else 20,
                             "cards": [_card(suit, 10), _card(suit, 9)], "show_seconds": 2})
    shown = browser.js("""[...document.querySelectorAll('[data-sang-seat]')].map((s) => ({
      seat: s.dataset.sangSeat, suit: s.dataset.suit, cards: s.querySelectorAll('.card').length,
      text: s.querySelector('.sang__points').textContent }))""")
    assert sorted(shown, key=lambda s: s["seat"]) == [
        {"seat": "0", "suit": "coppe", "cards": 2, "text": "Canta 40"},
        {"seat": "1", "suit": "denari", "cards": 2, "text": "Canta 20"},
        {"seat": "2", "suit": "spade", "cards": 2, "text": "Canta 20"},
        {"seat": "3", "suit": "bastoni", "cards": 2, "text": "Canta 20"},
    ]
    assert "ha cantato 20 a bastoni" in browser.js("document.querySelector('[data-table-status]').textContent")
    _check_fits(browser, "[data-sang-seat]")

    elapsed = _wait_gone(browser, "[data-sang-seat]", 6)
    assert elapsed >= 1.5
    assert browser.js("document.querySelector('[data-table-status]').textContent") == ""


def test_fine_partita_prima_la_presa_poi_il_riepilogo(browser, server):
    base = _view("1v1")
    _open(browser, server, "1v1")
    final = _trick_closed_1v1(base)
    final.update({"status": "finished", "turn": None, "legal": {"play": [], "sing": []}})
    final["last_hand"] = dict(_new_hand(base, 4)["last_hand"], hand_number=base["hand_number"])
    final["result"] = {"reason": "score", "winner_team": 0, "abandoned_seats": [], "scores": final["scores"]}
    _send_state(browser, final)
    assert _exists(browser, "[data-last-trick]") and not _exists(browser, "[data-result]")

    _wait_gone(browser, "[data-last-trick]", 6)
    assert _exists(browser, "[data-result='score'] [data-hand-summary][data-hand-number='3']")
    assert not _exists(browser, "[data-hand-summary-close]")


def test_fine_partita_per_abbandono_senza_riepilogo(browser, server):
    base = _view("1v1")
    _open(browser, server, "1v1")
    final = copy.deepcopy(base)
    final.update({"version": base["version"] + 1, "status": "finished", "turn": None,
                  "legal": {"play": [], "sing": []}})
    final["result"] = {"reason": "abandon", "winner_team": 0, "abandoned_seats": [1], "scores": base["scores"]}
    _send_state(browser, final)
    assert _exists(browser, "[data-result='abandon']")
    assert not _exists(browser, "[data-hand-summary]")
