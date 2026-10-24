"""P4: l'applicazione si avvia, risponde con la pagina "ok" e rifiuta configurazioni e versioni sbagliate.

O1: la configurazione production (DEBUG spento, cookie di sessione solo in https se il
.env non dice altro, R8) e ProxyFix con TRUSTED_PROXIES.

Non serve MySQL: create_app() non si collega al database (il controllo di MySQL lo fa run.py).
Comando (finché P6 non aggiunge il runner): python -m pytest tests/api/test_avvio.py
"""

import pytest
from flask import request

from app import create_app
from app.checks import StartupCheckError, check_mysql, check_mysql_version, check_python
from app.extensions import socketio
from config import ConfigError, load_config

SECRET = "x" * 32


@pytest.fixture
def app():
    return create_app("testing")


def test_l_applicazione_risponde(app):
    # La rotta che la SPA chiama per prima, che non vuole né il build né MySQL
    response = app.test_client().get("/api/auth/session")
    assert response.status_code == 200
    assert response.get_json()["ok"] is True


def test_blueprint_registrati(app):
    assert set(app.blueprints) == {"main", "auth", "auth_api", "profile", "profile_api", "game", "stats", "friends", "spa"}


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


def test_controllo_mysql_si_collega_senza_database(monkeypatch):
    """Il controllo di avvio si collega al server, non al database: se il database
    non esiste ancora il messaggio deve parlare di MySQL, non di utente e password."""
    received = []

    class Stop(Exception):
        pass

    def fake_create_engine(url, **_options):
        received.append(url)
        raise Stop

    env = {"SECRET_KEY": SECRET, "DB_NAME": "cinquecento_dev", "DB_USER": "u", "DB_PASSWORD": "p@ss"}
    url = load_config("development", environ=env).SQLALCHEMY_DATABASE_URI
    monkeypatch.setattr("app.checks.sa.create_engine", fake_create_engine)
    with pytest.raises(Stop):
        check_mysql(url, (8, 0))
    assert received[0].database is None
    # Il resto dell'indirizzo resta quello del .env.
    assert (received[0].username, received[0].password, received[0].host) == ("u", "p@ss", url.host)
    assert (received[0].port, received[0].query) == (url.port, url.query)


# --- O1: produzione, cookie solo in https, proxy davanti ---------------------------------

PRODUCTION_ENV = {"SECRET_KEY": SECRET, "DB_NAME": "cinquecento"}


def test_produzione_senza_debug_e_con_il_cookie_solo_in_https():
    config = load_config("production", environ=PRODUCTION_ENV)
    assert (config.ENV_NAME, config.DEBUG, config.TESTING) == ("production", False, False)
    assert config.SESSION_COOKIE_SECURE is True
    assert config.TRUSTED_PROXIES == 0


def test_demo_non_esiste_piu():
    with pytest.raises(ConfigError, match="APP_ENV"):
        load_config(environ={**PRODUCTION_ENV, "APP_ENV": "demo"})


@pytest.mark.parametrize(("name", "value", "expected"), [
    ("production", "false", False),
    ("production", "FALSE", False),
    ("production", "", True),
    ("development", None, False),
    ("development", "true", True),
])
def test_cookie_solo_in_https_dal_env(name, value, expected):
    env = dict(PRODUCTION_ENV)
    if value is not None:
        env["SESSION_COOKIE_SECURE"] = value
    assert load_config(name, environ=env).SESSION_COOKIE_SECURE is expected


@pytest.mark.parametrize("value", ["si", "1", "yes", "vero"])
def test_cookie_solo_in_https_non_valido(value):
    with pytest.raises(ConfigError, match="SESSION_COOKIE_SECURE"):
        load_config("production", environ={**PRODUCTION_ENV, "SESSION_COOKIE_SECURE": value})


def test_nei_test_il_cookie_va_anche_in_http():
    config = load_config("testing", environ={"SESSION_COOKIE_SECURE": "true"})
    assert config.SESSION_COOKIE_SECURE is False


@pytest.mark.parametrize(("value", "expected"), [("", 0), ("0", 0), ("1", 1), ("5", 5)])
def test_proxy_davanti_dal_env(value, expected):
    config = load_config("production", environ={**PRODUCTION_ENV, "TRUSTED_PROXIES": value})
    assert config.TRUSTED_PROXIES == expected


@pytest.mark.parametrize("value", ["abc", "-1", "6", "1.5"])
def test_proxy_davanti_non_valido(value):
    with pytest.raises(ConfigError, match="TRUSTED_PROXIES"):
        load_config("production", environ={**PRODUCTION_ENV, "TRUSTED_PROXIES": value})


def _who_is_calling(app):
    """Una rotta di prova che risponde con quello che Flask vede: schema, indirizzo e nome."""

    def who():
        return f"{request.scheme} {request.remote_addr} {request.host}"

    app.add_url_rule("/prova-proxy", "prova_proxy", who)
    forwarded = {"X-Forwarded-For": "203.0.113.5", "X-Forwarded-Proto": "https",
                 "X-Forwarded-Host": "cinquecento.esempio.it"}
    return app.test_client().get("/prova-proxy", headers=forwarded).get_data(as_text=True)


def test_con_un_proxy_flask_vede_chi_si_collega(monkeypatch):
    monkeypatch.setenv("TRUSTED_PROXIES", "1")
    app = create_app("testing")
    assert _who_is_calling(app) == "https 203.0.113.5 cinquecento.esempio.it"


def test_senza_proxy_le_intestazioni_si_ignorano(monkeypatch):
    # Senza un proxy davanti, X-Forwarded-... le può scrivere chiunque: non contano
    monkeypatch.delenv("TRUSTED_PROXIES", raising=False)
    app = create_app("testing")
    assert _who_is_calling(app) == "http 127.0.0.1 localhost"
