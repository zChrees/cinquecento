"""P22: home con dati finti (carte-pulsante, carta-modal, coda, rientro, online, sfondo).

Controlla il "Fatto quando" di SCALETTA.md (P22):
- risposte del server: la pagina ha le quattro carte-pulsante e i marcatori data-*;
  i dati finti ci sono solo in sviluppo e nei test (?demo=rientro per l'avviso di
  rientro); index.html ha solo markup, senza <style> né script scritti dentro;
- nel browser (Chrome o Edge senza finestra, pilotato con il protocollo DevTools
  su un server di prova alla porta 5099): la pagina non scorre alle misure di
  docs/prototipo/LEGGIMI.md; nelle quattro modalità ogni parte della carta-modal,
  "Gioca" compreso, sta dentro la cornice senza sovrapporsi alle altre; "Gioca"
  con un amico resta disattivato finché l'invito finto non è accettato; senza
  login il tocco apre la finestra di accesso; la schermata di coda si apre e si
  annulla; l'avviso di rientro compare solo con i dati che lo prevedono; le carte
  dello sfondo passano dietro a titoli e carte-pulsante.
Se né Chrome né Edge sono installati i controlli nel browser si saltano.
Non serve MySQL: l'utente con il login è finto (un cookie dei soli test).
"""

import json
import re
from pathlib import Path

import pytest

from app import create_app
from tests.browser import TEST_COOKIE, Browser, FakeUser, find_browser, running_server

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "app" / "static"
DEV = STATIC / "dev"
INDEX = ROOT / "app" / "templates" / "main" / "index.html"
TILES = [("veloce", "1v1"), ("veloce", "2v2"), ("amico", "1v1"), ("amico", "2v2")]
PAGE_CSS = ("pages/home", "components/card-background", "components/mode-modal", "components/queue-overlay")
COMPONENTS = ("ModeModal", "CardBackground", "QueueOverlay", "ResumeBanner")

# Misure controllate nel prototipo (docs/prototipo/LEGGIMI.md)
NO_SCROLL_SIZES = [(360, 640), (375, 667), (390, 844), (412, 915), (768, 1024), (844, 390),
                   (1280, 720), (1440, 900), (1920, 1080)]
MODAL_SIZES = [(1920, 1080), (1440, 900), (1366, 657), (1536, 730), (360, 560), (360, 640),
               (390, 844), (412, 915), (844, 390), (667, 375)]


@pytest.fixture
def app():
    return create_app("testing")


@pytest.fixture
def client(app):
    return app.test_client()


def _text(response):
    text = response.get_data(as_text=True)
    response.close()
    return text


# --- Risposte del server -----------------------------------------------------


def test_home_con_le_quattro_carte_pulsante(client):
    html = _text(client.get("/"))
    assert 'data-page="home"' in html and 'class="page home"' in html
    for kind, mode in TILES:
        assert re.search(rf'<button class="mode-tile [^"]+" type="button" data-tile data-kind="{kind}" data-mode="{mode}"', html), (kind, mode)
    assert "Partita Veloce" in html and "Gioca con un amico" in html
    for marker in ("data-home", "data-status-slot", "data-online", "data-online-count", "data-resume-slot"):
        assert marker in html, marker
    assert 'data-bg-cards data-img-base="/static/img/cards-bg/"' in html
    assert '<script type="module" src="/static/js/pages/home.js"></script>' in html


def test_dati_finti_in_sviluppo_e_nei_test(client):
    html = _text(client.get("/"))
    urls = dict(re.findall(r'data-demo-(home|friends|stats)-url="([^"]+)"', html))
    assert urls == {
        "home": "/static/dev/home_esempio.json",
        "friends": "/static/dev/amici_esempio.json",
        "stats": "/static/dev/statistiche_esempio.json",
    }
    for url in urls.values():
        response = client.get(url)
        assert response.status_code == 200, url
        response.close()
    assert "data-demo-state" not in html


