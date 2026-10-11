"""P132: l'anello del tempo parte dopo le pause del tavolo.

Il server fa partire il turno dopo ultima presa, riepilogo, mescolata e distribuzione
(P94, P118), e per tutta la pausa la vista dice il turno pieno; la pagina invece faceva
scendere l'anello dal momento in cui arrivava la vista, e a carte distribuite lo
mostrava già più basso. Ora l'anello resta pieno e fermo finché il tavolo è in pausa
(la stessa condizione del ticchettio, P103) e scende da lì.

Una partita vera contro la CPU (P68, non si salva), aperta in Chrome o Edge senza
finestra (tests/browser.py) con le pause vere: alla prima vista la pagina mescola e
distribuisce (P118). Rating e avvisi agli amici non leggono il database (non serve
MySQL). Senza browser il test si salta. Il caso della fine mano, nella prova del
tavolo, è in test_distribuzione.py.
"""

import time

import pytest

from app import create_app
from app.realtime import room_manager
from app.realtime.room import CPU_PLAYER, Player
from app.sockets import friends_events
from tests.browser import TEST_COOKIE, Browser, FakeUser, find_browser, running_server

USER_ID = 12

# L'anello di chi deve giocare (pieno = 1), se è fermo, e se il tavolo distribuisce ancora
RING = """(() => {
  const timer = document.querySelector('[data-timer]');
  return { dealing: document.querySelector('[data-dealt], [data-dealing], [data-shuffling]') !== null,
           ring: timer && { paused: 'paused' in timer.dataset,
                            full: Number(getComputedStyle(timer).getPropertyValue('--timer-p')) } };
})()"""


@pytest.fixture(scope="module")
def app():
    return create_app("testing")


@pytest.fixture(scope="module")
def server(app):
    with running_server(app, FakeUser("Mario", USER_ID)) as url:
        yield url


@pytest.fixture
def browser(server, tmp_path):
    b = Browser(find_browser(), tmp_path / "chrome")
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


def test_l_anello_resta_pieno_durante_la_prima_distribuzione(browser, server, room):
    # Come Browser.open, ma con le animazioni accese già alla prima vista (test_prima_distribuzione.py)
    browser.send("Emulation.setDeviceMetricsOverride", width=390, height=844, deviceScaleFactor=1, mobile=False)
    browser.send("Emulation.setEmulatedMedia", features=[{"name": "prefers-reduced-motion", "value": "no-preference"}])
    browser.send("Page.navigate", url=f"{server}/game/{room.id}")
    browser.wait_js("document.querySelector('[data-timer]') !== null", "tavolo con il turno", 30)
    state = browser.js(RING)
    assert state["dealing"], "la prima distribuzione non si vede"
    assert state["ring"] == {"paused": True, "full": 1}, state
    # Ultimo controllo a distribuzione in corso, poi il primo a distribuzione finita
    last, end = state, time.monotonic() + 10
    while state["dealing"] and time.monotonic() < end:
        last = state
        state = browser.js(RING)
    assert not state["dealing"], "la distribuzione non finisce"
    assert last["ring"] == {"paused": True, "full": 1}, last
    # Appena finita la distribuzione l'anello è ancora (quasi) pieno: prima era già sceso
    # di quanto era durata la distribuzione (circa 2 s su 15)
    assert not state["ring"]["paused"] and state["ring"]["full"] > 0.97, state
