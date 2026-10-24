"""P22: home (carte-pulsante, carta-modal, online, sfondo): i controlli rimasti qui.

Quasi tutti i controlli della home li fanno, sulla home React (/), i file
tests/frontend2/test_spa_home.py (pagina, ?demo=, senza e con il login, rientro),
tests/frontend/test_spa_home_misure.py (la home non scorre, sfondo, carta-modal che
contiene tutto) e tests/frontend/test_spa_home_coda.py (coda, CPU, connessione persa).
Qui restano, sulla home React:
- i CSS della home caricati dalla SPA, che esistono, e le immagini che usano;
- "Lo sapevi?" con i termini del regolamento (cantare 40 / 20, mai "matrimonio");
- la scelta dell'avversario solo nella Partita Veloce, con le parole del 1v1 e del 2v2
  (P73, P123) e i testi della carta-modal contro la CPU nel 2v2;
- "1 giocatore online" al singolare e "2 giocatori online" senza login (P120).
Nel browser (Chrome o Edge senza finestra) su un server di prova alla porta 5099; se
mancano, o manca il build della SPA, quei controlli si saltano.
Non serve MySQL: l'utente con il login è finto (un cookie dei soli test).
"""

import json
import re
import time
from pathlib import Path

import pytest

from app import create_app
from app.realtime.presence import presence
from tests.browser import TEST_COOKIE, Browser, FakeUser, find_browser, running_server
from tests.spa import needs_spa

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "app" / "static"
TILES = [("veloce", "1v1"), ("veloce", "2v2"), ("amico", "1v1"), ("amico", "2v2")]
# PAGE_CSS: i CSS della home (prima in main/index.html); la SPA li carica in frontend/index.html
PAGE_CSS = ("pages/home", "components/card-background", "components/mode-modal", "components/queue-overlay")


# --- File ----------------------------------------------------------------------


def test_la_spa_carica_i_css_della_home():
    spa = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    client = create_app("testing").test_client()
    for name in PAGE_CSS:
        path = f"/static/css/{name}.css"
        assert f'href="{path}"' in spa, name
        response = client.get(path)
        assert response.status_code == 200, name
        response.close()


def test_immagini_usate_dai_css_esistono():
    for name in PAGE_CSS:
        css_path = STATIC / "css" / f"{name}.css"
        for url in re.findall(r'url\("(\.\./[^"]+)"\)', css_path.read_text(encoding="utf-8")):
            assert (css_path.parent / url).resolve().is_file(), f"{name}.css: {url}"


def test_consigli_del_modal_dal_regolamento():
    # "Lo sapevi?" usa i termini del regolamento: cantare 40 / 20, mai "matrimonio"
    # (dal lotto 9b-1 nella carta-modal React)
    code = (ROOT / "frontend" / "src" / "components" / "ModeModal.tsx").read_text(encoding="utf-8")
    assert "matrimonio" not in code.lower()
    rules = (ROOT / "docs" / "REGOLE-GIOCO.md").read_text(encoding="utf-8")
    assert "Ogni mano vale 120 punti di carte, più i canti." in rules
    assert "Non c'è obbligo di rispondere al seme" in rules
    assert "almeno 3 carte in mano" in rules


# --- Nel browser ---------------------------------------------------------------


# La home è pronta quando c'è la cascata e "giocatori online" (il numero vero: con il login
# da home:status, senza da GET /api/online)
HOME_READY = ("document.querySelector('[data-bg-cards]')?.children.length > 0"
              " && document.querySelector('[data-online]:not([hidden])') !== null")


@pytest.fixture(scope="module")
def server():
    needs_spa()
    with running_server(create_app("testing"), FakeUser("Mario")) as url:
        yield url


@pytest.fixture(scope="module")
def browser(server, tmp_path_factory):
    b = Browser(find_browser(), tmp_path_factory.mktemp("chrome"))
    # Prima apertura: la prima volta si scaricano font e icone (poi restano in FONT_CACHE)
    b.open(f"{server}/", 390, 844, HOME_READY, timeout=100)
    yield b
    b.close()


@pytest.fixture
def logged_in(browser, server):
    browser.send("Network.setCookie", name=TEST_COOKIE[0], value=TEST_COOKIE[1], url=server)
    yield browser
    browser.send("Network.deleteCookies", name=TEST_COOKIE[0], url=server)


def _click(browser, selector):
    browser.js(f"document.querySelector({json.dumps(selector)}).click()")


def _open_modal(browser, kind, mode):
    _click(browser, f'[data-tile][data-kind="{kind}"][data-mode="{mode}"]')
    browser.wait_js("document.querySelector('[data-mode-modal]')?.open", f"apertura del modal {kind} {mode}")


def _close_modal(browser):
    # Nella home React la carta-modal chiusa non c'è nella pagina (CLAUDE.md, Home P22): si
    # aspetta che sparisca, cioè che finisca l'animazione di chiusura, prima di aprirne un'altra
    _click(browser, ".mode-modal__close")
    browser.wait_js("document.querySelector('[data-mode-modal]') === null", "chiusura del modal")


