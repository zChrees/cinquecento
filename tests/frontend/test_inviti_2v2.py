"""P59: 2v2 con più amici nella carta-modal "Gioca con un amico" (ModeModal.js, home.js).

Nel browser (Chrome o Edge senza finestra, tests/browser.py), con il server vero e il
database dei test (svuotato e ricreato qui con migrate.py, come in test_chat_vera.py):
Mario è nella pagina; Giulia, Salvo e Rosa sono suoi amici, collegati come client
Socket.IO simulati che accettano gli inviti. Controlla: nel 2v2 si invitano fino a tre
amici e i punti restano fermi, "Gioca" si accende appena uno accetta; con tre amici
tutti e quattro vanno al tavolo; con due il gruppo entra in coda e la schermata di
coda mostra compagno e avversari; nel 1v1 resta un invito alla volta.
P65: un amico bloccato, sbloccato e di nuovo amico torna nella carta senza ricaricare.
Se né Chrome né Edge sono installati i controlli nel browser si saltano.
"""

import importlib.util
import re
import threading
import time
import uuid
from pathlib import Path

import pytest
import requests
import socketio as sio_client
import sqlalchemy as sa

from app import create_app
from app.extensions import db
from app.realtime.invites import invites
from app.realtime.matchmaking import matchmaker
from app.realtime.presence import presence
from app.realtime.room_manager import find_room_of_user, rooms
from app.repositories import friend_repo
from app.services import auth_service, friend_service
from tests.browser import (
    TEST_COOKIE,
    Browser,
    FakeUser,
    find_browser,
    running_server,
    wait,
)

ROOT = Path(__file__).resolve().parents[2]
PASSWORD = "Password-di-prova-1"
FRIENDS = ("Giulia", "Salvo", "Rosa")
WAIT = 10
MODAL = "document.querySelector('[data-mode-modal]')"
PLAY = f"{MODAL}.querySelector('[data-play]')"
HINT = f"{MODAL}.querySelector('[data-invite-hint]').textContent"


def _migrate(url):
    spec = importlib.util.spec_from_file_location("migrate", ROOT / "scripts" / "migrate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.migrate(url, report=lambda _msg: None)


@pytest.fixture(scope="module")
def app():
    app = create_app("testing")
    with app.app_context():
        assert db.engine.url.database.endswith("_test")
        with db.engine.begin() as conn:
            tables = conn.execute(sa.text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE()"
            )).scalars().all()
            conn.execute(sa.text("SET FOREIGN_KEY_CHECKS = 0"))
            for table in tables:
                conn.execute(sa.text(f"DROP TABLE `{table}`"))
            conn.execute(sa.text("SET FOREIGN_KEY_CHECKS = 1"))
        _migrate(db.engine.url)
    return app


@pytest.fixture(scope="module")
def users(app):
    with app.app_context():
        ids = {name: auth_service.register(name, f"{name.lower()}@esempio.it", PASSWORD).id
               for name in ("Mario", *FRIENDS)}
        for name in FRIENDS:
            friend_service.send_request(ids["Mario"], uuid.uuid4().hex, name)
            friend_service.accept_request(ids[name], ids["Mario"])
        db.session.commit()
    return ids


@pytest.fixture(scope="module")
def server(app, users):
    with running_server(app, FakeUser("Mario", users["Mario"])) as url:
        yield url


class Friend:
    """Un amico collegato come client Socket.IO, con il login vero (modulo con CSRF)."""

    def __init__(self, url, name):
        session = requests.Session()
        page = session.get(f"{url}/auth/login", timeout=WAIT).text
        token = re.search(r'name="csrf_token" type="hidden" value="([^"]+)"', page)[1]
        answer = session.post(f"{url}/auth/login", data={"csrf_token": token, "username": name,
                                                          "password": PASSWORD},
                              allow_redirects=False, timeout=WAIT)
        assert answer.status_code == 302, "login di prova non riuscito"
        cookie = "; ".join(f"{k}={v}" for k, v in session.cookies.items())
        self.received, self.starts, self.updates = [], [], []
        self._cond = threading.Condition()
        self.client = sio_client.Client(reconnection=False)
        self.client.on("invite:received", lambda data: self._add(self.received, data))
        self.client.on("game:start", lambda data: self._add(self.starts, data))
        self.client.on("invite:update", lambda data: self._add(self.updates, data))
        self.client.connect(url, headers={"Cookie": cookie}, transports=["websocket"], wait_timeout=WAIT)

    def _add(self, items, data):
        with self._cond:
            items.append(data)
            self._cond.notify_all()

    def _wait(self, items, what):
        with self._cond:
            assert self._cond.wait_for(lambda: items, WAIT), f"non arrivato: {what}"
            return items[-1]

    def accept(self):
        invite = self._wait(self.received, "invite:received")
        answer = self.client.call("invite:accept", {"invite_id": invite["invite_id"]}, timeout=WAIT)
        assert answer["ok"] is True, answer

    def update(self, status):
        """Aspetta invite:update con quello stato (contratto 5.3)."""
        with self._cond:
            assert self._cond.wait_for(lambda: any(u["status"] == status for u in self.updates), WAIT),                 f"invite:update {status} non arrivato: {self.updates}"

    def game_start(self):
        return self._wait(self.starts, "game:start")

    def forget(self):
        """Dimentica gli eventi della prova prima."""
        with self._cond:
            self.received.clear()
            self.starts.clear()
            self.updates.clear()


