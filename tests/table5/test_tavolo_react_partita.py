"""P24, P25: il tavolo (frontend/src/game/tableStore.ts) gioca una partita vera.

Una partita vera contro la CPU (P68, non si salva), aperta sul tavolo
(/game/<codice>) in Chrome o Edge senza finestra
(tests/browser.py). Controlla:
- la pagina si collega, manda game:join e disegna la vista del server, con le
  immagini delle carte pronte (data-cards-ready, P79) e senza avviso di connessione;
- toccando una carta giocabile la mossa arriva al server (con la version della vista)
  e la carta lascia la mano;
- "Esci" apre la finestra "Vuoi uscire dalla partita?": "Annulla" resta al tavolo e
  la partita continua; "Esci" la chiude per abbandono e torna alla home (P25);
- aprendo la stessa partita in un altro browser, questo si ferma con "Questa partita è
  aperta in un'altra scheda o su un altro dispositivo." (game:replaced, D14);
- l'elenco delle frasi arriva dal server (game:phrases); una frase scelta va
  al server (game:send_phrase), il fumetto torna con game:phrase e il pulsante resta
  spento per la pausa (P56);
- dalla home al tavolo (game:start) e ritorno ("Esci") senza ricaricare la
  pagina, e tornati alla home il numero degli online c'è (home:refresh: il
  collegamento è rimasto aperto, quindi home:status non arriva di nuovo).
La partita interrotta (P95) la prova table6/test_partita_interrotta.py. Rating e avvisi agli amici non leggono il database (non serve MySQL).
Senza browser, o senza il build della SPA, i test si saltano.
"""

import json

import pytest

from app import create_app
from app.realtime import room_manager, table_phrases
from app.realtime.room import CPU_PLAYER, Player
from app.realtime.room_manager import create_room, rooms
from app.sockets import friends_events
from tests.browser import TEST_COOKIE, Browser, FakeUser, find_browser, running_server
from tests.spa import needs_spa

USER_ID = 12
READY = "document.querySelector('[data-mode]') !== null"
# PLAYABLE: la prima carta della tua mano che si può giocare adesso, oppure null
PLAYABLE = "document.querySelector('[data-hand] button.card:not(:disabled)')"
DIALOG = "document.querySelector('dialog.dialog[open]')"
# ONLINE: il numero degli online della home ('' finché non arriva lo stato)
ONLINE = "(document.querySelector('[data-online-count]')?.textContent ?? '')"


@pytest.fixture(scope="module")
def app():
    needs_spa()
    return create_app("testing")


@pytest.fixture(scope="module")
def server(app):
    with running_server(app, FakeUser("Mario", USER_ID)) as url:
        yield url


def _browser(server, tmp_path, name):
    # La home vera si collegherebbe al tempo reale e userebbe il database: qui basta
    # sapere che la pagina ci va, quindi il browser risponde da sé (come test_partita_interrotta.py)
    b = Browser(find_browser(), tmp_path / name, routes={f"{server}/": lambda _request: (200, {"home": True})})
    b.send("Network.setCookie", name=TEST_COOKIE[0], value=TEST_COOKIE[1], url=server)
    return b


@pytest.fixture
def browser(server, tmp_path):
    b = _browser(server, tmp_path, "chrome")
    yield b
    b.close()


@pytest.fixture
def room(app, monkeypatch):
    # Niente database: né rating né avvisi agli amici
    monkeypatch.setattr(room_manager, "_ratings_of", lambda players, mode, cpu_seats: None)
    monkeypatch.setattr(friends_events, "notify_presence", lambda *args, **kwargs: None)
    with app.app_context():
        created = room_manager.create_room([Player(user_id=USER_ID, username="Mario"), CPU_PLAYER], "1v1", 150,
                                           rated=False, cpu_seats=(1,))
    yield created
    created._stop_timers()
    room_manager.rooms.remove(created.id)


def _open(browser, server, room):
    browser.open(f"{server}/game/{room.id}", 390, 844, READY, timeout=30)


