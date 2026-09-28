"""Suite sockets: un server vero sulla porta dei test (5099) e client Socket.IO simulati.

- Il database dei test viene svuotato e ricreato con migrate.py; poi si creano gli
  utenti di prova. Serve MySQL con scripts/setup_db.sql già lanciato.
- Il server gira in un thread di questo processo: i test vedono lo stesso
  RoomManager del server (app.realtime.room_manager.rooms).
- Eventi "test:*" di prova, registrati SOLO qui: mettono alla prova stanze, canali
  e lock senza aspettare la partita vera (P24).
"""

import importlib.util
import re
import threading
import time
from pathlib import Path

import pytest
import requests
import socketio as sio_client
import sqlalchemy as sa
import websocket
from flask_login import current_user
from flask_socketio import join_room
from werkzeug.serving import make_server

from app import create_app
from app.extensions import db, socketio
from app.realtime.events import EventError, handler, user_channel
from app.realtime.room_manager import rooms
from app.services import auth_service

BASE_DIR = Path(__file__).resolve().parents[2]
PASSWORD = "Password-di-prova-1"
USERS = ("Primo", "Secondo", "Terzo")
WAIT = 5  # secondi massimi per aspettare un evento (si aspetta l'evento, non un tempo fisso)


# Il server di sviluppo (Werkzeug) non risponde alla chiusura ordinata del websocket,
# e websocket-client la aspetta fino a 3 secondi per ogni client. Nei test basta molto
# meno: il server vede lo scollegamento lo stesso. Il browser non aspetta questa risposta.
_ws_close = websocket.WebSocket.close


def _quick_close(self, status=websocket.STATUS_NORMAL, reason=b"", timeout=0.1):
    return _ws_close(self, status, reason, timeout)


websocket.WebSocket.close = _quick_close


def _load_migrate():
    spec = importlib.util.spec_from_file_location("migrate", BASE_DIR / "scripts" / "migrate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _reset_database(app):
    with app.app_context():
        url = db.engine.url
        assert url.database.endswith("_test"), "i test usano solo un database che finisce con _test"
        try:
            with db.engine.begin() as conn:
                tables = conn.execute(sa.text(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE()"
                )).scalars().all()
                conn.execute(sa.text("SET FOREIGN_KEY_CHECKS = 0"))
                for table in tables:
                    conn.execute(sa.text(f"DROP TABLE `{table}`"))
                conn.execute(sa.text("SET FOREIGN_KEY_CHECKS = 1"))
        except sa.exc.OperationalError as exc:
            code = exc.orig.args[0] if exc.orig is not None and exc.orig.args else "?"
            pytest.exit(
                f"Non riesco a usare il database {url.database} (errore MySQL {code}): "
                "MySQL è acceso? scripts/setup_db.sql è stato lanciato?",
                returncode=1,
            )
        _load_migrate().migrate(url, report=lambda _msg: None)
        return {name: auth_service.register(name, f"{name.lower()}@esempio.it", PASSWORD).id for name in USERS}


class LockProbe:
    """Conta quanti eventi sono dentro il lock della stanza nello stesso momento."""

    def __init__(self):
        self._guard = threading.Lock()
        self.reset()

    def reset(self):
        self.entered = self.max_entered = self.inside = self.max_inside = self.counter = 0

    def enter(self):
        with self._guard:
            self.entered += 1
            self.max_entered = max(self.max_entered, self.entered)

    def leave(self):
        with self._guard:
            self.entered -= 1

    def critical(self):
        """Lettura, attesa e scrittura: senza lock due eventi si pesterebbero i piedi."""
        with self._guard:
            self.inside += 1
            self.max_inside = max(self.max_inside, self.inside)
        value = self.counter
        time.sleep(0.005)
        self.counter = value + 1
        with self._guard:
            self.inside -= 1
        return self.counter


def _register_test_events(probe):
    def room_or_error(data):
        room = rooms.get(data.get("room_id") if isinstance(data, dict) else None)
        if room is None:
            raise EventError("not_found")
        return room

    @handler
    def test_join(data):
        room = room_or_error(data)
        room.add_member(current_user.id)
        join_room(room.channel)

    @handler
    def test_shout(data):
        room = room_or_error(data)
        room.run(lambda: socketio.emit("test:shouted", {"text": data.get("text")}, to=room.channel))

    @handler
    def test_ping_user(data):
        socketio.emit("test:ping", {}, to=user_channel(data["user_id"]))

    @handler
    def test_increment(data):
        room = room_or_error(data)
        probe.enter()
        try:
            return {"counter": room.run(probe.critical)}
        finally:
            probe.leave()

    @handler
    def test_fail(_data):
        raise RuntimeError("errore di prova")

    for name, fn in (("test:join", test_join), ("test:shout", test_shout), ("test:ping_user", test_ping_user),
                     ("test:increment", test_increment), ("test:fail", test_fail)):
        socketio.on_event(name, fn)


@pytest.fixture(scope="session")
def server():
    app = create_app("testing")
    user_ids = _reset_database(app)
    probe = LockProbe()
    _register_test_events(probe)
    http = make_server(app.config["HOST"], app.config["PORT"], app, threaded=True)
    thread = threading.Thread(target=http.serve_forever, daemon=True)
    thread.start()
    yield {
        "url": f"http://{app.config['HOST']}:{app.config['PORT']}",
        "user_ids": user_ids,
        "probe": probe,
    }
    http.shutdown()
    thread.join(WAIT)


def login_cookie(base_url, username, password=PASSWORD):
    """Fa il login come farebbe il browser (con il codice CSRF) e restituisce il cookie di sessione."""
    session = requests.Session()
    page = session.get(f"{base_url}/auth/login", timeout=WAIT).text
    token = re.search(r'name="csrf_token" type="hidden" value="([^"]+)"', page)[1]
    response = session.post(
        f"{base_url}/auth/login",
        data={"csrf_token": token, "username": username, "password": password},
        allow_redirects=False, timeout=WAIT,
    )
    assert response.status_code == 302, "login di prova non riuscito"
    return "; ".join(f"{k}={v}" for k, v in session.cookies.items())


@pytest.fixture
def connect(server):
    """connect("Primo") → client Socket.IO collegato con il login di quell'utente.

    `before(client)`, se c'è, si chiama prima del collegamento: serve per ascoltare gli
    eventi che il server manda appena la scheda si collega (P28: queue:status).
    """
    clients = []

    def _connect(username=None, transports=("websocket",), before=None):
        client = sio_client.Client(reconnection=False)
        headers = {"Cookie": login_cookie(server["url"], username)} if username else {}
        if before is not None:
            before(client)
        clients.append(client)
        client.connect(server["url"], headers=headers, transports=list(transports), wait_timeout=WAIT)
        return client

    yield _connect
    for client in clients:
        if client.connected:
            client.disconnect()


@pytest.fixture
def room():
    """Una stanza nuova, tolta alla fine della prova."""
    new = rooms.create()
    yield new
    rooms.remove(new.id)


class Inbox:
    """Raccoglie gli eventi di un nome arrivati a un client; `wait` aspetta il primo."""

    def __init__(self, client, event):
        self.items = []
        self._arrived = threading.Event()

        def receive(data):
            self.items.append(data)
            self._arrived.set()

        client.on(event, receive)

    def wait(self, timeout=WAIT):
        return self._arrived.wait(timeout)


@pytest.fixture
def inbox():
    """inbox(client, "evento") → raccoglitore di quell'evento per quel client."""
    return Inbox
