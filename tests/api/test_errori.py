"""P7: log ed errori di base.

Prova le pagine 404 e 500 (HTML e JSON), il file di log con la rotazione, i valori
nascosti negli errori del database, gli errori degli eventi socket e che la password
di un login non finisca mai nel file di log.
I log di queste prove vanno in una cartella temporanea, mai in logs/.
Solo l'ultima prova usa MySQL (database dei test). Comando: python tests/esegui_tutti.py api
"""

import importlib.util
import logging
import re
import sys
from pathlib import Path

import pytest
import sqlalchemy as sa
from flask import request

from app import create_app, errors
from app.extensions import db, socketio
from app.logging_config import (
    LOG_BACKUP_COUNT,
    LOG_FILE_NAME,
    LOG_MAX_BYTES,
    SafeFormatter,
    remove_file_handlers,
)
from app.services import auth_service
from app.services.auth_service import LoginLimiter
from config import TestingConfig

BASE_DIR = Path(__file__).resolve().parents[2]
TEMPLATES = BASE_DIR / "app" / "templates" / "errors"
SECRET_DETAIL = "dettaglio-interno-7f3a"
PASSWORD = "Password-segreta-P7"
EMAIL = "prova.log@esempio.it"


def _file_handlers(app):
    return [h for h in app.logger.handlers if isinstance(h, logging.FileHandler)]


@pytest.fixture
def log_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(TestingConfig, "LOG_DIR", tmp_path)
    return tmp_path


@pytest.fixture
def app(log_dir):
    app = create_app("testing")
    app.config["PROPAGATE_EXCEPTIONS"] = False
    app.config["WTF_CSRF_ENABLED"] = False
    app.logger.setLevel("INFO")

    @app.route("/_prova/rotta")
    def broken():
        raise RuntimeError(SECRET_DETAIL)

    @app.route("/stats/_prova/rotta")
    def broken_json():
        raise RuntimeError(SECRET_DETAIL)

    yield app
    remove_file_handlers(app)


@pytest.fixture
def client(app):
    return app.test_client()


def log_text(log_dir):
    path = log_dir / LOG_FILE_NAME
    return path.read_text(encoding="utf-8") if path.exists() else ""


# Pagine 404


def test_pagina_inesistente_404(client):
    response = client.get("/pagina-che-non-esiste")
    assert response.status_code == 404
    page = response.get_data(as_text=True)
    assert 'data-error="404"' in page
    assert "Pagina non trovata" in page
    assert 'href="/"' in page


def test_404_json_nella_forma_del_contratto(client):
    for path in ("/stats/non-esiste", "/friends/non-esiste"):
        response = client.get(path)
        assert response.status_code == 404
        body = response.get_json()
        assert body["ok"] is False
        assert body["error"]["code"] == "not_found"
        assert body["error"]["message"]


def test_pagine_di_errore_senza_navbar(client):
    page = client.get("/pagina-che-non-esiste").get_data(as_text=True)
    assert 'data-part="navbar"' not in page
    assert 'name="csrf-token"' in page  # la struttura è quella di base.html


@pytest.mark.parametrize("name", ["404.html", "500.html"])
def test_pagine_di_errore_estendono_base_html(name):
    source = (TEMPLATES / name).read_text(encoding="utf-8")
    assert source.lstrip().startswith('{% extends "base.html" %}')
    assert "<script" not in source and "<style" not in source


# Pagine 500 e log


def test_errore_forzato_500_senza_dettagli_e_riga_error_nel_log(client, log_dir):
    response = client.get("/_prova/rotta")
    assert response.status_code == 500
    page = response.get_data(as_text=True)
    assert 'data-error="500"' in page
    assert "Errore del server" in page
    assert SECRET_DETAIL not in page
    assert "Traceback" not in page and "RuntimeError" not in page

    text = log_text(log_dir)
    assert re.search(r"^\S+ \S+ ERROR \[app\] Exception on /_prova/rotta \[GET\]", text, re.MULTILINE)
    assert "Traceback" in text and SECRET_DETAIL in text


def test_500_json_nella_forma_del_contratto(client):
    response = client.get("/stats/_prova/rotta")
    assert response.status_code == 500
    body = response.get_json()
    assert body["ok"] is False
    assert body["error"]["code"] == "server_error"
    assert SECRET_DETAIL not in response.get_data(as_text=True)


def test_500_minima_se_la_pagina_non_si_mostra(client, log_dir, monkeypatch):
    def broken_render(*_args, **_kwargs):
        raise RuntimeError("anche il template è rotto")

    monkeypatch.setattr(errors, "render_template", broken_render)
    response = client.get("/_prova/rotta")
    assert response.status_code == 500
    page = response.get_data(as_text=True)
    assert page == errors.MINIMAL_500
    assert SECRET_DETAIL not in page
    assert "Non riesco a mostrare la pagina 500" in log_text(log_dir)


def test_file_di_log_con_rotazione(app, log_dir):
    (handler,) = _file_handlers(app)
    assert Path(handler.baseFilename) == log_dir / LOG_FILE_NAME
    assert handler.maxBytes == LOG_MAX_BYTES == 1_000_000
    assert handler.backupCount == LOG_BACKUP_COUNT == 5


