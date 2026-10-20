"""Passo 8a della migrazione: il tavolo React (frontend/src/game/) disegnato da una vista.

Controlla, aprendo la prova (/game/prova?demo=1v1 o 2v2) nel tavolo Jinja e poi in
quello React (&ui=react), in Chrome o Edge senza finestra (tests/browser.py):
- la stessa pagina, elemento per elemento (tag, attributi, testi) dentro <main>, per
  la vista finta e per varie viste mandate con l'evento "demo:state": canti e
  "Cala le carte", mazzo finito, avversario CPU e scollegato, fine partita a punti e
  per abbandono, pareggio, nel 2v2 le carte del compagno con il consiglio (anche
  della CPU compagna) e le frasi (elenco aperto e fumetto);
- le stesse risposte della prova quando si tocca una carta, un canto o una carta
  del compagno (riga di stato, carta consigliata);
- le stesse posizioni delle parti del tavolo sul telefono e da computer;
- senza ?demo= il tavolo React aspetta la partita; la CSP non blocca niente.
Le differenze ammesse, che il confronto toglie: il ritardo delle animazioni (il
tempo da quando la pagina è aperta), l'indirizzo delle immagini scritto per intero o
no, data-cards-ready (le immagini precaricate, P79: nel tavolo React dal lotto 8b).
Nel tavolo Jinja le viste nuove fanno partire i "momenti" (P57): le varianti qui
cambiano solo campi che non ne fanno partire, e "riduci movimento" è acceso.
Non serve MySQL. Senza browser, o senza il build della SPA, i test si saltano.
"""

import copy
import json
from pathlib import Path

import pytest

from app import create_app
from app.realtime import table_phrases
from tests.browser import TEST_COOKIE, Browser, FakeUser, find_browser, running_server
from tests.spa import needs_spa

ROOT = Path(__file__).resolve().parents[2]
DEV = ROOT / "app" / "static" / "dev"
JINJA = "/game/prova?demo={mode}"
REACT = "/game/prova?demo={mode}&ui=react"
READY = "document.querySelector('[data-mode]') !== null"
# Come test_csp.py: registra ogni risorsa bloccata dalla CSP
RECORD = (
    "window.__csp = [];"
    "document.addEventListener('securitypolicyviolation',"
    " e => window.__csp.push(e.effectiveDirective + ' ' + e.blockedURI));"
)
# SIGNATURE: ogni elemento di <main> come "profondità tag attributi | testo proprio".
# Attributi in ordine alfabetico (React e utils/dom.js li scrivono in ordini diversi);
# src risolto (img.src: indirizzo intero); style come elenco ordinato di regole, con
# il numero dei ritardi delle animazioni tolto; data-cards-ready saltato.
SIGNATURE = """(() => {
  const out = [];
  function style(value) {
    return value.split(';').map((s) => s.trim()).filter(Boolean)
      .map((s) => s.replace(/^(animation-delay:\\s*)-?\\d+ms$/, '$1Nms')).sort().join('; ');
  }
  function walk(node, depth) {
    for (const child of node.children) {
      const attrs = [...child.attributes].filter((a) => a.name !== 'data-cards-ready').map((a) => {
        if (a.name === 'src') return `src=${child.src}`;
        if (a.name === 'style') return `style=${style(a.value)}`;
        return `${a.name}=${a.value}`;
      }).sort();
      const text = [...child.childNodes].filter((n) => n.nodeType === 3)
        .map((n) => n.textContent).join('').replace(/\\s+/g, ' ').trim();
      out.push(`${depth} ${child.tagName} ${attrs.join(' ')} | ${text}`);
      walk(child, depth + 1);
    }
  }
  walk(document.querySelector('main'), 0);
  return out;
})()"""
# BOXES: i rettangoli delle parti del tavolo, arrotondati al pixel
BOXES = """(() => {
  const out = {};
  const parts = ['.table__top', '[data-leave]', '[data-scoreboard]', '[data-trump-badge]', '.table__center',
    '[data-trick]', '[data-deck-count]', '.table__me', '[data-phrases-button]', '[data-sing-buttons]',
    '.table__mine .hand', '[data-table-status]'];
  for (const seat of document.querySelectorAll('.seat[data-seat]')) parts.push(`.seat[data-seat="${seat.dataset.seat}"]`);
  for (const fan of document.querySelectorAll('[data-edge-hand]')) parts.push(`[data-edge-hand="${fan.dataset.edgeHand}"]`);
  for (const part of parts) {
    const e = document.querySelector(part);
    if (!e) { out[part] = null; continue; }
    const r = e.getBoundingClientRect();
    out[part] = [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)];
  }
  return out;
})()"""


def _view(mode):
    return json.loads((DEV / f"vista_{mode}.json").read_text(encoding="utf-8"))


