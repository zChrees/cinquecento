"""P56: frasi del tavolo nella pagina (pulsante, elenco, fumetto).

Controlla il "Fatto quando" di SCALETTA.md (P56): a 360 px l'elenco delle frasi sta
sullo schermo e il fumetto non copre le carte in mano; il pulsante con sola icona ha
un'etichetta accessibile; il componente non usa innerHTML con dati esterni. In più:
pulsante spento per 3 secondi dopo l'invio, fumetto che sparisce, Esc e tocco fuori
che chiudono l'elenco, frasi anche a partita finita.

Il tavolo si apre nella prova (/game/prova?demo=1v1 o 2v2) in Chrome o Edge senza
finestra (tests/browser.py); il test gli manda l'elenco e le frasi con gli eventi
del browser "demo:phrases" e "demo:phrase", che la pagina accetta solo nella prova.
L'elenco è quello vero del server (app/realtime/table_phrases.py, P55). L'invio al
server (game:send_phrase) lo provano i test di P55 in tests/sockets/. Non serve MySQL.
Il nome del file è diverso da tests/sockets/test_frasi_tavolo.py (P55): con due file
di test con lo stesso nome, un pytest lanciato su tutte le cartelle si fermerebbe.
"""

import json
import time
from pathlib import Path

import pytest

from app import create_app
from app.realtime import table_phrases
from tests.browser import TEST_COOKIE, Browser, FakeUser, find_browser, running_server

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "app" / "static"
PHONE = (360, 640)
PHRASES = table_phrases.phrases_event()
LONGEST = max(PHRASES["phrases"], key=lambda phrase: len(phrase["text"]))


# --- File e pagina -------------------------------------------------------------


def test_css_delle_frasi_nella_pagina_del_tavolo():
    app = create_app("testing")
    app.config["LOGIN_DISABLED"] = True
    client = app.test_client()
    response = client.get("/game/prova?demo=1v1")
    html = response.get_data(as_text=True)
    response.close()
    assert 'href="/static/css/components/table-phrases.css"' in html
    for path in ("/static/css/components/table-phrases.css", "/static/js/components/TablePhrases.js"):
        response = client.get(path)
        assert response.status_code == 200, path
        response.close()


def test_componente_solo_testo_e_niente_copia_delle_frasi():
    code = (STATIC / "js" / "components" / "TablePhrases.js").read_text(encoding="utf-8")
    for forbidden in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write"):
        assert forbidden not in code, forbidden
    # L'elenco arriva solo dal server (game:phrases): nella pagina non c'è una copia
    for path in ("components/TablePhrases.js", "pages/game.js", "components/Table.js"):
        text = (STATIC / "js" / path).read_text(encoding="utf-8")
        for phrase in PHRASES["phrases"]:
            assert phrase["text"] not in text, (path, phrase["code"])


def test_pausa_uguale_al_limite_del_server():
    code = (STATIC / "js" / "pages" / "game.js").read_text(encoding="utf-8")
    assert f"const PHRASE_PAUSE_MS = {table_phrases.MIN_INTERVAL_SECONDS * 1000};" in code


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


def _open(browser, server, mode, size=PHONE, phrases=PHRASES):
    browser.open(f"{server}/game/prova?demo={mode}", *size, "document.querySelector('[data-mode]') !== null")
    if phrases is not None:
        _dispatch(browser, "demo:phrases", phrases)


def _dispatch(browser, name, detail):
    browser.js(f"document.querySelector('[data-table]').dispatchEvent(new CustomEvent({json.dumps(name)}, "
               f"{{ detail: {json.dumps(detail)} }}))")


def _exists(browser, selector):
    return browser.js(f"document.querySelector({json.dumps(selector)}) !== null")


def _view(mode):
    return json.loads((STATIC / "dev" / f"vista_{mode}.json").read_text(encoding="utf-8"))