@pytest.fixture(scope="module")
def connected_friends(server, users):
    """I tre amici collegati una volta sola per tutto il file: scollegare un client
    Socket.IO costa circa 3 secondi, e la suite frontend ha un limite di 120 (runner)."""
    connected = {name: Friend(server, name) for name in FRIENDS}
    yield connected
    closing = [threading.Thread(target=f.client.disconnect) for f in connected.values()]
    for thread in closing:
        thread.start()
    for thread in closing:
        thread.join(WAIT)


@pytest.fixture
def friends(connected_friends, users):
    for friend in connected_friends.values():
        friend.forget()
    # la pagina legge la lista degli amici appena si apre: devono risultare già online
    wait(lambda: all(presence.is_online(users[name]) for name in FRIENDS) or None, WAIT, "amici online")
    yield connected_friends
    for user_id in users.values():
        invites.cancel_all_of(user_id)
        matchmaker.queue.leave(user_id)
        room = find_room_of_user(user_id)
        if room is not None:
            room.run(room._stop_timers)
            rooms.remove(room.id)


@pytest.fixture
def browser(server, tmp_path):
    b = Browser(find_browser(), tmp_path / "chrome")
    b.send("Network.setCookie", name=TEST_COOKIE[0], value=TEST_COOKIE[1], url=server)
    yield b
    b.close()


def _open_modal(browser, server, users, mode):
    """La home collegata (4 online: Mario e i tre amici) e la carta "Gioca con un amico"
    con i tre amici veri. In sviluppo e nei test la pagina parte con gli amici finti di
    app/static/dev/ finché non arriva GET /friends/, e la carta disegna la lista che c'è
    quando si apre: se è ancora quella finta, si chiude e si riapre."""
    browser.open(f"{server}/", 390, 844, "document.querySelector('[data-online-count]')?.textContent === '4'",
                 timeout=60)
    _open_card(browser, users, mode)


def _open_card(browser, users, mode):
    """Apre la carta "Gioca con un amico" finché, entro WAIT secondi, non mostra i tre amici
    veri (la lista la rilegge la pagina da sola: la carta disegna quella che c'è quando si
    apre). Conta il tempo, non i tentativi: senza finestra l'animazione non dura niente e
    dieci aperture possono finire prima che arrivi la risposta di GET /friends/."""
    expected = sorted(users[name] for name in FRIENDS)
    rows = f"[...{MODAL}.querySelectorAll('[data-invite-user]')].map((b) => Number(b.dataset.inviteUser))"
    deadline = time.monotonic() + WAIT
    while True:
        browser.click(f"[data-tile][data-kind='amico'][data-mode='{mode}']")
        _wait_card_still(browser, open_=True)
        if sorted(browser.js(rows)) == expected:
            return
        if time.monotonic() > deadline:
            pytest.fail(f"la carta non mostra i tre amici veri: {browser.js(rows)}", pytrace=False)
        _close_card(browser)
        time.sleep(0.1)


def _wait_card_still(browser, open_):
    """Carta aperta (o chiusa) e ferma: durante l'animazione non si chiude."""
    state = f"{MODAL}?.open" if open_ else f"!{MODAL}?.open"
    browser.wait_js(f"{state} && !({MODAL}?.querySelector('.mode-modal__flip')"
                    ".getAnimations({ subtree: true }).length)", "carta ferma")