def _change(base, version, **changes):
    view = copy.deepcopy(base)
    view["version"] = version
    view.update(changes)
    return view


def _player(view, seat, **changes):
    players = copy.deepcopy(view["players"])
    players[seat].update(changes)
    return players


NO_MOVES = {"play": [], "sing": [], "lay_down": False}


def _variants_1v1(base):
    """Le viste del 1v1 da confrontare (nome, vista, azione da fare dopo)."""
    v = base["version"]
    sang = base["sings"] + [{"seat": 0, "suit": "spade", "points": 20}]
    finished = {"status": "finished", "turn": None, "legal": NO_MOVES,
                "last_hand": dict(base["last_hand"], hand_number=base["hand_number"])}
    scores = [{"team": 0, "total": 510}, {"team": 1, "total": 260}]
    return [
        ("vista finta", base, None),
        ("tocco una carta", base, "[data-hand] button.card:not(:disabled)"),
        ("tocco un canto", base, "[data-sing-button]"),
        ("canti e calata", _change(base, v + 1, sings=sang, legal=dict(base["legal"], sing=[], lay_down=True)), None),
        ("tocco cala le carte", _change(base, v + 2, sings=sang, legal=dict(base["legal"], sing=[], lay_down=True)),
         "[data-lay-down-button]"),
        ("cpu scollegata, mazzo finito", _change(
            base, v + 3, deck_count=0, turn=dict(base["turn"], seat=1, seconds_left=4.4), legal=NO_MOVES,
            players=_player(base, 1, cpu=True, avatar=None, rating=None, connected=False,
                            reconnect_seconds_left=30.5)), None),
        ("senza briscola, mazzo finito", _change(base, v + 4, deck_count=0, trump=None, sings=[]), None),
        ("fine partita", _change(base, v + 5, scores=scores,
                                 result={"reason": "score", "winner_team": 0, "abandoned_seats": [], "scores": scores},
                                 **finished), None),
        ("abbandono", _change(base, v + 6, result={"reason": "abandon", "winner_team": 1, "abandoned_seats": [0],
                                                   "scores": base["scores"]}, **finished), None),
    ]


def _variants_2v2(base):
    """Le viste del 2v2 da confrontare (nome, vista, azione da fare dopo)."""
    v = base["version"]
    partner = {"trump": "bastoni", "sings": [{"seat": 2, "suit": "bastoni", "points": 40}], "deck_count": 0,
               "partner_hand": [{"suit": "spade", "rank": 5}, {"suit": "bastoni", "rank": 1},
                                {"suit": "coppe", "rank": 2}],
               "advice": {"seat": 2, "card": base["hand"][2]},
               "turn": dict(base["turn"], seat=0), "legal": dict(NO_MOVES, play=base["hand"])}
    last_hand = {"hand_number": 1, "laid_down": None, "last_trick": base["last_trick"],
                 "teams": [{"team": 0, "card_points": 60, "sing_points": 40, "hand_total": 100},
                           {"team": 1, "card_points": 60, "sing_points": 40, "hand_total": 100}]}
    scores = [{"team": 0, "total": 300}, {"team": 1, "total": 300}]
    return [
        ("vista finta", base, None),
        ("carte del compagno", _change(base, v + 1, **partner), None),
        ("consiglio al compagno", _change(base, v + 1, **partner), "[data-advise-card]"),
        ("consiglio tolto", _change(base, v + 1, **partner), "[data-advised]"),
        ("compagno cpu", _change(base, v + 2, players=_player(base, 2, cpu=True, avatar=None, rating=None),
                                 **partner), None),
        ("pareggio", _change(base, v + 3, status="finished", turn=None, legal=NO_MOVES, last_hand=last_hand,
                             scores=scores,
                             result={"reason": "score", "winner_team": None, "abandoned_seats": [],
                                     "scores": scores}), None),
    ]


VARIANTS = {"1v1": _variants_1v1, "2v2": _variants_2v2}


@pytest.fixture(scope="module")
def server():
    needs_spa()
    with running_server(create_app("testing"), FakeUser("Mario", 12)) as url:
        yield url


@pytest.fixture
def browser(server, tmp_path):
    b = Browser(find_browser(), tmp_path / "chrome")
    b.send("Network.setCookie", name=TEST_COOKIE[0], value=TEST_COOKIE[1], url=server)
    b.send("Page.enable")  # senza, lo script qui sotto non parte con le pagine nuove
    b.send("Page.addScriptToEvaluateOnNewDocument", source=RECORD)
    yield b
    b.close()


def _dispatch(browser, name, detail):
    browser.js(f"document.querySelector('[data-table]').dispatchEvent(new CustomEvent({json.dumps(name)}, "
               f"{{ detail: {json.dumps(detail)} }}))")


