"""P71: grafica del tavolo dopo la prova sul telefono.

Controlla il "Fatto quando" di SCALETTA.md (P71): il seme della briscola sta al
centro sopra il mazzo, senza nome; P77: è l'unico posto dove si vede (niente tondo
sopra la mano) e a mazzo finito il seme resta dov'era il mazzo, con la sua misura,
fino a fine mano; niente "Carte franche" né "mazziere";
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
        points: rect('.table__me-side [data-hand-points]'), me: rect('.table__mine [data-position="bottom"]'),
        button: rect('[data-phrases-button]'), hand: rect('.table__mine .hand'),
        w: innerWidth, h: innerHeight,
        scrollH: document.scrollingElement.scrollHeight, scrollW: document.scrollingElement.scrollWidth,
      };
    })()""")


def _overlap(a, b):
    return a["l"] < b["r"] and a["r"] > b["l"] and a["t"] < b["b"] and a["b"] > b["t"]


def test_briscola_solo_sul_mazzo_al_telefono(browser, server):
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

    # Mazzo e carte della presa più grandi di prima (40 e 48 px); P86 ingrandisce il
    # mazzo solo da computer: sul telefono resta da 56 px
    assert abs(box["deckCard"]["w"] - 56) <= 1
    assert box["trickCard"]["w"] >= 60 - 1

    # P77: la briscola si vede una volta sola, sul mazzo; niente tondo vicino alla mano
    assert browser.js("document.querySelectorAll('[data-trump]').length") == 1
    assert browser.js("document.querySelector('[data-trump-badge], .trump-badge')") is None

    # Sopra la mano: i tuoi punti a sinistra, tu al centro, frasi a destra; niente copre la mano
    points, me, button, hand = box["points"], box["me"], box["button"], box["hand"]
    assert points["r"] <= me["l"] and me["r"] <= button["l"]
    for part in (points, me, button):
        assert part["b"] <= hand["t"] + 1
    assert browser.js("document.querySelector('.table__top [data-phrases-button]')") is None


@pytest.mark.parametrize("mode", ["1v1", "2v2"])
@pytest.mark.parametrize("size", [(360, 640), (1280, 720)], ids=lambda s: f"{s[0]}x{s[1]}")
def test_mazzo_finito_resta_il_seme_dov_era_il_mazzo(browser, server, mode, size):
    base = _view(mode)
    _open(browser, server, mode, size)
    trumped = _state(base, trump="denari", sings=[{"seat": 0, "suit": "denari", "points": 40}])
    _dispatch(browser, "demo:state", trumped)
    deck = _boxes(browser)["deck"]
    _dispatch(browser, "demo:state", _state(trumped, deck_count=0))
    empty = browser.js("""(() => { const e = document.querySelector('[data-deck-empty]');
      const t = e.querySelector('[data-trump]'); const b = e.getBoundingClientRect(); const r = t.getBoundingClientRect();
      return { l: b.left, t: b.top, r: b.right, b: b.bottom, trump: t.dataset.trump, label: e.getAttribute('aria-label'),
               trumpShown: r.width > 0 && getComputedStyle(t).visibility === 'visible',
               slotShown: getComputedStyle(e.querySelector('.card')).visibility !== 'hidden' }; })()""")
    assert browser.js("document.querySelector('[data-deck-count]')") is None
    # Stesso posto e stessa misura del mazzo; si vede solo il seme
    for side in ("l", "t", "r", "b"):
        assert abs(empty[side] - deck[side]) <= 1, side
    assert empty["trump"] == "denari" and empty["trumpShown"] is True and empty["slotShown"] is False
    assert empty["label"] == "Mazzo finito. Briscola: denari"
    assert browser.js("document.querySelectorAll('[data-trump]').length") == 1
    assert "Mazzo finito" not in browser.js("document.querySelector('[data-table]').innerText")