def _close_card(browser):
    browser.key("Escape", "Escape", 27)
    _wait_card_still(browser, open_=False)


def _invite_button(users, name):
    return f"{MODAL}.querySelector('[data-invite-user=\"{users[name]}\"]')"


def _invite(browser, users, names):
    for name in names:
        browser.js(f"{_invite_button(users, name)}.click()")
        browser.wait_js(f"{_invite_button(users, name)}.dataset.state === 'pending'", f"invito a {name}")


def test_tre_amici_invitati_poi_tutti_al_tavolo(browser, server, users, friends):
    _open_modal(browser, server, users, "2v2")
    _invite(browser, users, FRIENDS)
    state = browser.js(f"""(() => ({{
      enabled: [...{MODAL}.querySelectorAll('[data-invite-user]')].filter((b) => !b.disabled).length,
      targets: [...{MODAL}.querySelectorAll('input[name="target"]')].every((i) => i.disabled),
      play: {PLAY}.disabled }}))()""")
    assert state == {"enabled": 0, "targets": True, "play": True}
    # il pulsante cambia subito, la richiesta arriva al server un attimo dopo
    wait(lambda: len(invites.group_of(users["Mario"])) == 3 or None, WAIT, "tre inviti sul server")

    friends["Giulia"].accept()
    browser.wait_js(f"!{PLAY}.disabled", "Gioca attivo dopo il primo sì")
    assert "puoi giocare subito" in browser.js(HINT)
    friends["Salvo"].accept()
    friends["Rosa"].accept()
    browser.wait_js(f"{HINT}.includes('hanno accettato: puoi giocare!')", "tutti hanno accettato")

    browser.js(f"{PLAY}.click()")
    game_ids = {friend.game_start()["game_id"] for friend in friends.values()}
    assert len(game_ids) == 1
    game_id = game_ids.pop()
    assert rooms.get(game_id).rated is False
    # Mario va al tavolo e si siede: si aspetta il collegamento prima di chiudere il browser
    browser.wait_js(f"location.pathname === '/game/{game_id}'"
                    " && document.querySelectorAll('[data-seat]').length === 4", "tavolo con quattro posti",
                    timeout=30)


def test_due_amici_il_gruppo_in_coda_con_compagno_e_avversari(browser, server, users, friends):
    _open_modal(browser, server, users, "2v2")
    _invite(browser, users, ("Giulia", "Salvo"))
    assert browser.js(f"{_invite_button(users, 'Rosa')}.disabled") is False  # c'è ancora posto
    friends["Giulia"].accept()
    friends["Salvo"].accept()
    browser.wait_js(f"{HINT}.includes('Giulia e Salvo hanno accettato')", "due amici hanno accettato")

    browser.js(f"{PLAY}.click()")
    overlay = "document.querySelector('[data-queue-overlay]')"
    browser.wait_js(f"{overlay}?.open", "schermata di coda")
    text = browser.js(f"{overlay}.textContent")
    assert "Con gli amici · 2v2 · 500 punti" in text
    assert "Cerco il quarto giocatore…" in text
    has_partner = browser.js(f"{overlay}.querySelector('[data-queue-partner]') !== null")
    opponents = browser.js(f"{overlay}.querySelector('[data-queue-opponents]').dataset.queueOpponents")
    assert len(opponents.split()) == (1 if has_partner else 2)
    assert "Contro " in text
    for name in ("Mario", "Giulia", "Salvo"):
        assert users[name] in matchmaker.queue, name
    assert users["Rosa"] not in matchmaker.queue


def test_nel_1v1_un_invito_alla_volta(browser, server, users, friends):
    _open_modal(browser, server, users, "1v1")
    _invite(browser, users, ("Giulia",))
    enabled = browser.js(f"[...{MODAL}.querySelectorAll('[data-invite-user]')].filter((b) => !b.disabled).length")
    assert enabled == 0
    assert browser.js(f"{PLAY}.disabled") is True