def _check_fits(browser, selector):
    """`selector` sta nello schermo, non copre le carte in mano, e la pagina non scorre."""
    box = browser.js(f"""(() => {{
      const rect = (e) => {{ const b = e.getBoundingClientRect(); return {{ l: b.left, t: b.top, r: b.right, b: b.bottom }}; }};
      return {{
        items: [...document.querySelectorAll({json.dumps(selector)})].map(rect),
        hand: rect(document.querySelector('.table__mine .hand')),
        w: innerWidth, h: innerHeight,
        scroll: document.scrollingElement.scrollHeight, scrollW: document.scrollingElement.scrollWidth,
      }};
    }})()""")
    assert box["items"], f"{selector} non c'è"
    assert box["scroll"] <= box["h"] and box["scrollW"] <= box["w"], "la pagina scorre"
    hand = box["hand"]
    for item in box["items"]:
        assert item["l"] >= -1 and item["t"] >= -1 and item["r"] <= box["w"] + 1 and item["b"] <= box["h"] + 1, \
            (selector, item, "fuori dallo schermo")
        overlap = item["l"] < hand["r"] and item["r"] > hand["l"] and item["t"] < hand["b"] and item["b"] > hand["t"]
        assert not overlap, (selector, item, hand, "copre la mano")


def test_senza_elenco_niente_pulsante(browser, server):
    _open(browser, server, "2v2", phrases=None)
    assert not _exists(browser, "[data-phrases-button]")


def test_elenco_a_360_px(browser, server):
    _open(browser, server, "2v2")
    button = browser.js("""(() => { const b = document.querySelector('[data-phrases-button]');
      return { label: b.getAttribute('aria-label'), expanded: b.getAttribute('aria-expanded'), disabled: b.disabled }; })()""")
    assert button == {"label": "Frasi", "expanded": "false", "disabled": False}

    browser.click("[data-phrases-button]")
    texts = browser.js("[...document.querySelectorAll('[data-phrases-menu] [data-phrase-code]')].map((p) => p.textContent)")
    assert texts == [phrase["text"] for phrase in PHRASES["phrases"]]
    assert browser.js("document.querySelector('[data-phrases-button]').getAttribute('aria-expanded')") == "true"
    _check_fits(browser, "[data-phrases-menu]")


def test_frase_mandata_fumetto_e_pausa(browser, server):
    _open(browser, server, "2v2")
    browser.click("[data-phrases-button]")
    browser.click("[data-phrase-code='mizzica']")
    assert not _exists(browser, "[data-phrases-menu]")

    bubble = browser.js("""(() => { const b = document.querySelector('[data-seat="0"] [data-phrase-bubble]');
      return b && { text: b.textContent, shown: b.lastChild.textContent }; })()""")
    assert bubble is not None and bubble["shown"] == "Mizzica!"
    assert bubble["text"].endswith(": Mizzica!")  # il nome c'è solo per i lettori di schermo
    _check_fits(browser, "[data-phrase-bubble]")

    # Pulsante spento per 3 secondi dopo l'invio
    start = time.monotonic()
    assert browser.js("document.querySelector('[data-phrases-button]').disabled") is True
    browser.wait_js("!document.querySelector('[data-phrases-button]').disabled", "pulsante di nuovo attivo", 8)
    assert time.monotonic() - start >= 2.5
    # Il fumetto dura 4 secondi dall'invio
    browser.wait_js("document.querySelector('[data-phrase-bubble]') === null", "fumetto sparito", 8)
    assert time.monotonic() - start >= 3.5


def _real_click(browser, selector):
    """Un clic vero del mouse al centro di `selector` (non element.click(), che salta
    i controlli del browser): arriva a quello che c'è davvero sotto il puntatore."""
    point = browser.js(f"""(() => {{
      const b = document.querySelector({json.dumps(selector)}).getBoundingClientRect();
      return {{ x: b.left + b.width / 2, y: b.top + b.height / 2 }};
    }})()""")
    for kind in ("mousePressed", "mouseReleased"):
        browser.send("Input.dispatchMouseEvent", type=kind, x=point["x"], y=point["y"], button="left", clickCount=1)