def test_forma_dei_dati_finti_usati_dalla_home():
    home = json.loads((DEV / "home_esempio.json").read_text(encoding="utf-8"))
    assert set(home["home:status"]) == {"online_count", "resume"} and home["home:status"]["resume"] is None
    resume = home["home:status con partita in corso"]["resume"]
    assert re.fullmatch(r"/game/[A-Za-z0-9_-]+", resume["url"])
    for key in ("queue:status", "queue:status 2v2 con un amico"):
        assert set(home[key]) == {"mode", "target_score", "seconds_waiting", "rating_range", "partner"}, key
    friends = json.loads((DEV / "amici_esempio.json").read_text(encoding="utf-8"))["GET /friends/"]["friends"]
    assert [f for f in friends if f["presence"] == "online"], "serve almeno un amico online da invitare"
    stats = json.loads((DEV / "statistiche_esempio.json").read_text(encoding="utf-8"))
    assert {"value", "provisional"} <= set(stats["ratings"]["1v1"])


def test_avviso_di_rientro_con_demo_rientro(client):
    html = _text(client.get("/?demo=rientro"))
    assert 'data-demo-state="rientro"' in html


@pytest.mark.parametrize("path", ["/?demo=coda", "/?demo=", "/?demo=RIENTRO"])
def test_stati_finti_non_validi(client, path):
    assert client.get(path).status_code == 404


def test_niente_dati_finti_nella_demo_vera(app):
    app.config["ENV_NAME"] = "demo"
    client = app.test_client()
    html = _text(client.get("/"))
    assert "data-demo-" not in html
    assert "data-tile" in html
    assert client.get("/?demo=rientro").status_code == 404


def test_index_solo_markup():
    text = re.sub(r"\{#.*?#\}", "", INDEX.read_text(encoding="utf-8"), flags=re.DOTALL)
    assert "<style" not in text
    assert not re.search(r"<script\b(?![^>]*\bsrc=)", text), "script scritto nella pagina"
    assert not re.search(r"\sstyle=", text)
    assert '{% extends "base.html" %}' in text


def test_css_e_js_della_home_esistono(client):
    html = _text(client.get("/"))
    for name in PAGE_CSS:
        path = f"/static/css/{name}.css"
        assert f'href="{path}"' in html, name
        response = client.get(path)
        assert response.status_code == 200, name
        response.close()
    for name in COMPONENTS:
        response = client.get(f"/static/js/components/{name}.js")
        assert response.status_code == 200, name
        response.close()


def test_immagini_usate_dai_css_esistono():
    for name in PAGE_CSS:
        css_path = STATIC / "css" / f"{name}.css"
        for url in re.findall(r'url\("(\.\./[^"]+)"\)', css_path.read_text(encoding="utf-8")):
            assert (css_path.parent / url).resolve().is_file(), f"{name}.css: {url}"


def test_una_sola_funzione_render():
    code = (STATIC / "js" / "pages" / "home.js").read_text(encoding="utf-8")
    assert code.count("function render(") == 1
    assert "initLayout()" in code


def test_consigli_del_modal_dal_regolamento():
    # "Lo sapevi?" usa i termini del regolamento: cantare 40 / 20, mai "matrimonio"
    code = (STATIC / "js" / "components" / "ModeModal.js").read_text(encoding="utf-8")
    assert "matrimonio" not in code.lower()
    rules = (ROOT / "docs" / "REGOLE-GIOCO.md").read_text(encoding="utf-8")
    assert "Ogni mano vale 120 punti di carte, più i canti." in rules
    assert "Non c'è obbligo di rispondere al seme" in rules
    assert "almeno 3 carte in mano" in rules


# --- Nel browser ---------------------------------------------------------------


# La home è pronta quando c'è la cascata e, con i dati finti, "giocatori online" o l'avviso di rientro
HOME_READY = ("document.querySelector('[data-bg-cards]')?.children.length > 0"
              " && (!document.querySelector('[data-demo-home-url]')"
              "     || !document.querySelector('[data-online]').hidden"
              "     || !document.querySelector('[data-resume-slot]').hidden)")


class HomeBrowser(Browser):
    def open(self, url, width, height, timeout=15):
        super().open(url, width, height, HOME_READY, timeout)


@pytest.fixture(scope="module")
def server():
    with running_server(create_app("testing"), FakeUser("Mario")) as url:
        yield url


@pytest.fixture(scope="module")
def browser(server, tmp_path_factory):
    b = HomeBrowser(find_browser(), tmp_path_factory.mktemp("chrome"))
    # Prima apertura: la prima volta si scaricano font e icone (poi restano in FONT_CACHE)
    b.open(f"{server}/", 390, 844, timeout=100)
    yield b
    b.close()


