"""Passo 7c della migrazione: gli inviti a partita nella home React (dal passo 7d su /;
prima /prova-home).

Gli stessi casi di test_invito_ricevuto.py (P47) e test_inviti_2v2.py (P59, P65, P83),
che provano la home Jinja (dal passo 7d su /vecchia-home), sulla home React: stesso HTML, stesse classi e stessi
data-* di ModeModal.js (carta "Gioca con un amico") e InviteDialog.js (invito ricevuto).

Nel browser (Chrome o Edge senza finestra, tests/browser.py), con il server vero e il
database dei test, svuotato e ricreato qui con migrate.py (la SPA legge i dati veri).
Mario è nella pagina, con il login finto di running_server (FakeUser con il suo id vero);
Giulia, Salvo e Rosa sono suoi amici, collegati come client Socket.IO simulati con il
login vero (/api/auth/login), che accettano gli inviti.
Controlla:
- invito ricevuto: chi invita, modalità e punti (il nome entra come testo, mai come
  HTML), il conto alla rovescia, "Accetta" e l'attesa di chi ha invitato,
  l'annullamento, l'errore del server nella finestra, Esc che rifiuta;
- nel 2v2 si invitano fino a tre amici e i punti restano fermi, "Gioca" si accende
  appena uno accetta; con tre amici tutti e quattro vanno al tavolo; con due il gruppo
  entra in coda e la schermata di coda mostra compagno e avversari;
- nel 1v1 resta un invito alla volta;
- P65: un amico bloccato, sbloccato e di nuovo amico torna nella carta senza ricaricare;
- P83: invito accettato e carta chiusa, l'amico lo sa; l'invitato che perde la rete
  non resta ad aspettare;
- la CSP non blocca niente.
Differenze dalla home Jinja: la carta-modal e la finestra dell'invito chiuse non ci
sono nella pagina (null); il collegamento si legge da [data-friends-panel]
(data-connection="connected"), non da core/socket.js.
Senza browser, o senza il build della SPA, i controlli si saltano.
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
from app.extensions import db, socketio
from app.realtime.events import user_channel
from app.realtime.invites import invites
from app.realtime.matchmaking import matchmaker
from app.realtime.presence import presence
from app.realtime.room import Player
from app.realtime.room_manager import find_room_of_user, rooms
from app.repositories import friend_repo
from app.services import auth_service, friend_service
from tests import accounts
from tests.browser import (
    TEST_COOKIE,
    Browser,
    FakeUser,
    find_browser,
    running_server,
    wait,
)
from tests.spa import needs_spa

ROOT = Path(__file__).resolve().parents[2]
PAGE = "/"  # dal passo 7d (fino al 7c era /prova-home)
PASSWORD = "Password-di-prova-7c"
FRIENDS = ("Giulia", "Salvo", "Rosa")
WAIT = 10
# Chi manda gli inviti "ricevuti" creati dal test: non è un utente del database,
# e il nome con dell'HTML deve restare testo
SENDER = Player(9999, "<b>Giulia</b>")
# Come test_csp.py: registra ogni risorsa bloccata dalla CSP
RECORD = (
    "window.__csp = [];"
    "document.addEventListener('securitypolicyviolation',"
    " e => window.__csp.push(e.effectiveDirective + ' ' + e.blockedURI));"
)
CONNECTED = "document.querySelector('[data-friends-panel]')?.dataset.connection === 'connected'"
# READY: home collegata al tempo reale, con Mario e i tre amici online (home:status)
READY = f"{CONNECTED} && document.querySelector('[data-online-count]')?.textContent === '4'"
MODAL = "document.querySelector('[data-mode-modal]')"
PLAY = f"{MODAL}.querySelector('[data-play]')"
HINT = f"{MODAL}.querySelector('[data-invite-hint]').textContent"
DIALOG = "document.querySelector('[data-invite-dialog]')"
OVERLAY = "document.querySelector('[data-queue-overlay]')"


def _migrate(url):
    spec = importlib.util.spec_from_file_location("migrate", ROOT / "scripts" / "migrate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.migrate(url, report=lambda _msg: None)


@pytest.fixture(scope="module")
def app():
    needs_spa()
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
    # Con il cookie di prova risulta collegato Mario, con il suo id vero
    with running_server(app, FakeUser("Mario", users["Mario"])) as url:
        yield url


class Friend:
    """Un amico collegato come client Socket.IO, con il login vero (/api/auth/login con CSRF)."""

    def __init__(self, url, name):
        session = requests.Session()
        answer = accounts.login_http(session, url, name, PASSWORD)
        assert accounts.ok(answer), "login di prova non riuscito"
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
            assert self._cond.wait_for(lambda: any(u["status"] == status for u in self.updates), WAIT), \
                f"invite:update {status} non arrivato: {self.updates}"

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
    Socket.IO costa circa 3 secondi, e ogni suite ha un limite di tempo (runner)."""
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
    # Nessuna prova lascia inviti aperti, qualcuno in coda o una partita aperta
    for user_id in users.values():
        invites.cancel_all_of(user_id)
        matchmaker.queue.leave(user_id)
        room = find_room_of_user(user_id)
        if room is not None:
            room.run(room._stop_timers)
            rooms.remove(room.id)