def test_tocchi_rapidi_una_frase_per_pausa(browser, server):
    # P69: tocchi veri e ripetuti sul pulsante e sulle frasi mandano una sola frase per pausa
    # Una seconda frase partita durante la pausa la farebbe ricominciare: il pulsante
    # resterebbe spento più dei 3 secondi dalla prima
    _open(browser, server, "2v2")
    _real_click(browser, "[data-phrases-button]")
    menu = browser.js("""(() => { const b = document.querySelector("[data-phrase-code='mizzica']").getBoundingClientRect();
      return { x: b.left + b.width / 2, y: b.top + b.height / 2 }; })()""")
    _real_click(browser, "[data-phrase-code='mizzica']")
    start = time.monotonic()
    assert browser.js("document.querySelector('[data-seat=\"0\"] [data-phrase-bubble]').lastChild.textContent") == "Mizzica!"

    # Durante la pausa: tocchi a raffica sul pulsante spento e dove stava la frase
    while time.monotonic() - start < 2.0:
        _real_click(browser, "[data-phrases-button]")
        assert not _exists(browser, "[data-phrases-menu]")
        for kind in ("mousePressed", "mouseReleased"):
            browser.send("Input.dispatchMouseEvent", type=kind, x=menu["x"], y=menu["y"], button="left", clickCount=1)
    assert browser.js("document.querySelector('[data-phrases-button]').disabled") is True

    # Finita la pausa (3 secondi dalla prima frase, non di più) si torna a parlare
    browser.wait_js("!document.querySelector('[data-phrases-button]').disabled", "pulsante di nuovo attivo", 8)
    assert time.monotonic() - start < 3.8
    _real_click(browser, "[data-phrases-button]")
    assert _exists(browser, "[data-phrases-menu]")


def test_fumetti_di_tutti_i_posti_a_360_px(browser, server):
    _open(browser, server, "2v2")
    for seat in range(4):
        _dispatch(browser, "demo:phrase", {"seat": seat, "code": LONGEST["code"]})
    seats = browser.js("[...document.querySelectorAll('[data-phrase-bubble]')].map((b) => b.closest('[data-seat]').dataset.seat)")
    assert sorted(seats) == ["0", "1", "2", "3"]
    _check_fits(browser, "[data-phrase-bubble]")


def test_fumetto_in_alto_nel_1v1(browser, server):
    _open(browser, server, "1v1")
    _dispatch(browser, "demo:phrase", {"seat": 1, "code": LONGEST["code"]})
    assert _exists(browser, "[data-position='top'] [data-phrase-bubble]")
    _check_fits(browser, "[data-phrase-bubble]")


def test_codice_sconosciuto_ignorato(browser, server):
    _open(browser, server, "2v2")
    _dispatch(browser, "demo:phrase", {"seat": 1, "code": "non_esiste"})
    _dispatch(browser, "demo:phrase", {"seat": 9, "code": "ciao"})
    assert not _exists(browser, "[data-phrase-bubble]")


def test_esc_e_tocco_fuori_chiudono(browser, server):
    _open(browser, server, "2v2")
    browser.click("[data-phrases-button]")
    browser.key("Escape", "Escape", 27)
    assert not _exists(browser, "[data-phrases-menu]")
    assert browser.js("document.activeElement.hasAttribute('data-phrases-button')") is True

    browser.click("[data-phrases-button]")
    assert _exists(browser, "[data-phrases-menu]")
    browser.js("document.querySelector('[data-scoreboard]').dispatchEvent(new PointerEvent('pointerdown', { bubbles: true }))")
    assert not _exists(browser, "[data-phrases-menu]")


def test_testo_delle_frasi_come_testo(browser, server):
    _open(browser, server, "2v2", phrases={"phrases": [{"code": "prova", "text": "<img src=x>"}]})
    browser.click("[data-phrases-button]")
    pill = browser.js("""(() => { const p = document.querySelector('[data-phrase-code="prova"]');
      return { text: p.textContent, children: p.children.length }; })()""")
    assert pill == {"text": "<img src=x>", "children": 0}
    _dispatch(browser, "demo:phrase", {"seat": 1, "code": "prova"})
    assert browser.js("document.querySelector('[data-phrase-bubble] img')") is None


def test_frasi_anche_a_partita_finita(browser, server):
    _open(browser, server, "1v1")
    view = _view("1v1")
    view.update({"version": view["version"] + 1, "status": "finished", "turn": None,
                 "legal": {"play": [], "sing": []}})
    view["result"] = {"reason": "abandon", "winner_team": 0, "abandoned_seats": [1], "scores": view["scores"]}
    _dispatch(browser, "demo:state", view)
    assert _exists(browser, "[data-result]")
    assert browser.js("document.querySelector('[data-phrases-button]').disabled") is False
    browser.click("[data-phrases-button]")
    browser.click("[data-phrase-code='bella_partita']")
    assert browser.js("document.querySelector('[data-phrase-bubble]').lastChild.textContent") == "Bella partita!"