def test_amico_bloccato_sbloccato_e_di_nuovo_amico_torna_nella_carta(app, browser, server, users, friends):
    """P65: Mario blocca Giulia, la sblocca, Giulia gli manda la richiesta e Mario accetta
    (da un'altra scheda, come il pannello amici): senza ricaricare la home, Giulia torna
    tra gli amici online nella carta "Gioca con un amico"."""
    _open_modal(browser, server, users, "2v2")
    _close_card(browser)
    mario, giulia = users["Mario"], users["Giulia"]
    loaded = ("performance.getEntriesByType('resource')"
              ".filter((e) => new URL(e.name).pathname === '/friends/').length")
    before = browser.js(loaded)
    try:
        with app.app_context():
            friend_service.block(mario, uuid.uuid4().hex, giulia)
            friend_service.unblock(mario, giulia)
            friend_service.send_request(giulia, uuid.uuid4().hex, "Mario")
        # Prima di accettare la pagina ha finito di rileggere la lista dopo i tre avvisi
        # (blocca, sblocca, richiesta: home e pannello amici, 6 letture), così l'unica
        # rilettura che può riportare Giulia è quella dopo l'accettazione
        browser.wait_js(f"{loaded} >= {before + 6}"
                        " && document.querySelector('[data-friends-badge]').textContent === '1'",
                        "lista riletta dopo la richiesta")
        with app.app_context():
            friend_service.accept_request(mario, giulia)
        _open_card(browser, users, "2v2")
    finally:
        with app.app_context():
            if giulia not in {u.id for u in friend_repo.friends_of(mario)}:
                friend_service.unblock(mario, giulia)
                friend_service.send_request(giulia, uuid.uuid4().hex, "Mario")
                friend_service.accept_request(mario, giulia)


@pytest.mark.parametrize("mode", ["1v1", "2v2"])
def test_invito_accettato_e_carta_chiusa_l_amico_lo_sa(browser, server, users, friends, mode):
    """P83: Giulia accetta, poi Mario chiude la carta: Giulia riceve "cancelled" e torna libera."""
    _open_modal(browser, server, users, mode)
    _invite(browser, users, ("Giulia",))
    friends["Giulia"].accept()
    browser.wait_js(f"!{PLAY}.disabled", "Gioca attivo dopo il sì")
    _close_card(browser)
    friends["Giulia"].update("cancelled")
    assert invites.open_of(users["Giulia"]) is None


def _network(browser, offline):
    browser.send("Network.enable")
    browser.send("Network.emulateNetworkConditions", offline=offline, latency=0,
                 downloadThroughput=-1, uploadThroughput=-1)


def test_invitato_che_perde_la_connessione_non_resta_ad_aspettare(browser, server, users, friends):
    """P83, il difetto della prova a mano: Mario accetta l'invito di Giulia e poi il suo
    telefono perde la rete senza avvisare. Il server annulla l'invito (Mario è rimasto senza
    schede), ma "cancelled" non può arrivargli: la finestra lo dice da sola e, tornata la
    connessione, non resta su "aspettiamo che Giulia avvii la partita"."""
    dialog = "document.querySelector('[data-invite-dialog]')"
    browser.open(f"{server}/", 390, 844, "document.querySelector('[data-online-count]')?.textContent === '4'",
                 timeout=60)
    answer = friends["Giulia"].client.call("invite:send", {
        "request_id": uuid.uuid4().hex, "user_id": users["Mario"], "mode": "2v2", "target_score": 300,
    }, timeout=WAIT)
    assert answer["ok"] is True, answer
    browser.wait_js(f"{dialog}?.open", "finestra dell'invito")
    browser.js(f"{dialog}.querySelector('[data-invite-accept]').click()")
    browser.wait_js(f"{dialog}.dataset.inviteStatus === 'accepted'", "invito accettato")

    _network(browser, offline=True)
    friends["Giulia"].update("cancelled")  # il server ha annullato (Mario senza schede)
    browser.wait_js(f"{dialog}.dataset.inviteStatus === 'connection_lost'", "invito annullato nella finestra")
    note = browser.js(f"{dialog}.querySelector('[data-invite-note]').textContent")
    assert note == "La connessione è caduta: l'invito è stato annullato."
    _network(browser, offline=False)
    browser.wait_js(f"!{dialog} && document.querySelector('[data-online-count]')?.textContent === '4'",
                    "finestra chiusa e di nuovo collegato", timeout=30)
    # Mario è di nuovo libero: Giulia lo può invitare ancora
    friends["Giulia"].forget()
    answer = friends["Giulia"].client.call("invite:send", {
        "request_id": uuid.uuid4().hex, "user_id": users["Mario"], "mode": "1v1", "target_score": 150,
    }, timeout=WAIT)
    assert answer["ok"] is True, answer
    browser.wait_js(f"{dialog}?.dataset.inviteStatus === 'pending'", "nuovo invito ricevuto")