def test_si_collega_e_gioca_una_carta(browser, server, room):
    _open(browser, server, room)
    table = browser.js("""(() => { const t = document.querySelector('[data-table]');
      return { id: t.dataset.gameId, root: document.getElementById('root') !== null,
               seats: document.querySelectorAll('.seat').length, cpu: document.querySelector('[data-cpu]') !== null }; })()""")
    assert table == {"id": room.id, "root": True, "seats": 2, "cpu": True}
    browser.wait_js("document.querySelector('[data-table]').dataset.cardsReady === '1'", "immagini pronte", 30)
    assert browser.js("document.querySelector('[data-banner]')") is None

    # Quando tocca a te (dopo la distribuzione e, se apre la CPU, dopo la sua carta)
    browser.wait_js(f"{PLAYABLE} !== null", "una carta giocabile", 30)
    card = browser.js(f"(() => {{ const c = {PLAYABLE}; return {{ suit: c.dataset.suit, rank: c.dataset.rank }}; }})()")
    before = int(browser.js("document.querySelector('[data-version]').dataset.version"))
    browser.click("[data-hand] button.card:not(:disabled)")
    in_hand = f"document.querySelector('[data-hand] [data-suit=\"{card['suit']}\"][data-rank=\"{card['rank']}\"]')"
    browser.wait_js(f"{in_hand} === null", "carta uscita dalla mano", 15)
    assert int(browser.js("document.querySelector('[data-version]').dataset.version")) > before
    # Il server l'ha davvero giocata: non è più nella tua mano nemmeno per lui
    hand = room.view_for(0)["hand"]
    assert {"suit": card["suit"], "rank": int(card["rank"])} not in hand
    assert browser.js("document.querySelector('[data-table-status]').textContent") == ""


def test_esci_annulla_e_conferma(browser, server, room):
    _open(browser, server, room)
    # Annulla: si resta al tavolo e la partita continua
    browser.click("[data-leave]")
    browser.wait_js(f"{DIALOG} !== null", "finestra di Esci")
    texts = browser.js(f"""(() => {{ const d = {DIALOG};
      return {{ title: d.querySelector('h2').textContent, body: d.querySelector('.dialog__body').textContent,
                buttons: [...d.querySelectorAll('.dialog__actions button')].map((b) => b.textContent) }}; }})()""")
    assert texts == {"title": "Vuoi uscire dalla partita?", "body": "La partita sarà persa per abbandono.",
                     "buttons": ["Annulla", "Esci"]}
    browser.js(f"[...{DIALOG}.querySelectorAll('button')].find((b) => b.textContent === 'Annulla').click()")
    browser.wait_js(f"{DIALOG} === null", "finestra chiusa")
    assert browser.js("location.pathname") == f"/game/{room.id}"
    assert room.finished is False

    # Esci: game:leave, partita persa per abbandono, ritorno alla home
    browser.click("[data-leave]")
    browser.wait_js(f"{DIALOG} !== null", "finestra di Esci")
    browser.js(f"[...{DIALOG}.querySelectorAll('button')].find((b) => b.textContent === 'Esci').click()")
    browser.wait_js("location.pathname === '/'", "ritorno alla home", 15)
    assert room.finished is True
    assert room.abandoned_seats