@pytest.fixture
def logged_in(browser, server):
    browser.send("Network.setCookie", name=TEST_COOKIE[0], value=TEST_COOKIE[1], url=server)
    yield browser
    browser.send("Network.deleteCookies", name=TEST_COOKIE[0], url=server)


# Misure della home: rettangoli di navbar, spazio di stato, titoli e carte-pulsante
MEASURE_HOME = """(() => {
  const box = (e) => { const r = e.getBoundingClientRect(); return {top: r.top, bottom: r.bottom, left: r.left, right: r.right}; };
  const visible = (e) => e.getClientRects().length > 0;
  const main = document.querySelector('main');
  const status = [...document.querySelectorAll('[data-status-slot] > *')].filter(visible);
  return {
    vw: innerWidth, vh: innerHeight,
    scrollW: document.documentElement.scrollWidth, scrollH: document.documentElement.scrollHeight,
    mainScroll: main.scrollHeight, mainClient: main.clientHeight,
    navbar: box(document.querySelector('[data-part="navbar"]')),
    status: status.map(box),
    titles: [...document.querySelectorAll('.mode-section__title')].map(box),
    tiles: [...document.querySelectorAll('[data-tile]')].map(box),
  };
})()"""

# Misure della carta-modal: faccia, parti visibili del corpo nell'ordine, X e titolo
MEASURE_MODAL = """(() => {
  const box = (e) => { const r = e.getBoundingClientRect(); return {top: r.top, bottom: r.bottom, left: r.left, right: r.right}; };
  const dialog = document.querySelector('[data-mode-modal]');
  const parts = [...dialog.querySelector('.mode-modal__body').children].filter((e) => e.getClientRects().length > 0);
  return {
    vw: innerWidth, vh: innerHeight,
    face: box(dialog.querySelector('.mode-modal__face')),
    parts: parts.map((e) => ({name: e.className || e.tagName, ...box(e)})),
    close: box(dialog.querySelector('.mode-modal__close')),
    title: box(dialog.querySelector('.mode-modal__title')),
    play: box(dialog.querySelector('[data-play]')),
    faceScroll: dialog.querySelector('.mode-modal__face').scrollHeight,
    faceClient: dialog.querySelector('.mode-modal__face').clientHeight,
  };
})()"""

FRAME = 14   # cornice doppia della faccia: 10 px dal bordo più 4 px di spessore
EPS = 0.5


def _overlap(a, b):
    return a["left"] < b["right"] - EPS and b["left"] < a["right"] - EPS \
        and a["top"] < b["bottom"] - EPS and b["top"] < a["bottom"] - EPS


def _click(browser, selector):
    browser.js(f"document.querySelector({json.dumps(selector)}).click()")


def _open_modal(browser, kind, mode):
    _click(browser, f'[data-tile][data-kind="{kind}"][data-mode="{mode}"]')
    browser.wait_js("document.querySelector('[data-mode-modal]')?.open", f"apertura del modal {kind} {mode}")


def _close_modal(browser):
    _click(browser, ".mode-modal__close")
    browser.wait_js("!document.querySelector('[data-mode-modal]').open", "chiusura del modal")


@pytest.mark.parametrize("size", NO_SCROLL_SIZES, ids=lambda s: f"{s[0]}x{s[1]}")
def test_la_home_non_scorre(logged_in, server, size):
    width, height = size
    logged_in.open(f"{server}/", width, height)
    m = logged_in.js(MEASURE_HOME)
    assert m["scrollW"] <= m["vw"] and m["scrollH"] <= m["vh"], m
    assert m["mainScroll"] <= m["mainClient"] + 1, "il contenuto della home esce dalla pagina"
    assert len(m["tiles"]) == 4 and len(m["status"]) == 1
    for tile in m["tiles"]:
        assert tile["top"] >= m["navbar"]["bottom"] - EPS, tile
        assert tile["bottom"] <= m["vh"] + EPS and tile["left"] >= -EPS and tile["right"] <= m["vw"] + EPS, tile
    for block in m["titles"] + m["status"]:
        assert block["top"] >= m["navbar"]["bottom"] - EPS and block["bottom"] <= m["vh"] + EPS, block
        for tile in m["tiles"]:
            assert not _overlap(block, tile), (block, tile)