# P74: le parti del tavolo da computer, ciascuna come elenco di rettangoli
DESKTOP_PARTS = r"""(() => {
  const rects = (s) => [...document.querySelectorAll(s)].map((e) => {
    const b = e.getBoundingClientRect(); return { l: b.left, t: b.top, r: b.right, b: b.bottom, w: b.width }; });
  const parts = {
    leave: rects('[data-leave]'), scoreboard: rects('[data-scoreboard]'),
    trick: rects('[data-trick] .card'), deck: rects('[data-deck-count] .card'),
    hand: rects('.table__mine .hand .card'), sing: rects('[data-sing-button]'),
    phrasesButton: rects('[data-phrases-button]'),
  };
  for (const fan of document.querySelectorAll('[data-edge-hand]')) {
    parts[`fan-${fan.dataset.edgeHand}`] = rects(`[data-edge-hand="${fan.dataset.edgeHand}"] > .card`);
  }
  for (const seat of document.querySelectorAll('.seat')) {
    const p = seat.dataset.position;
    parts[`avatar-${p}`] = [...seat.querySelectorAll('.seat__avatar > .avatar')].map((e) => {
      const b = e.getBoundingClientRect(); return { l: b.left, t: b.top, r: b.right, b: b.bottom, w: b.width }; });
    parts[`label-${p}`] = [...seat.querySelectorAll(':scope > .seat__label')].map((e) => {
      const b = e.getBoundingClientRect(); return { l: b.left, t: b.top, r: b.right, b: b.bottom, w: b.width }; });
    parts[`bubble-${p}`] = [...seat.querySelectorAll('.phrase-bubble')].map((e) => {
      const b = e.getBoundingClientRect(); return { l: b.left, t: b.top, r: b.right, b: b.bottom, w: b.width }; });
  }
  for (const points of document.querySelectorAll('[data-hand-points]')) {
    const where = points.closest('.table__me-side') ? 'me' : points.closest('.seat').dataset.position;
    parts[`points-${where}`] = [points].map((e) => {
      const b = e.getBoundingClientRect(); return { l: b.left, t: b.top, r: b.right, b: b.bottom, w: b.width }; });
  }
  return { parts, w: innerWidth, h: innerHeight,
           scrollH: document.scrollingElement.scrollHeight, scrollW: document.scrollingElement.scrollWidth };
})()"""


def _span(rects):
    """Il rettangolo che contiene tutti quelli dell'elenco."""
    return {"l": min(r["l"] for r in rects), "t": min(r["t"] for r in rects),
            "r": max(r["r"] for r in rects), "b": max(r["b"] for r in rects)}