def test_frase_nella_partita_vera(browser, server, room):
    _open(browser, server, room)
    # L'elenco lo manda il server a game:join: senza, il pulsante non c'è
    browser.wait_js("document.querySelector('[data-phrases-button]') !== null", "pulsante delle frasi", 15)
    browser.wait_js("document.querySelector('[data-phrases-button]').disabled === false", "pulsante acceso", 15)
    browser.click("[data-phrases-button]")
    browser.wait_js("document.querySelector('[data-phrase-code]') !== null", "elenco delle frasi")
    phrase = browser.js("""(() => { const p = document.querySelector('[data-phrase-code]');
      return { code: p.dataset.phraseCode, text: p.textContent }; })()""")
    assert phrase["code"] in {item["code"] for item in table_phrases.phrases_event()["phrases"]}
    browser.click(f"[data-phrase-code=\"{phrase['code']}\"]")
    # Il fumetto lo rimanda il server (game:phrase), accanto a te
    bubble = ".seat[data-position=\"bottom\"] [data-phrase-bubble]"
    browser.wait_js(f"document.querySelector({json.dumps(bubble)}) !== null", "il tuo fumetto", 10)
    assert browser.js(f"document.querySelector({json.dumps(bubble)}).textContent") == f"Mario: {phrase['text']}"
    # Subito dopo il pulsante è spento (pausa di P55), e l'elenco chiuso
    assert browser.js("document.querySelector('[data-phrases-button]').disabled") is True
    assert browser.js("document.querySelector('[data-phrases-menu]')") is None
    assert browser.js("document.querySelector('[data-table-status]').textContent") == ""


def test_dalla_home_al_tavolo_e_ritorno_senza_ricaricare(app, server, tmp_path, monkeypatch):
    # Niente database, come la fixture room
    monkeypatch.setattr(room_manager, "_ratings_of", lambda players, mode, cpu_seats: None)
    monkeypatch.setattr(friends_events, "notify_presence", lambda *args, **kwargs: None)
    # Un browser con la home vera (quello delle altre prove risponde da sé su /)
    browser = Browser(find_browser(), tmp_path / "home")
    browser.send("Network.setCookie", name=TEST_COOKIE[0], value=TEST_COOKIE[1], url=server)
    created = None
    try:
        # La home con il login si collega e riceve home:status: c'è il numero degli online
        browser.open(f"{server}/", 390, 844, f"{ONLINE} !== ''", timeout=30)
        # Un segno nella pagina: se la pagina si ricaricasse, sparirebbe
        browser.js("window.__stessa_pagina = true")
        # La partita parte (come dalla coda): il server manda game:start e la home va al tavolo
        with app.app_context():
            created = create_room([Player(user_id=USER_ID, username="Mario"), CPU_PLAYER], "1v1", 150,
                                  rated=False, cpu_seats=(1,))
        browser.wait_js(f"location.pathname === '/game/{created.id}' && {READY}", "tavolo dopo game:start", 30)
        assert browser.js("window.__stessa_pagina === true") is True
        assert browser.js("document.querySelector('[data-table]').dataset.gameId") == created.id
        # "Esci", conferma: game:leave e di nuovo la home, sempre senza ricaricare
        browser.click("[data-leave]")
        browser.wait_js(f"{DIALOG} !== null", "finestra di Esci")
        browser.js(f"[...{DIALOG}.querySelectorAll('button')].find((b) => b.textContent === 'Esci').click()")
        browser.wait_js("location.pathname === '/' && document.querySelector('[data-home]') !== null",
                        "ritorno alla home", 15)
        assert browser.js("window.__stessa_pagina === true") is True
        assert created.finished is True
        # La home nuova chiede lo stato con home:refresh: il numero degli online torna
        browser.wait_js(f"{ONLINE} !== ''", "numero degli online dopo il ritorno", 10)
        assert browser.js("document.querySelector('[data-table]')") is None
    finally:
        browser.close()
        if created is not None:
            created._stop_timers()
            rooms.remove(created.id)


def test_partita_aperta_in_un_altra_scheda(browser, server, room, tmp_path):
    _open(browser, server, room)
    other = _browser(server, tmp_path, "chrome2")
    try:
        _open(other, server, room)
        message = "Questa partita è aperta in un'altra scheda o su un altro dispositivo."
        browser.wait_js(f"document.querySelector('[data-table-message]')?.textContent === {json.dumps(message)}",
                        "messaggio dell'altra scheda", 15)
        assert browser.js("document.querySelectorAll('.table__inner').length") == 0
        # L'altra scheda gioca normalmente
        assert other.js("document.querySelectorAll('.table__inner').length") == 1
    finally:
        other.close()