def test_sfondo_dietro_a_titoli_e_carte(logged_in, server):
    logged_in.open(f"{server}/", 1440, 900)
    result = logged_in.js("""(() => {
      const deco = document.querySelector('[data-bg-cards]');
      const hit = (e) => { const r = e.getBoundingClientRect();
        return document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2); };
      return {
        cards: deco.children.length,
        zIndex: getComputedStyle(deco).zIndex,
        tiles: [...document.querySelectorAll('[data-tile]')].every((t) => t.contains(hit(t))),
        titles: [...document.querySelectorAll('.mode-section__title')].every((t) => t.contains(hit(t))),
      };
    })()""")
    assert result["cards"] >= 8 and result["zIndex"] == "-1"
    assert result["tiles"] and result["titles"], result


@pytest.mark.parametrize("size", MODAL_SIZES, ids=lambda s: f"{s[0]}x{s[1]}")
def test_la_carta_modal_contiene_tutto(logged_in, server, size):
    width, height = size
    logged_in.open(f"{server}/", width, height)
    for kind, mode in TILES:
        _open_modal(logged_in, kind, mode)
        m = logged_in.js(MEASURE_MODAL)
        where = f"{kind} {mode} a {width}x{height}"
        face = m["face"]
        assert face["top"] >= -EPS and face["bottom"] <= m["vh"] + EPS, where
        assert face["left"] >= -EPS and face["right"] <= m["vw"] + EPS, where
        assert m["faceScroll"] <= m["faceClient"], f"{where}: la faccia scorre"
        inner = {"top": face["top"] + FRAME, "bottom": face["bottom"] - FRAME,
                 "left": face["left"] + FRAME, "right": face["right"] - FRAME}
        names = [p["name"] for p in m["parts"]]
        assert "btn btn--primary btn--big" in names, f"{where}: manca Gioca"
        for part in m["parts"]:
            assert part["top"] >= inner["top"] - EPS and part["bottom"] <= inner["bottom"] + EPS, (where, part)
            assert part["left"] >= inner["left"] - EPS and part["right"] <= inner["right"] + EPS, (where, part)
        for before, after in zip(m["parts"], m["parts"][1:]):
            assert before["bottom"] <= after["top"] + EPS, (where, before["name"], after["name"])
        assert not _overlap(m["close"], m["title"]), f"{where}: la X copre il titolo"
        _close_modal(logged_in)


def test_invito_finto_poi_gioca_e_coda_con_il_compagno(logged_in, server):
    logged_in.open(f"{server}/", 390, 844)
    _open_modal(logged_in, "amico", "2v2")
    assert logged_in.js("document.querySelector('[data-play]').disabled") is True
    names = logged_in.js("[...document.querySelectorAll('.invite__name')].map((e) => e.textContent)")
    assert names == ["Giulia", "Salvo"]   # solo gli amici online di amici_esempio.json
    _click(logged_in, '[data-invite-user="44"]')
    assert logged_in.js("document.querySelector('[data-invite-user=\"44\"]').dataset.state") == "pending"
    # Un invito alla volta: gli altri "Invita" e i punti sono fermi
    assert logged_in.js("document.querySelector('[data-invite-user=\"45\"]').disabled") is True
    assert logged_in.js("[...document.querySelectorAll('input[name=target]')].every((i) => i.disabled)") is True
    assert logged_in.js("document.querySelector('[data-play]').disabled") is True
    logged_in.wait_js("document.querySelector('[data-invite-user=\"44\"]').dataset.state === 'accepted'",
                      "accettazione dell'invito finto", timeout=6)
    assert logged_in.js("document.querySelector('[data-play]').disabled") is False

    _click(logged_in, "[data-play]")
    logged_in.wait_js("document.querySelector('[data-queue-overlay]')?.open", "schermata di coda")
    text = logged_in.js("document.querySelector('[data-queue-overlay]').textContent")
    assert "In squadra con Giulia" in text and "Va bene qualunque avversario" in text
    assert "Cerco gli avversari" in text and "2v2 · 500 punti" in text
    # Mentre si è in coda le carte-pulsante non aprono il modal (la schermata copre la pagina)
    assert logged_in.js("document.querySelector('[data-mode-modal]').open") is False
    _click(logged_in, "[data-queue-cancel]")
    logged_in.wait_js("!document.querySelector('[data-queue-overlay]')", "chiusura della schermata di coda")