def _show(browser, view):
    """Manda la vista e aspetta che il tavolo la disegni (React disegna dopo l'evento)."""
    _dispatch(browser, "demo:state", view)
    browser.wait_js(f"document.querySelector('[data-version]')?.dataset.version === '{view['version']}'",
                    f"vista {view['version']}")
    # P93: nel tavolo Jinja la scritta "Mazzo finito: ora vedi le carte di …" è un
    # momento (2,5 s); il tavolo React la mostra dal lotto 8c
    browser.wait_js("document.querySelector('[data-partner-notice]') === null", "scritta del compagno sparita")


def _signatures(browser, server, page, mode):
    """Apre `page` e restituisce le firme di <main> per ogni variante, nell'ordine."""
    browser.open(f"{server}{page.format(mode=mode)}", 390, 844, READY)
    # La pagina è davvero quella giusta: la SPA ha <div id="root">, il template game.js
    react = browser.js("document.getElementById('root') !== null")
    jinja = browser.js("document.querySelector('script[src$=\"/js/pages/game.js\"]') !== null")
    assert (react, jinja) == ((True, False) if page == REACT else (False, True))
    out = {"inizio": browser.js(SIGNATURE)}
    for name, view, action in VARIANTS[mode](_view(mode)):
        _show(browser, view)
        if action is not None:
            browser.click(action)
            # la risposta della prova è una frase nella riga di stato
            browser.wait_js("document.querySelector('[data-table-status]').textContent !== ''", f"risposta a {name}")
        out[name] = browser.js(SIGNATURE)
    # P56: le frasi; l'elenco aperto e il fumetto di un altro giocatore
    _dispatch(browser, "demo:phrases", table_phrases.phrases_event())
    browser.wait_js("document.querySelector('[data-phrases-button]') !== null", "pulsante delle frasi")
    browser.click("[data-phrases-button]")
    browser.wait_js("document.querySelector('[data-phrases-menu]') !== null", "elenco delle frasi")
    code = table_phrases.phrases_event()["phrases"][0]["code"]
    _dispatch(browser, "demo:phrase", {"seat": 1, "code": code})
    browser.wait_js("document.querySelector('[data-phrase-bubble]') !== null", "fumetto")
    out["frasi"] = browser.js(SIGNATURE)
    assert browser.js("window.__csp") == []
    return out


@pytest.mark.parametrize("mode", ["1v1", "2v2"])
def test_stesso_tavolo_della_versione_jinja(browser, server, mode):
    old = _signatures(browser, server, JINJA, mode)
    new = _signatures(browser, server, REACT, mode)
    assert list(new) == list(old)
    for name in old:
        assert new[name] == old[name], name
    # Le varianti hanno cambiato davvero il tavolo (il confronto non è tra pagine vuote)
    assert len({json.dumps(signature) for signature in old.values()}) >= 5


@pytest.mark.parametrize("mode", ["1v1", "2v2"])
@pytest.mark.parametrize("size", [(360, 640), (1280, 720)])
def test_stesse_posizioni(browser, server, mode, size):
    boxes = []
    for page in (JINJA, REACT):
        browser.open(f"{server}{page.format(mode=mode)}", *size, READY)
        _dispatch(browser, "demo:phrases", table_phrases.phrases_event())
        browser.wait_js("document.querySelector('[data-phrases-button]') !== null", "pulsante delle frasi")
        # I caratteri dei nomi e dei numeri si scaricano quando il tavolo compare (dopo
        # la vista): si misura quando sono pronti, e dopo due disegni del browser
        browser.js("document.fonts.ready.then(() => new Promise((r) => requestAnimationFrame(() => "
                   "requestAnimationFrame(r))))")
        browser.wait_js("document.fonts.status === 'loaded'", "caratteri pronti")
        boxes.append(browser.js(BOXES))
    assert boxes[1] == boxes[0]
    assert boxes[0]["[data-trick]"] is not None and boxes[0][".table__mine .hand"] is not None


def test_senza_demo_aspetta_la_partita(browser, server):
    browser.open(f"{server}/game/a1b2c3d4?ui=react", 390, 844, "document.querySelector('[data-table-message]') !== null")
    page = browser.js("""(() => { const t = document.querySelector('[data-table]');
      return { id: t.dataset.gameId, demo: t.dataset.demoUrl ?? null, text: t.textContent,
               title: document.title, navbar: document.querySelector('.navbar') !== null,
               main: document.querySelector('main').className }; })()""")
    assert page == {"id": "a1b2c3d4", "demo": None, "text": "In attesa della partita…", "title": "Partita · Cinquecento",
                    "navbar": False, "main": "page page--game"}
    assert browser.js("document.getElementById('root') !== null") is True
    assert browser.js("window.__csp") == []