def test_rotazione_crea_i_file_vecchi(app, log_dir):
    (handler,) = _file_handlers(app)
    handler.maxBytes = 2000
    for i in range(200):
        app.logger.info("riga di prova numero %04d", i)
    files = sorted(p.name for p in log_dir.iterdir())
    assert files == [LOG_FILE_NAME] + [f"{LOG_FILE_NAME}.{n}" for n in range(1, 6)]


def test_livelli_distinti_nel_file(app, log_dir):
    logging.getLogger("app.prova").info("evento normale")
    logging.getLogger("app.prova").warning("anomalia")
    text = log_text(log_dir)
    assert " INFO [app.prova] evento normale" in text
    assert " WARNING [app.prova] anomalia" in text


def test_righe_delle_richieste_solo_sul_terminale(app, log_dir):
    web = logging.getLogger("werkzeug")
    web.info('127.0.0.1 - - "GET / HTTP/1.1" 200 -')
    web.warning("anomalia del server web")
    text = log_text(log_dir)
    assert "127.0.0.1" not in text
    assert " WARNING [werkzeug] anomalia del server web" in text


def test_i_test_non_scrivono_nella_cartella_logs_vera(monkeypatch):
    monkeypatch.setattr(TestingConfig, "LOG_DIR", BASE_DIR / "logs")
    app = create_app("testing")
    assert _file_handlers(app) == []


def test_una_seconda_create_app_non_raddoppia_il_file(app, log_dir):
    second = create_app("testing")
    try:
        assert len(_file_handlers(second)) == 1
        second.logger.warning("una volta sola")
        assert log_text(log_dir).count("una volta sola") == 1
    finally:
        remove_file_handlers(second)


def test_valori_degli_errori_del_database_nascosti():
    orig = Exception("(1062, \"Duplicate entry 'Mario' for key 'utenti.uq_utenti_nome'\")")
    exc = sa.exc.IntegrityError(
        "INSERT INTO utenti (nome_utente, email, password_hash) VALUES (%s, %s, %s)",
        ("Mario", EMAIL, "scrypt:hash-segreto"),
        orig,
    )
    try:
        raise exc
    except sa.exc.IntegrityError:
        record = logging.LogRecord("app.prova", logging.ERROR, __file__, 1, "Errore: %s", (exc,), sys.exc_info())
    text = SafeFormatter("%(message)s").format(record)
    assert "INSERT INTO utenti" in text
    assert "[parameters: nascosti nel log]" in text
    for value in ("Mario", EMAIL, "hash-segreto"):
        assert value not in text


# Eventi socket


def test_errori_socket_con_il_gestore_generale(app):
    assert socketio.default_exception_handler is errors._socket_error


def test_errore_socket_risponde_solo_server_error(app, log_dir):
    with app.test_request_context():
        request.event = {"message": "prova:evento", "args": ("testo di un utente",)}
        answer = errors._socket_error(RuntimeError(SECRET_DETAIL))
    assert answer == {"ok": False, "error": {"code": "server_error", "message": "Errore del server: riprova."}}
    text = log_text(log_dir)
    assert "ERROR [app.errors] Errore imprevisto nell'evento socket prova:evento" in text
    assert "testo di un utente" not in text


def test_errore_socket_nella_connessione_la_rifiuta(app):
    with app.test_request_context():
        request.event = {"message": "connect", "args": ()}
        assert errors._socket_error(RuntimeError("controllo rotto")) is False


# Password mai nel file di log (serve MySQL)


def _load_migrate():
    spec = importlib.util.spec_from_file_location("migrate", BASE_DIR / "scripts" / "migrate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_password_ed_email_mai_nel_file_di_log(app, client, log_dir, monkeypatch):
    app.logger.setLevel("DEBUG")
    monkeypatch.setattr(auth_service, "limiter", LoginLimiter())
    with app.app_context():
        url = db.engine.url
        assert url.database.endswith("_test")
        try:
            _load_migrate().migrate(url, report=lambda _msg: None)
            db.session.execute(sa.text("DELETE FROM utenti"))
            db.session.commit()
        except sa.exc.OperationalError:
            pytest.fail(f"Non riesco a usare il database {url.database}: MySQL è acceso?", pytrace=False)

    data = {"username": "ProvaLog", "email": EMAIL, "password": PASSWORD, "confirm": PASSWORD}
    assert client.post("/auth/register", data=data).status_code == 302
    client.post("/auth/logout")
    for _ in range(6):
        client.post("/auth/login", data={"username": "ProvaLog", "password": PASSWORD + "-sbagliata"})
    client.post("/auth/login", data={"username": "ProvaLog", "password": PASSWORD})

    text = log_text(log_dir)
    assert "Nuovo utente registrato" in text and "Login bloccato" in text
    for secret in (PASSWORD, EMAIL, "ProvaLog"):
        assert secret not in text

    with app.app_context():
        db.session.execute(sa.text("DELETE FROM utenti"))
        db.session.commit()
