"""P4: l'applicazione si avvia, risponde con la pagina "ok" e rifiuta configurazioni e versioni sbagliate.

Non serve MySQL: create_app() non si collega al database (il controllo di MySQL lo fa run.py).
Comando (finché P6 non aggiunge il runner): python -m pytest tests/api/test_avvio.py
"""

import pytest

from app import create_app
from app.checks import StartupCheckError, check_mysql_version, check_python
from app.extensions import socketio
from config import ConfigError, load_config

SECRET = "x" * 32


@pytest.fixture
def app():
    return create_app("testing")


def test_home_mostra_ok(app):
    response = app.test_client().get("/")
    assert response.status_code == 200
    assert b'data-stato="ok"' in response.data


def test_blueprint_registrati(app):
    assert set(app.blueprints) == {"main", "auth", "profile", "game", "stats", "friends"}


def test_socketio_in_modalita_threading(app):
    assert socketio.server.eio.async_mode == "threading"


def test_punteggi_ammessi():
    assert load_config("testing", environ={}).TARGET_SCORES == (150, 300, 500)


def test_configurazione_di_test():
    config = load_config("testing", environ={})
    assert config.PORT == 5099
    assert config.DB_NAME == "cinquecento_test"
    assert config.SQLALCHEMY_DATABASE_URI.database == "cinquecento_test"


@pytest.mark.parametrize("version", [(3, 14, 0), (3, 14, 4), (3, 14, 9)])
def test_python_314_accettato(version):
    check_python((3, 14), version_info=version)


@pytest.mark.parametrize("version", [(3, 13, 7), (3, 15, 0), (2, 7, 18)])
def test_python_diverso_rifiutato(version):
    with pytest.raises(StartupCheckError, match="Serve Python 3.14"):
        check_python((3, 14), version_info=version)


@pytest.mark.parametrize("text", ["8.0.39", "8.0.43-log", "8.0.0"])
def test_mysql_80_accettato(text):
    check_mysql_version(text, (8, 0))


@pytest.mark.parametrize("text", ["8.4.2", "5.7.44", "9.1.0", "10.11.6-MariaDB", "", None, "boh"])
def test_mysql_diverso_rifiutato(text):
    with pytest.raises(StartupCheckError, match="Serve MySQL 8.0"):
        check_mysql_version(text, (8, 0))


def test_database_di_test_deve_finire_con_test():
    with pytest.raises(ConfigError, match="_test"):
        load_config("testing", environ={"DB_NAME_TEST": "cinquecento_dev"})


def test_manca_secret_key():
    with pytest.raises(ConfigError, match="Manca SECRET_KEY"):
        load_config("development", environ={"DB_NAME": "cinquecento_dev"})


def test_secret_key_troppo_corta():
    with pytest.raises(ConfigError, match="troppo corta"):
        load_config("development", environ={"SECRET_KEY": "corta", "DB_NAME": "cinquecento_dev"})


def test_ambiente_sconosciuto():
    with pytest.raises(ConfigError, match="APP_ENV"):
        load_config(environ={"APP_ENV": "produzione"})


@pytest.mark.parametrize("port", ["abc", "0", "70000", "-1"])
def test_porta_non_valida(port):
    env = {"SECRET_KEY": SECRET, "DB_NAME": "cinquecento_dev", "PORT": port}
    with pytest.raises(ConfigError, match="porta valida"):
        load_config("development", environ=env)


def test_livello_log_non_valido():
    env = {"SECRET_KEY": SECRET, "DB_NAME": "cinquecento_dev", "LOG_LEVEL": "TUTTO"}
    with pytest.raises(ConfigError, match="LOG_LEVEL"):
        load_config("development", environ=env)


def test_sviluppo_con_env_completo():
    env = {"SECRET_KEY": SECRET, "DB_NAME": "cinquecento_dev", "DB_USER": "u", "DB_PASSWORD": "p@ss:/word"}
    config = load_config("development", environ=env)
    assert (config.HOST, config.PORT, config.DEBUG) == ("127.0.0.1", 5000, True)
    # Una password con caratteri speciali non rompe l'indirizzo del database.
    assert config.SQLALCHEMY_DATABASE_URI.password == "p@ss:/word"
    assert config.SQLALCHEMY_DATABASE_URI.query["charset"] == "utf8mb4"