@pytest.mark.parametrize("mode", ["1v1", "2v2"])
@pytest.mark.parametrize("size", [(1024, 768), (1280, 720), (1440, 900)], ids=lambda s: f"{s[0]}x{s[1]}")
def test_tavolo_da_computer(browser, server, mode, size):
    base = _view(mode)
    _open(browser, server, mode, size)
    view = _state(base)
    for player in view["players"]:
        if player["seat"] != view["you"]["seat"]:
            player["cards_in_hand"] = 5
    _dispatch(browser, "demo:state", view)
    # Un fumetto per ogni giocatore, con la frase più lunga
    longest = max(table_phrases.phrases_event()["phrases"], key=lambda p: len(p["text"]))
    for player in view["players"]:
        _dispatch(browser, "demo:phrase", {"seat": player["seat"], "code": longest["code"]})
    box = browser.js(DESKTOP_PARTS)
    parts, w = box["parts"], box["w"]
    assert box["scrollH"] <= box["h"] and box["scrollW"] <= w

    # "Esci" nell'angolo in alto a sinistra, il tabellone in quello in alto a destra
    leave, scoreboard = parts["leave"][0], parts["scoreboard"][0]
    assert leave["l"] <= 24 and leave["t"] <= 24
    assert scoreboard["r"] >= w - 32 and scoreboard["t"] <= 24

    # Carte degli avversari da 72 px (larghezza della carta, non del rettangolo ruotato)
    widths = browser.js("[...document.querySelectorAll('[data-edge-hand] > .card')].map((c) => c.offsetWidth)")
    assert widths and all(width == 72 for width in widths)

    # P86: mazzo da 88 px (prima 60), più grande delle carte della presa e lontano da tutto
    assert browser.js("document.querySelector('[data-deck-count] > .card').offsetWidth") == 88

    # Ogni avversario accanto al suo ventaglio: in alto a sinistra, ai lati verso il centro
    top_fan, top_avatar = _span(parts["fan-top"]), parts["avatar-top"][0]
    top_seat = browser.js("""(() => { const b = document.querySelector('.seat--top').getBoundingClientRect();
      return { l: b.left, r: b.right }; })()""")
    assert top_avatar["r"] <= parts["label-top"][0]["l"]   # punti, avatar, nome, poi le carte
    assert top_seat["r"] <= top_fan["l"] <= top_seat["r"] + 40
    assert top_avatar["t"] < top_fan["b"]
    if mode == "2v2":
        left_fan, right_fan = _span(parts["fan-left"]), _span(parts["fan-right"])
        assert left_fan["r"] <= parts["avatar-left"][0]["l"] <= left_fan["r"] + 40
        assert right_fan["l"] - 40 <= parts["avatar-right"][0]["r"] <= right_fan["l"]

    # Il tuo avatar a sinistra della mano, i tuoi punti a destra, alla stessa altezza
    hand = _span(parts["hand"])
    me, points = parts["avatar-bottom"][0], parts["points-me"][0]
    assert me["r"] <= hand["l"] and hand["r"] <= points["l"]
    for part in (me, points):
        assert hand["t"] <= (part["t"] + part["b"]) / 2 <= hand["b"]

    # Niente si sovrappone: ogni coppia di parti diverse
    names = [name for name in parts if parts[name]]
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            for ra in parts[a]:
                for rb in parts[b]:
                    assert not _overlap(ra, rb), f"{a} tocca {b}"


@pytest.mark.parametrize("mode", ["1v1", "2v2"])
@pytest.mark.parametrize("size", [(1024, 768), (1280, 720), (1440, 900)], ids=lambda s: f"{s[0]}x{s[1]}")
def test_da_computer_la_mano_non_aspetta_le_immagini(browser, server, mode, size):
    """Da computer la mano sta in una colonna larga quanto il suo contenuto (P74): prima
    che arrivassero le immagini le carte erano larghe 27 px e presa e mazzo stavano più
    in basso, poi saltavano su (e il test del mazzo finito falliva una volta su sei)."""
    browser.send("Network.enable")
    browser.send("Network.setBlockedURLs", urls=["*/img/cards/*"])
    _open(browser, server, mode, size)
    # Le immagini delle carte in mano non sono arrivate davvero
    assert browser.js("[...document.querySelectorAll('.table__mine .hand img')].every((i) => i.naturalWidth === 0)")
    widths = browser.js("[...document.querySelectorAll('.table__mine .hand > .card')].map((c) => c.offsetWidth)")
    # --hand-card-max di table.css: 13% dell'altezza, tra 60 e 104 px
    expected = min(max(60, size[1] * 0.13), 104)
    assert widths and all(abs(width - expected) <= 1 for width in widths), (widths, expected)


def test_mazzo_finito_senza_briscola_niente(browser, server):
    base = _view("2v2")
    _open(browser, server, "2v2")
    _dispatch(browser, "demo:state", _state(base, deck_count=0))
    assert browser.js("document.querySelector('[data-deck-count], [data-deck-empty], [data-trump]')") is None


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
            # Prima di P70 (secondo lotto), sui portatili bassi nel 1v1, la presa entrava nel
            # posto dell'avversario: le sue carte coperte ora sono al bordo dello schermo
            assert not _overlap(box["trick"], seat), (mode, size, "la presa copre un giocatore", seat)
            assert not _overlap(box["deck"], seat), (mode, size, "il mazzo copre un giocatore", seat)
        assert not _overlap(box["deck"], box["me"]), (mode, size, "il mazzo copre la tua riga")