@pytest.fixture
def browser(server, tmp_path):
    # Un browser nuovo per ogni prova (la cronologia tiene lo stato del pannello amici)
    b = Browser(find_browser(), tmp_path / "chrome")
    b.send("Network.setCookie", name=TEST_COOKIE[0], value=TEST_COOKIE[1], url=server)
    b.send("Page.enable")  # senza, lo script qui sotto non parte con le pagine nuove
    b.send("Page.addScriptToEvaluateOnNewDocument", source=RECORD)
    yield b
    b.close()


def _open_home(browser, server):
    browser.open(f"{server}{PAGE}", 390, 844, READY, timeout=60)


def _open_modal(browser, server, users, mode):
    """La home collegata (4 online: Mario e i tre amici) e la carta "Gioca con un amico"
    con i tre amici veri."""
    _open_home(browser, server)
    _open_card(browser, users, mode)


def _open_card(browser, users, mode):
    """Apre la carta "Gioca con un amico" finché, entro WAIT secondi, non mostra i tre amici
    veri (la carta disegna la lista che c'è quando si apre, e GET /friends/ può arrivare
    dopo). Conta il tempo, non i tentativi: senza finestra l'animazione non dura niente."""
    expected = sorted(users[name] for name in FRIENDS)
    rows = f"[...{MODAL}.querySelectorAll('[data-invite-user]')].map((b) => Number(b.dataset.inviteUser))"
    deadline = time.monotonic() + WAIT
    while True:
        browser.click(f"[data-tile][data-kind='amico'][data-mode='{mode}']")
        _wait_card_open(browser)
        if sorted(browser.js(rows)) == expected:
            return
        if time.monotonic() > deadline:
            pytest.fail(f"la carta non mostra i tre amici veri: {browser.js(rows)}", pytrace=False)
        _close_card(browser)
        time.sleep(0.1)


def _wait_card_open(browser):
    """Carta aperta e ferma: durante l'animazione non si chiude."""
    browser.wait_js(f"{MODAL}?.open === true && !({MODAL}.querySelector('.mode-modal__flip')"
                    "?.getAnimations({ subtree: true }).length)", "carta aperta e ferma")


def _close_card(browser):
    """Esc chiude la carta: nella home React la carta chiusa non c'è più nella pagina."""
    browser.key("Escape", "Escape", 27)
    browser.wait_js(f"{MODAL} === null", "carta chiusa")


def _invite_button(users, name):
    return f"{MODAL}.querySelector('[data-invite-user=\"{users[name]}\"]')"


def _invite(browser, users, names):
    for name in names:
        browser.js(f"{_invite_button(users, name)}.click()")
        browser.wait_js(f"{_invite_button(users, name)}.dataset.state === 'pending'", f"invito a {name}")


def _receive(users, mode="2v2", target_score=300):
    """Un invito per Mario creato sul server vero e mandato alla pagina con
    invite:received, come farebbe invite:send di un amico."""
    invite = invites.send(SENDER, Player(users["Mario"], "Mario"), mode, target_score)
    socketio.emit("invite:received", invites.data(invite), to=user_channel(users["Mario"]))
    return invite


# --- Invito ricevuto (P47) ----------------------------------------------------------


def test_invito_ricevuto_con_chi_invita_e_conto_alla_rovescia(browser, server, users, friends):
    _open_home(browser, server)
    invite = _receive(users)
    browser.wait_js(f"{DIALOG}?.open", "finestra dell'invito")
    facts = browser.js(f"""(() => {{ const d = {DIALOG};
      return {{id: d.dataset.inviteDialog, status: d.dataset.inviteStatus, text: d.textContent,
               bold: d.querySelector('b') !== null,
               seconds: d.querySelector('[data-invite-seconds]').textContent,
               accept: !d.querySelector('[data-invite-accept]').hidden}}; }})()""")
    assert facts["id"] == invite.invite_id
    assert facts["status"] == "pending"
    assert "<b>Giulia</b> ti invita a una partita 2v2 tra amici, a 300 punti." in facts["text"]
    assert facts["bold"] is False
    assert re.fullmatch(r"0:5\d|1:00", facts["seconds"])
    assert facts["accept"] is True
    # Il conto alla rovescia scende da solo
    browser.wait_js(f"{DIALOG}.querySelector('[data-invite-seconds]').textContent !== {facts['seconds']!r}",
                    "conto alla rovescia", 5)
    assert browser.js("window.__csp") == []