def test_partita_veloce_apre_e_annulla_la_coda(logged_in, server):
    logged_in.open(f"{server}/", 1440, 900)
    _open_modal(logged_in, "veloce", "1v1")
    facts = logged_in.js("document.querySelector('.facts').textContent")
    assert "Conta per il tuo rating 1v1 (1540)" in facts
    _click(logged_in, 'input[name="target"][value="150"]')
    _click(logged_in, "[data-play]")
    logged_in.wait_js("document.querySelector('[data-queue-overlay]')?.open", "schermata di coda")
    overlay = logged_in.js("""(() => { const o = document.querySelector('[data-queue-overlay]');
      return {mode: o.dataset.mode, target: o.dataset.targetScore, text: o.textContent,
              seconds: o.querySelector('[data-queue-seconds]').textContent}; })()""")
    assert overlay["mode"] == "1v1" and overlay["target"] == "150"
    assert "Cerco un avversario" in overlay["text"] and "tra 1340 e 1740" in overlay["text"]
    assert re.fullmatch(r"\d+:\d\d", overlay["seconds"])
    # Esc vale come "Annulla"
    logged_in.send("Input.dispatchKeyEvent", type="keyDown", key="Escape", code="Escape", windowsVirtualKeyCode=27)
    logged_in.send("Input.dispatchKeyEvent", type="keyUp", key="Escape", code="Escape", windowsVirtualKeyCode=27)
    logged_in.wait_js("!document.querySelector('[data-queue-overlay]')", "Esc sulla schermata di coda")


def test_con_un_amico_1v1_messaggio_di_prova(logged_in, server):
    logged_in.open(f"{server}/", 1440, 900)
    _open_modal(logged_in, "amico", "1v1")
    _click(logged_in, '[data-invite-user="45"]')
    logged_in.wait_js("!document.querySelector('[data-play]').disabled", "accettazione dell'invito finto", timeout=6)
    _click(logged_in, "[data-play]")
    logged_in.wait_js("document.querySelector('[data-flash]')?.textContent.includes('contro Salvo')",
                      "messaggio della partita di prova")
    assert logged_in.js("document.querySelector('[data-queue-overlay]')") is None


def test_senza_login_la_carta_apre_la_finestra_di_accesso(browser, server):
    browser.open(f"{server}/", 390, 844)
    assert browser.js("document.body.dataset.userId") == ""
    _click(browser, '[data-tile][data-kind="veloce"][data-mode="1v1"]')
    browser.wait_js("document.querySelector('dialog.dialog[open]') !== null", "finestra di accesso")
    assert "Accedi o registrati per giocare" in browser.js("document.querySelector('dialog.dialog[open]').textContent")
    assert browser.js("document.querySelector('[data-mode-modal]')") is None


def test_avviso_di_rientro_solo_se_previsto(logged_in, server):
    logged_in.open(f"{server}/", 1440, 900)
    assert logged_in.js("document.querySelector('[data-resume]')") is None
    assert logged_in.js("document.querySelector('[data-online-count]').textContent") == "24"

    for width, height in [(1440, 900), (360, 640), (844, 390)]:
        logged_in.open(f"{server}/?demo=rientro", width, height)
        banner = logged_in.js("""(() => { const b = document.querySelector('[data-resume]');
          return b && {text: b.textContent, href: b.querySelector('[data-resume-link]').getAttribute('href'),
                       online: document.querySelector('[data-online]').hidden}; })()""")
        assert banner and "Hai una partita in corso" in banner["text"] and "1v1 a 500 punti" in banner["text"]
        assert banner["href"] == "/game/a1b2c3d4" and banner["online"] is True
        m = logged_in.js(MEASURE_HOME)
        assert m["scrollH"] <= m["vh"] and m["mainScroll"] <= m["mainClient"] + 1, (width, height)
        for tile in m["tiles"]:
            assert not _overlap(m["status"][0], tile), (width, height)
            assert tile["bottom"] <= m["vh"] + EPS, (width, height)
