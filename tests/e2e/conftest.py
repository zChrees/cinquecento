"""Suite e2e (P31): il programma vero, provato solo dall'esterno.

- Il server è un processo a parte, avviato come lo avvia un utente (`python run.py`),
  con APP_ENV=testing: porta 5099 e database cinquecento_test, svuotato e ricreato con
  migrate.py prima di partire. Alla fine il processo si ferma.
- I test non vedono la memoria del server: passano solo dagli ingressi veri.
  Registrazione e login dai moduli (con il codice CSRF), amici con le rotte HTTP,
  coda, inviti, chat e partite con Socket.IO, statistiche con GET /stats/me.
  Utenti, schede e aiuti per le partite sono in tests/e2e/helpers.py.
- Ogni test usa utenti nuovi (Utente01, Utente02, …), così rating, amicizie e code
  di un test non toccano quelli degli altri.
- I tempi del server sono quelli veri (30 s di turno, 60 s per rientrare): le scadenze
  le prova la suite sockets, che li può accorciare.
"""

import importlib.util
import itertools
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests
import sqlalchemy as sa

from config import load_config
from tests.e2e.helpers import WAIT, User

BASE_DIR = Path(__file__).resolve().parents[2]
START_WAIT = 30  # secondi massimi perché il server risponda dopo l'avvio


def _reset_database():
    url = load_config("testing").SQLALCHEMY_DATABASE_URI
    assert url.database.endswith("_test"), "i test usano solo un database che finisce con _test"
    engine = sa.create_engine(url)
    try:
        with engine.begin() as conn:
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
    finally:
        engine.dispose()
    spec = importlib.util.spec_from_file_location("migrate", BASE_DIR / "scripts" / "migrate.py")
    migrate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migrate)
    migrate.migrate(url, report=lambda _msg: None)


def _port_in_use(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(1)
        return probe.connect_ex((host, port)) == 0


def _wait_until_ready(process, url, output):
    deadline = time.monotonic() + START_WAIT
    while time.monotonic() < deadline:
        if process.poll() is not None:
            pytest.exit(f"Il server dei test si è fermato all'avvio:\n{output.read_text(encoding='utf-8')}",
                        returncode=1)
        try:
            if requests.get(f"{url}/auth/login", timeout=1).status_code == 200:
                return
        except requests.ConnectionError:
            pass
        time.sleep(0.1)  # il server non avvisa quando è pronto: si riprova finché risponde
    pytest.exit(f"Il server dei test non risponde dopo {START_WAIT} secondi.", returncode=1)


@pytest.fixture(scope="session")
def server(tmp_path_factory):
    config = load_config("testing")
    if _port_in_use(config.HOST, config.PORT):
        pytest.exit(f"La porta {config.PORT} è occupata: chiudi il server che la usa.", returncode=2)
    _reset_database()
    output = tmp_path_factory.mktemp("server") / "server.log"
    env = {**os.environ, "APP_ENV": "testing", "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}
    with output.open("wb") as sink:
        process = subprocess.Popen([sys.executable, "run.py"], cwd=BASE_DIR, env=env,
                                   stdout=sink, stderr=subprocess.STDOUT)
    url = f"http://{config.HOST}:{config.PORT}"
    try:
        _wait_until_ready(process, url, output)
        yield {"url": url, "output": output}
    finally:
        process.terminate()
        try:
            process.wait(WAIT)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(WAIT)


_numbers = itertools.count(1)  # un nome nuovo per ogni utente della sessione


@pytest.fixture
def users(server):
    """users(2) → due utenti nuovi, con il login; alla fine le loro schede si chiudono."""
    created = []

    def _users(count):
        new = [User(server["url"], f"Utente{next(_numbers):02d}") for _ in range(count)]
        created.extend(new)
        return new

    yield _users
    for user in created:
        user.close()
