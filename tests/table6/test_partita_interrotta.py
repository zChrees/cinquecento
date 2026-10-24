"""P95: partita interrotta dal riavvio del server.

Le partite in corso stanno solo in memoria: se il server si riavvia, la pagina del
tavolo si ricollega da sola, manda game:join e il server risponde not_found. Prima
la pagina scriveva solo il messaggio nella riga di stato e lasciava il tavolo com'era:
non si poteva né giocare né uscire. Ora al posto del tavolo c'è il riquadro "La
partita è stata interrotta" con "Torna alla home", e dopo 5 secondi si torna alla home
da soli (scelta di Christian).

Qui il riavvio si imita così: una partita vera contro la CPU (P68, non si salva), poi
la stanza si toglie dall'elenco (come se il server fosse ripartito senza) e il server
chiude il collegamento della pagina come un calo di rete (P33): la pagina si ricollega
e trova la partita sparita. Rating e avvisi agli amici non leggono il database (non
serve MySQL).
R4: a partita finita la stanza si toglie 10 minuti dopo; se la pagina mostra
ancora il risultato, lo stesso not_found non fa comparire il riquadro.
Chrome o Edge senza finestra (tests/browser.py); senza browser il test si salta.
Senza il build della SPA il test si salta (table_path di tests/spa.py).
"""

import time

import pytest

from app import create_app
from app.extensions import socketio
from app.realtime import room_manager
from app.realtime.presence import presence
from app.realtime.room import CPU_PLAYER, Player
from app.sockets import friends_events
from tests.browser import TEST_COOKIE, Browser, FakeUser, find_browser, running_server
from tests.spa import table_path

USER_ID = 12
GONE = "document.querySelector('[data-game-gone]')"


@pytest.fixture(scope="module")
def app():
    return create_app("testing")


@pytest.fixture(scope="module")
def server(app):
    with running_server(app, FakeUser("Mario", USER_ID)) as url:
        yield url


@pytest.fixture
def browser(server, tmp_path):
    # La home vera si collegherebbe al tempo reale e userebbe il database: qui basta sapere
    # che la pagina ci va, quindi il browser risponde da sé (un collegamento lasciato a metà
    # a fine test può bloccare lo spegnimento del server, punto delicato di P58)
    b = Browser(find_browser(), tmp_path / "chrome", routes={f"{server}/": lambda _request: (200, {"home": True})})
    b.send("Network.setCookie", name=TEST_COOKIE[0], value=TEST_COOKIE[1], url=server)
    yield b
    b.close()


@pytest.fixture
def room(app, monkeypatch):
    # Niente database: né rating né avvisi agli amici (la suite table non prepara MySQL)
    monkeypatch.setattr(room_manager, "_ratings_of", lambda players, mode, cpu_seats: None)
    monkeypatch.setattr(friends_events, "notify_presence", lambda *args, **kwargs: None)
    with app.app_context():
        created = room_manager.create_room([Player(user_id=USER_ID, username="Mario"), CPU_PLAYER], "1v1", 150,
                                           rated=False, cpu_seats=(1,))
    yield created
    created._stop_timers()
    room_manager.rooms.remove(created.id)


def _restart(room):
    """Il server "riparte": la stanza non c'è più e il collegamento della pagina cade."""
    room._stop_timers()
    room_manager.rooms.remove(room.id)
    for sid in presence.tabs_of(USER_ID):
        socketio.server.eio.disconnect(socketio.server.manager.eio_sid_from_sid(sid, "/"))


def test_riquadro_e_ritorno_alla_home(browser, server, room):
    browser.open(f"{server}{table_path(room.id)}", 390, 844, "document.querySelector('[data-mode]') !== null", timeout=30)
    _restart(room)
    browser.wait_js(f"{GONE} !== null", "riquadro della partita interrotta", 20)
    gone = browser.js(f"({{ title: {GONE}.querySelector('h2').textContent, text: {GONE}.querySelector('p').textContent,"
                      f" link: {GONE}.querySelector('a').getAttribute('href'), role: {GONE}.getAttribute('role') }})")
    assert gone == {"title": "La partita è stata interrotta",
                    "text": "Il server si è riavviato o la partita non esiste più.",
                    "link": "/", "role": "alert"}
    # Il tavolo non c'è più: niente carte né pulsanti da usare
    assert browser.js("document.querySelectorAll('.table__inner, [data-hand] button').length") == 0
    start = time.monotonic()
    browser.wait_js("location.pathname === '/' && document.readyState === 'complete'", "ritorno alla home", 15)
    assert 4 < time.monotonic() - start < 9


RESULT = "document.querySelector('[data-result]')"


def test_a_partita_finita_resta_il_risultato(browser, server, room):
    """R4: 10 minuti dopo la fine il server toglie la stanza. Se la pagina mostra ancora il
    risultato e si ricollega, il not_found di game:join non è una partita interrotta: niente
    riquadro, il risultato resta (si torna alla home con "Esci")."""
    browser.open(f"{server}{table_path(room.id)}", 390, 844, "document.querySelector('[data-mode]') !== null", timeout=30)
    # La partita finisce (Mario abbandona) e la pagina mostra il risultato
    assert room.abandon(0)
    room.broadcast_states()
    browser.wait_js(f"{RESULT} !== null", "riquadro del risultato", 20)
    # La stanza sparisce (come dopo i 10 minuti di R4) e il collegamento cade: la pagina si
    # ricollega da sola e manda game:join, che risponde not_found
    # old_tabs: le schede di prima; si aspetta una scheda nuova (la pagina ricollegata)
    old_tabs = set(presence.tabs_of(USER_ID))
    _restart(room)
    deadline = time.monotonic() + 20
    while len(set(presence.tabs_of(USER_ID)) - old_tabs) == 0:
        assert time.monotonic() < deadline, "la pagina non si è ricollegata"
        time.sleep(0.05)
    # Per 3 secondi dopo il rientro (la risposta a game:join arriva in pochi millesimi):
    # nessun riquadro "interrotta", il risultato resta e la pagina non torna alla home
    end = time.monotonic() + 3
    while time.monotonic() < end:
        assert browser.js(f"{GONE} === null && {RESULT} !== null && location.pathname !== '/'"), \
            "a partita finita la pagina ha mostrato la partita interrotta"
        time.sleep(0.1)
