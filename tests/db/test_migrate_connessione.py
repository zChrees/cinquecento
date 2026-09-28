"""migrate.py: se non riesce a collegarsi a MySQL esce con il suo messaggio in italiano, senza traceback.

Si usa solo la configurazione dei test (APP_ENV=testing, impostato da conftest.py):
nessuna migrazione viene applicata. Il caso "password sbagliata" vuole MySQL acceso.
"""

import importlib.util
import socket
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parents[2]


def _load_migrate():
    spec = importlib.util.spec_from_file_location("migrate", BASE_DIR / "scripts" / "migrate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


migrate = _load_migrate()


def _closed_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return str(s.getsockname()[1])


@pytest.mark.parametrize(("variable", "value", "code"), [
    ("DB_PASSWORD", "password-sbagliata", "1045"),   # MySQL rifiuta utente o password
    ("DB_PORT", _closed_port(), "2003"),             # nessun MySQL su quella porta
])
def test_connessione_rifiutata_messaggio_chiaro(monkeypatch, capsys, variable, value, code):
    monkeypatch.setenv(variable, value)
    assert migrate.main([]) == 1
    err = capsys.readouterr().err
    assert err.startswith("Migrazione annullata: non riesco a collegarmi a MySQL")
    assert f"errore MySQL {code}" in err
    assert "Traceback" not in err
    assert "password-sbagliata" not in err