OPPONENT = """(() => { const d = document.querySelector('[data-mode-modal]');
  const f = d.querySelector('[data-opponent]');
  return {hidden: f.hidden, checked: f.querySelector('input:checked')?.value ?? null,
          desc: d.querySelector('[data-modal-desc]').textContent,
          facts: d.querySelector('.facts').textContent,
          note: d.querySelector('.target__note').getClientRects().length > 0}; })()"""
CHOICES = "[...document.querySelectorAll('fieldset[data-opponent] .opponent__choice')].map((s) => s.textContent)"
LEGEND = "document.querySelector('fieldset[data-opponent] legend').textContent"   # la finestra ha anche data-opponent


def test_scelta_dell_avversario_solo_nella_partita_veloce(logged_in, server):
    # P73 (D43): "Avversario: Giocatore · CPU" nella Partita Veloce 1v1; P123: "Gioca con:
    # Giocatori · CPU" nella Partita Veloce 2v2; con un amico niente; parte sempre da Giocatore
    logged_in.open(f"{server}/", 1440, 900, HOME_READY)
    for kind, mode in TILES:
        _open_modal(logged_in, kind, mode)
        state = logged_in.js(OPPONENT)
        assert state["hidden"] is (kind != "veloce"), (kind, mode)
        assert state["checked"] == "player", (kind, mode)
        _close_modal(logged_in)
    _open_modal(logged_in, "veloce", "1v1")
    assert "15 secondi per ogni turno" in logged_in.js(OPPONENT)["facts"]   # P94: non più 30
    assert logged_in.js(LEGEND) == "Avversario"
    assert logged_in.js(CHOICES) == ["personGiocatore", "smart_toyCPU"]   # icona (nome nel font) e parola
    _close_modal(logged_in)
    _open_modal(logged_in, "veloce", "2v2")
    assert logged_in.js(LEGEND) == "Gioca con"
    assert logged_in.js(CHOICES) == ["personGiocatori", "smart_toyCPU"]
    _close_modal(logged_in)
    _open_modal(logged_in, "veloce", "1v1")   # e tornando al 1v1 le parole tornano quelle del 1v1
    assert logged_in.js(LEGEND) == "Avversario" and logged_in.js(CHOICES)[0] == "personGiocatore"
    _close_modal(logged_in)


def test_contro_la_cpu_nel_2v2_i_testi(logged_in, server):
    # P123 (D49): con "Gioca con: CPU" cambiano descrizione e "In breve" e sparisce la frase
    # dei punti; tornando a "Giocatori" torna tutto. Che "Gioca" porti al tavolo 2v2 con le
    # tre CPU lo controlla test_spa_home_coda.py (test_contro_la_cpu_si_va_subito_al_tavolo)
    logged_in.open(f"{server}/", 1440, 900, HOME_READY)
    _open_modal(logged_in, "veloce", "2v2")
    _click(logged_in, 'input[name="opponent"][value="cpu"]')
    logged_in.wait_js("document.querySelector('[data-mode-modal]').dataset.opponent === 'cpu'", "scelta della CPU")
    state = logged_in.js(OPPONENT)
    assert "in coppia con il computer" in state["desc"] and state["note"] is False
    assert "Parte subito, senza coda" in state["facts"] and "Non conta per il rating" in state["facts"]
    assert "CPU 1, la tua compagna, siede di fronte a te" in state["facts"]
    _click(logged_in, 'input[name="opponent"][value="player"]')
    logged_in.wait_js("document.querySelector('[data-mode-modal]').dataset.opponent === 'player'", "scelta dei giocatori")
    state = logged_in.js(OPPONENT)
    assert "Entri in coda da solo" in state["desc"] and state["note"] is True and "Conta per il tuo rating 2v2" in state["facts"]
    _close_modal(logged_in)


ONLINE_TEXT = r"document.querySelector('[data-online]').textContent.replace(/\s+/g, ' ').trim()"


def test_un_giocatore_online_al_singolare(browser, server):
    # P120: "1 giocatore online", "2 giocatori online" (senza login, il numero di GET /api/online, P82);
    # schede finte di utenti che non esistono (come test_online_senza_login.py).
    # La pagina del test prima (con il login di Mario, utente 7) è ancora aperta e collegata:
    # si apre la home senza login e si aspetta che la sua scheda esca, altrimenti il conto
    # di partenza sarebbe sbagliato
    browser.open(f"{server}/", 390, 844, HOME_READY)
    deadline = time.monotonic() + 10
    while presence.tabs_of(7) and time.monotonic() < deadline:
        time.sleep(0.1)
    before = presence.count()
    if before > 1:
        pytest.skip(f"già {before} utenti collegati")
    tabs = [(9101, "p120-a"), (9102, "p120-b")][before:]
    try:
        for count, (user_id, sid) in enumerate(tabs, start=before + 1):
            presence.add(user_id, sid)
            browser.open(f"{server}/", 390, 844, HOME_READY)
            browser.wait_js(f"{ONLINE_TEXT}.startsWith('{count} ')", f"{count} online")
            expected = "1 giocatore online" if count == 1 else f"{count} giocatori online"
            assert browser.js(ONLINE_TEXT) == expected
    finally:
        for user_id, sid in tabs:
            presence.remove(user_id, sid)
