"""P71: grafica del tavolo dopo la prova sul telefono.

Controlla il "Fatto quando" di SCALETTA.md (P71); P102 e P108 (cambiano P77): la
briscola si vede solo in alto a destra, con Cavallo e Re del seme a ventaglio (sul
telefono simmetrici a "Esci" e alti come lui, da computer a sinistra del tabellone),
non più sopra il mazzo; a mazzo finito al posto del mazzo resta uno spazio vuoto
della sua misura; niente "Carte franche" né "mazziere";
sul telefono, nel 1v1, il mazzo sta sul bordo destro (P100: 64 px); da computer, nel
1v1, sotto la pillola "Frasi" e la presa al centro; mazzo e carte della presa sono
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


def _badge(browser):
    """P102: il tondo della briscola, con "Esci", il ventaglio e il posto in alto."""
    return browser.js("""(() => {
      const rect = (e) => { if (!e) return null; const b = e.getBoundingClientRect();
        return { l: b.left, t: b.top, r: b.right, b: b.bottom, w: b.width }; };
      const e = document.querySelector('[data-trump-badge]'); if (!e) return null;
      return { ...rect(e), suit: e.dataset.trumpBadge, label: e.getAttribute('aria-label'),
               cards: [...e.querySelectorAll('img')].map((i) => i.getAttribute('src').split('/').pop()),
               leave: rect(document.querySelector('[data-leave]')),
               fan: rect(document.querySelector('[data-edge-hand="top"]')),
               seat: rect(document.querySelector('.table__board [data-position="top"]')),
               scoreboard: rect(document.querySelector('[data-scoreboard]')) };
    })()""")


def _overlap(a, b):
    return a["l"] < b["r"] and a["r"] > b["l"] and a["t"] < b["b"] and a["b"] > b["t"]


def test_briscola_nell_angolo_al_telefono(browser, server):
    base = _view("1v1")
    _open(browser, server, "1v1")
    # Una carta nella presa, per misurarla
    _dispatch(browser, "demo:state", _state(base, trick={"leader_seat": 1, "cards": [
        {"seat": 1, "card": {"suit": "denari", "rank": 5}}]}))
    box = _boxes(browser)

    # P108: sul mazzo solo il numero di carte, niente seme né nome della briscola
    assert box["deckTrump"] is None
    assert browser.js("document.querySelector('.table__center').innerText.trim()") == str(base["deck_count"])
    assert browser.js("document.querySelector('[data-deck-count]').getAttribute('aria-label')") == f"Mazzo: {base['deck_count']} carte"

    # Nel 1v1 al telefono il mazzo sta sul bordo destro, lontano dalla presa
    assert box["deck"]["r"] >= box["center"]["r"] - 1
    assert box["deck"]["r"] >= box["w"] - 40
    assert not _overlap(box["deck"], box["trick"])

    # Mazzo e carte della presa più grandi di prima (40 e 48 px); P86 ingrandisce il
    # mazzo da computer; P100: sul telefono, nel 1v1, 64 px (prima 56)
    assert abs(box["deckCard"]["w"] - 64) <= 1
    assert box["trickCard"]["w"] >= 60 - 1

    # P102, P108: in alto a destra, simmetrica a "Esci" e alta come lui: Cavallo e Re del seme
    assert browser.js("document.querySelector('[data-trump]')") is None
    badge = _badge(browser)
    assert badge["suit"] == base["trump"] and badge["label"] == f"Briscola: {base['trump']}"
    assert badge["cards"] == [f"cavallo-{base['trump']}.webp", f"re-{base['trump']}.webp"]
    assert badge["b"] - badge["t"] == pytest.approx(badge["leave"]["b"] - badge["leave"]["t"], abs=1)
    assert badge["r"] == pytest.approx(box["w"] - badge["leave"]["l"], abs=1)
    assert (badge["t"] + badge["b"]) / 2 == pytest.approx((badge["leave"]["t"] + badge["leave"]["b"]) / 2, abs=1)
    for part in ("fan", "seat"):
        assert not _overlap(badge, badge[part]), part

    # Sopra la mano: i tuoi punti a sinistra, tu al centro, frasi a destra; niente copre la mano
    points, me, button, hand = box["points"], box["me"], box["button"], box["hand"]
    assert points["r"] <= me["l"] and me["r"] <= button["l"]
    for part in (points, me, button):
        assert part["b"] <= hand["t"] + 1
    assert browser.js("document.querySelector('.table__top [data-phrases-button]')") is None


@pytest.mark.parametrize("mode", ["1v1", "2v2"])
@pytest.mark.parametrize("size", [(360, 640), (1280, 720)], ids=lambda s: f"{s[0]}x{s[1]}")
def test_mazzo_finito_resta_lo_spazio_e_il_tondo(browser, server, mode, size):
    # P102 (cambia P77): a mazzo finito il seme sul mazzo sparisce, resta il tondo
    base = _view(mode)
    _open(browser, server, mode, size)
    trumped = _state(base, trump="denari", sings=[{"seat": 0, "suit": "denari", "points": 40}])
    _dispatch(browser, "demo:state", trumped)
    before = _boxes(browser)
    badge = _badge(browser)
    _dispatch(browser, "demo:state", _state(trumped, deck_count=0))
    empty = browser.js("""(() => { const e = document.querySelector('[data-deck-empty]');
      const b = e.getBoundingClientRect();
      return { l: b.left, t: b.top, r: b.right, b: b.bottom, hidden: e.getAttribute('aria-hidden'),
               slotShown: getComputedStyle(e.querySelector('.card')).visibility !== 'hidden' }; })()""")
    assert browser.js("document.querySelector('[data-deck-count]')") is None
    # Uno spazio vuoto dov'era il mazzo, della stessa misura; niente seme
    for side in ("l", "t", "r", "b"):
        assert abs(empty[side] - before["deck"][side]) <= 1, side
    assert empty["slotShown"] is False and empty["hidden"] == "true"
    assert browser.js("document.querySelector('[data-trump]')") is None
    # Il tondo resta uguale e la presa non si sposta
    after = _badge(browser)
    trick = _boxes(browser)["trick"]
    assert after["suit"] == "denari"
    for side in ("l", "t", "r", "b"):
        assert abs(after[side] - badge[side]) <= 1, side
        assert abs(trick[side] - before["trick"][side]) <= 1, side
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
    assert browser.js("document.querySelector('[data-deck-count], [data-deck-empty], [data-trump], [data-trump-badge]')") is None


def test_prima_del_40_niente_briscola_ne_scritte(browser, server):
    _open(browser, server, "2v2")
    text = browser.js("document.querySelector('[data-table]').innerText")
    assert "Carte franche" not in text and "mazziere" not in text and "Briscola" not in text
    assert browser.js("document.querySelector('[data-trump], [data-trump-badge]')") is None
    assert browser.js("document.querySelector('[data-deck-count]') !== null") is True


MENU_PARTS = """(() => {
  const rect = (s) => { const e = document.querySelector(s); if (!e) return null; const b = e.getBoundingClientRect();
    return { l: b.left, t: b.top, r: b.right, b: b.bottom }; };
  return { menu: rect('[data-phrases-menu]'), button: rect('[data-phrases-button]'), me: rect('.table__me'),
           mine: rect('.table__mine'), hand: rect('.table__mine .hand'), trick: rect('[data-trick]'),
           deck: rect('.deck'), fan: rect('[data-edge-hand="top"]'), top: rect('.table__board [data-position="top"]'),
           left: rect('.table__board [data-position="left"]'), right: rect('.table__board [data-position="right"]'),
           w: innerWidth, h: innerHeight, scroll: document.scrollingElement.scrollHeight,
           scrolls: getComputedStyle(document.querySelector('[data-phrases-menu]')).overflowY };
})()"""


@pytest.mark.parametrize("mode", ["1v1", "2v2"])
@pytest.mark.parametrize("size", [(360, 640), (390, 844)], ids=lambda s: f"{s[0]}x{s[1]}")
def test_sul_telefono_le_frasi_sopra_le_tue_carte(browser, server, mode, size):
    # P101: l'elenco aperto copre solo la zona delle tue carte, sotto la tua riga
    _open(browser, server, mode, size)
    browser.click("[data-phrases-button]")
    box = browser.js(MENU_PARTS)
    menu, mine = box["menu"], box["mine"]
    assert abs(menu["t"] - box["me"]["b"]) <= 8 and abs(menu["b"] - mine["b"]) <= 1, box
    assert menu["l"] >= 0 and menu["r"] <= box["w"] and box["scroll"] <= box["h"]
    assert box["scrolls"] == "auto"
    assert not _overlap(menu, box["button"]) and not _overlap(menu, box["me"])
    for part in ("trick", "deck", "fan", "top", "left", "right"):
        if box[part]:
            assert not _overlap(menu, box[part]), part


def test_sul_tablet_elenco_delle_frasi_verso_l_alto(browser, server):
    # Sul tablet (da 640 px) l'elenco si apre ancora sopra la tua riga, senza coprire la mano
    _open(browser, server, "1v1", (768, 1024))
    browser.click("[data-phrases-button]")
    box = browser.js(MENU_PARTS)
    assert box["menu"]["b"] <= box["button"]["t"]
    assert abs(box["menu"]["r"] - box["me"]["r"]) <= 1
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


@pytest.mark.parametrize("size", [(1024, 768), (1280, 720), (1440, 900), (1920, 1080)], ids=lambda s: f"{s[0]}x{s[1]}")
def test_da_computer_mazzo_del_1v1_sotto_frasi(browser, server, size):
    # P100: il centro del mazzo sulla verticale della pillola "Frasi"; la presa al centro
    _open(browser, server, "1v1", size)
    box = _boxes(browser)
    deck, button = box["deck"], box["button"]
    assert abs((deck["l"] + deck["r"]) / 2 - (button["l"] + button["r"]) / 2) <= 6
    trick = box["trick"]
    assert abs((trick["l"] + trick["r"]) / 2 - box["w"] / 2) <= 2
    badge = _badge(browser)
    for name, part in (("presa", trick), ("ventaglio", badge["fan"]), ("avversario", badge["seat"]),
                       ("tabellone", badge["scoreboard"]), ("briscola", badge)):
        assert not _overlap(deck, part), name
    assert box["scrollH"] <= box["h"] and box["scrollW"] <= box["w"]


LAUNCH = """(() => {
  const r = (e) => { const b = e.getBoundingClientRect(); return { l: b.left, t: b.top, r: b.right, b: b.bottom }; };
  const q = (s) => { const e = document.querySelector(s); return e ? r(e) : null; };
  return { fan: q('[data-edge-hand="top"]'), hand: q('.table__mine .hand'), deck: q('.deck .card'),
           top: q('.trick__card--top .card'), bottom: q('.trick__card--bottom .card'),
           sing: q('.table__mine .sing-buttons:not(:empty)'), button: q('[data-phrases-button]') };
})()"""


@pytest.mark.parametrize("size", [(1024, 768), (1280, 720), (1366, 657), (1440, 900), (1920, 1080)],
                         ids=lambda s: f"{s[0]}x{s[1]}")
def test_da_computer_lancio_lungo_uguale(browser, server, size):
    # P117: nel 1v1 da computer tra il ventaglio dell'avversario e la sua carta c'è lo stesso
    # spazio che tra la tua carta e la tua mano; con o senza "Canta" presa e mazzo stanno fermi
    base = _view("1v1")
    _open(browser, server, "1v1", size)
    trick = {"leader_seat": 1, "cards": [{"seat": 1, "card": {"suit": "coppe", "rank": 3}},
                                         {"seat": 0, "card": {"suit": "coppe", "rank": 1}}], "winning_seat": None}
    seen = []
    for sing in (base["legal"]["sing"], []):
        _dispatch(browser, "demo:state", _state(base, version=base["version"] + 1 + len(seen), trick=trick,
                                                 legal={**base["legal"], "sing": sing}))
        box = browser.js(LAUNCH)
        above, below = box["top"]["t"] - box["fan"]["b"], box["hand"]["t"] - box["bottom"]["b"]
        assert abs(above - below) <= 2, (size, bool(sing), above, below)
        assert above >= 20, (size, above)
        if box["sing"]:
            assert box["bottom"]["b"] <= box["sing"]["t"] - 12, (size, "la presa tocca Canta")
        assert not _overlap(box["deck"], box["button"]), (size, "il mazzo tocca Frasi")
        seen.append((box["top"], box["bottom"], box["deck"], box["hand"]))
    assert seen[0] == seen[1], (size, "presa, mazzo o mano si spostano quando sparisce Canta")


@pytest.mark.parametrize("mode", ["1v1", "2v2"])
@pytest.mark.parametrize("size", [(1024, 768), (1280, 720), (1440, 900)], ids=lambda s: f"{s[0]}x{s[1]}")
def test_da_computer_briscola_a_sinistra_del_tabellone(browser, server, mode, size):
    # P102, P108: Cavallo e Re (56 px) a sinistra del tabellone, senza toccare niente
    base = _view(mode)
    _open(browser, server, mode, size)
    _dispatch(browser, "demo:state", _state(base, trump="denari", sings=[{"seat": 1, "suit": "denari", "points": 40}]))
    badge = _badge(browser)
    board = badge["scoreboard"]
    assert badge["b"] - badge["t"] == pytest.approx(56, abs=1)
    assert badge["cards"] == ["cavallo-denari.webp", "re-denari.webp"]
    assert badge["r"] <= board["l"] and board["l"] - badge["r"] <= 16
    assert abs((badge["t"] + badge["b"]) / 2 - (board["t"] + board["b"]) / 2) <= 1
    for part in ("leave", "fan", "seat", "scoreboard"):
        assert not _overlap(badge, badge[part]), part
    # Il tabellone resta nell'angolo in alto a destra (P74)
    assert board["r"] == pytest.approx(size[0] - 24, abs=1) and board["t"] == pytest.approx(14, abs=1)


def test_nel_2v2_il_mazzo_non_cambia(browser, server):
    # P100: solo il 1v1; nel 2v2 sul telefono il mazzo resta da 56 px
    _open(browser, server, "2v2")
    assert abs(_boxes(browser)["deck"]["w"] - 56) <= 1


HAND_PARTS = """(() => {
  const r = (s) => { const e = document.querySelector(s); if (!e) return null; const b = e.getBoundingClientRect();
    return { l: Math.round(b.left), t: Math.round(b.top), w: Math.round(b.width), h: Math.round(b.height) }; };
  return { card: r('.table__mine .hand > .card'), hand: r('.table__mine .hand'), trick: r('[data-trick]'),
           deck: r('.deck'), me: r('.table__mine [data-position="bottom"]'), top: r('.table__board [data-position="top"]') };
})()"""


@pytest.mark.parametrize("mode", ["1v1", "2v2"])
@pytest.mark.parametrize("size", [(360, 640), (390, 844), (768, 1024), (1280, 720)], ids=lambda s: f"{s[0]}x{s[1]}")
def test_meno_carte_in_mano_niente_si_sposta(browser, server, mode, size):
    # P106: con meno carte in mano le carte non si ingrandiscono e il tavolo non si muove
    base = _view(mode)
    _open(browser, server, mode, size)
    full = None
    for count in (5, 4, 3, 1):
        view = _state(base, hand=base["hand"][:count])
        view["version"] = base["version"] + 10 - count  # versioni che salgono
        _dispatch(browser, "demo:state", view)
        parts = browser.js(HAND_PARTS)
        if full is None:
            full = parts
            continue
        assert parts["card"]["w"] == full["card"]["w"] and parts["card"]["h"] == full["card"]["h"], (count, parts)
        for name in ("hand", "trick", "deck", "me", "top"):
            assert parts[name] == full[name], (count, name, parts[name], full[name])