def test_accetta_poi_aspetta_chi_ha_invitato_e_l_annullamento(browser, server, users, friends):
    _open_home(browser, server)
    invite = _receive(users, "1v1", 150)
    browser.wait_js(f"{DIALOG}?.open", "finestra dell'invito")
    browser.js(f"{DIALOG}.querySelector('[data-invite-accept]').click()")
    browser.wait_js(f"{DIALOG}.dataset.inviteStatus === 'accepted'", "invito accettato")
    assert invites.get(invite.invite_id).status == "accepted"
    note = browser.js(f"{DIALOG}.querySelector('[data-invite-note]').textContent")
    assert note == "Hai accettato: aspettiamo che <b>Giulia</b> avvii la partita…"
    assert browser.js(f"{DIALOG}.querySelector('[data-invite-accept]').hidden") is True

    invites.cancel(invite.invite_id, SENDER.user_id)  # chi ha invitato chiude la carta
    browser.wait_js(f"{DIALOG}.dataset.inviteStatus === 'cancelled'", "annullamento")
    assert "ha annullato l'invito" in browser.js(f"{DIALOG}.querySelector('[data-invite-note]').textContent")
    browser.js(f"{DIALOG}.querySelector('.icon-btn').click()")  # la X chiude subito
    browser.wait_js(f"{DIALOG} === null", "chiusura della finestra")


def test_errore_del_server_nella_finestra(browser, server, users, friends):
    _open_home(browser, server)
    invite = _receive(users)
    browser.wait_js(f"{DIALOG}?.open", "finestra dell'invito")
    invites.cancel(invite.invite_id, SENDER.user_id)  # annullato, ma la pagina non lo sa ancora
    browser.js(f"{DIALOG}.querySelector('[data-invite-accept]').click()")
    browser.wait_js(f"{DIALOG}?.querySelector('[data-invite-note]').textContent !== ''", "risposta del server")
    # L'annullamento arriva comunque con invite:update: la finestra lo mostra
    browser.wait_js(f"{DIALOG}.dataset.inviteStatus === 'cancelled'", "annullamento")


def test_esc_rifiuta(browser, server, users, friends):
    _open_home(browser, server)
    invite = _receive(users)
    browser.wait_js(f"{DIALOG}?.open", "finestra dell'invito")
    browser.key("Escape", "Escape", 27)
    browser.wait_js(f"{DIALOG} === null", "chiusura con Esc")
    assert invites.get(invite.invite_id).status == "declined"


# --- Carta "Gioca con un amico" (P59) ---------------------------------------------


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
    browser.wait_js(f"{OVERLAY}?.open === true", "schermata di coda")
    assert browser.js(f"{MODAL}") is None  # la carta si è chiusa
    text = browser.js(f"{OVERLAY}.textContent")
    assert "Con gli amici · 2v2 · 500 punti" in text
    assert "Cerco il quarto giocatore…" in text
    has_partner = browser.js(f"{OVERLAY}.querySelector('[data-queue-partner]') !== null")
    opponents = browser.js(f"{OVERLAY}.querySelector('[data-queue-opponents]').dataset.queueOpponents")
    assert len(opponents.split()) == (1 if has_partner else 2)
    assert "Contro " in text
    for name in ("Mario", "Giulia", "Salvo"):
        assert users[name] in matchmaker.queue, name
    assert users["Rosa"] not in matchmaker.queue
    assert browser.js("window.__csp") == []


def test_nel_1v1_un_invito_alla_volta(browser, server, users, friends):
    _open_modal(browser, server, users, "1v1")
    _invite(browser, users, ("Giulia",))
    enabled = browser.js(f"[...{MODAL}.querySelectorAll('[data-invite-user]')].filter((b) => !b.disabled).length")
    assert enabled == 0
    assert browser.js(f"{PLAY}.disabled") is True
    assert browser.js(HINT) == "Invito inviato a Giulia. Aspettiamo che accetti…"


def _friends_reads(browser):
    return browser.js("performance.getEntriesByType('resource')"
                      ".filter((e) => new URL(e.name).pathname === '/friends/').length")


def _wait_friends_reads_quiet(browser, at_least):
    """Aspetta almeno `at_least` letture di GET /friends/ finite e poi nessuna lettura
    nuova per un secondo. La home Jinja contava 6 letture esatte (home e pannello): nella
    home React il numero dipende da chi rilegge la lista, quindi si aspetta la calma."""
    browser.wait_js(f"performance.getEntriesByType('resource')"
                    f".filter((e) => new URL(e.name).pathname === '/friends/').length >= {at_least}",
                    "letture della lista dopo gli avvisi")
    last, since = _friends_reads(browser), time.monotonic()
    deadline = since + WAIT
    while time.monotonic() - since < 1:
        assert time.monotonic() < deadline, "la pagina continua a rileggere la lista degli amici"
        time.sleep(0.1)
        now = _friends_reads(browser)
        if now != last:
            last, since = now, time.monotonic()


def test_amico_bloccato_sbloccato_e_di_nuovo_amico_torna_nella_carta(app, browser, server, users, friends):
    """P65: Mario blocca Giulia, la sblocca, Giulia gli manda la richiesta e Mario accetta
    (da un'altra scheda, come il pannello amici): senza ricaricare la home, Giulia torna
    tra gli amici online nella carta "Gioca con un amico"."""
    _open_modal(browser, server, users, "2v2")
    _close_card(browser)
    mario, giulia = users["Mario"], users["Giulia"]
    before = _friends_reads(browser)
    try:
        with app.app_context():
            friend_service.block(mario, uuid.uuid4().hex, giulia)
            friend_service.unblock(mario, giulia)
            friend_service.send_request(giulia, uuid.uuid4().hex, "Mario")
        # Prima di accettare la pagina ha finito di rileggere la lista dopo i tre avvisi
        # (blocca, sblocca, richiesta), così l'unica rilettura che può riportare Giulia è
        # quella dopo l'accettazione
        browser.wait_js("document.querySelector('[data-friends-badge]')?.textContent === '1'",
                        "richiesta di Giulia nel contatore")
        _wait_friends_reads_quiet(browser, before + 3)
        with app.app_context():
            friend_service.accept_request(mario, giulia)
        _open_card(browser, users, "2v2")
    finally:
        with app.app_context():
            if giulia not in {u.id for u in friend_repo.friends_of(mario)}:
                friend_service.unblock(mario, giulia)
                friend_service.send_request(giulia, uuid.uuid4().hex, "Mario")
                friend_service.accept_request(mario, giulia)


# --- Inviti e rete persa (P83) -----------------------------------------------------


@pytest.mark.parametrize("mode", ["1v1", "2v2"])
def test_invito_accettato_e_carta_chiusa_l_amico_lo_sa(browser, server, users, friends, mode):
    """Giulia accetta, poi Mario chiude la carta: Giulia riceve "cancelled" e torna libera."""
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
    """Il difetto della prova a mano: Mario accetta l'invito di Giulia e poi il suo
    telefono perde la rete senza avvisare. Il server annulla l'invito (Mario è rimasto senza
    schede), ma "cancelled" non può arrivargli: la finestra lo dice da sola e, tornata la
    connessione, non resta su "aspettiamo che Giulia avvii la partita"."""
    _open_home(browser, server)
    answer = friends["Giulia"].client.call("invite:send", {
        "request_id": uuid.uuid4().hex, "user_id": users["Mario"], "mode": "2v2", "target_score": 300,
    }, timeout=WAIT)
    assert answer["ok"] is True, answer
    browser.wait_js(f"{DIALOG}?.open", "finestra dell'invito")
    browser.js(f"{DIALOG}.querySelector('[data-invite-accept]').click()")
    browser.wait_js(f"{DIALOG}.dataset.inviteStatus === 'accepted'", "invito accettato")

    _network(browser, offline=True)
    friends["Giulia"].update("cancelled")  # il server ha annullato (Mario senza schede)
    browser.wait_js(f"{DIALOG}.dataset.inviteStatus === 'connection_lost'", "invito annullato nella finestra")
    note = browser.js(f"{DIALOG}.querySelector('[data-invite-note]').textContent")
    assert note == "La connessione è caduta: l'invito è stato annullato."
    _network(browser, offline=False)
    browser.wait_js(f"{DIALOG} === null && {READY}", "finestra chiusa e di nuovo collegato", timeout=30)
    # Mario è di nuovo libero: Giulia lo può invitare ancora
    friends["Giulia"].forget()
    answer = friends["Giulia"].client.call("invite:send", {
        "request_id": uuid.uuid4().hex, "user_id": users["Mario"], "mode": "1v1", "target_score": 150,
    }, timeout=WAIT)
    assert answer["ok"] is True, answer
    browser.wait_js(f"{DIALOG}?.dataset.inviteStatus === 'pending'", "nuovo invito ricevuto")
