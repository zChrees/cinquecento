"""Configurazioni dell'applicazione: sviluppo, test e demo.

I valori che cambiano da un PC all'altro (segreti, database, indirizzo) arrivano
dal file .env (modello in .env.example); tutto il resto è qui.
Le chiavi segnate "provvisorio, Dn" usano il valore consigliato per una domanda
ancora aperta in DA-DECIDERE.md: quando è decisa, si cambia solo il numero.
"""

import os
from pathlib import Path
from typing import ClassVar

from dotenv import load_dotenv
from sqlalchemy.engine import URL

BASE_DIR = Path(__file__).resolve().parent

# Le variabili già impostate nel sistema hanno la precedenza sul file .env.
load_dotenv(BASE_DIR / ".env")

SECRET_KEY_MIN_LENGTH = 32
LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")


class ConfigError(Exception):
    """Configurazione mancante o non valida: l'avvio si ferma con questo messaggio."""


class BaseConfig:
    ENV_NAME = ""
    DEBUG = False
    TESTING = False

    # Versioni richieste, controllate all'avvio da app/checks.py
    REQUIRED_PYTHON = (3, 14)
    REQUIRED_MYSQL = (8, 0)

    # Server: in tutte le installazioni gira il server di Werkzeug, in un solo
    # processo (meno di 50 utenti, vedi DECISIONI.md). Flask-SocketIO lo accetta
    # fuori da un terminale solo con questa opzione.
    ALLOW_UNSAFE_WERKZEUG = True

    # Cookie di sessione
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # Database: controlla la connessione prima di usarla e la rinnova prima che
    # MySQL la chiuda per inattività
    SQLALCHEMY_ENGINE_OPTIONS: ClassVar[dict] = {"pool_pre_ping": True, "pool_recycle": 280}

    # Partita
    TARGET_SCORES = (150, 300, 500)
    TURN_SECONDS = 30
    RECONNECT_SECONDS = 60
    TABLE_PHRASE_MIN_INTERVAL_SECONDS = 3  # frasi del tavolo: una ogni 3 secondi per giocatore (D24, P55)

    # Matchmaking (deciso, D16): intervallo di rating che si allarga col tempo
    MATCH_RANGE_START = 100
    MATCH_RANGE_STEP = 50
    MATCH_RANGE_STEP_SECONDS = 10
    MATCH_RANGE_MAX = 400
    MATCH_ANY_AFTER_SECONDS = 120

    # Rating Glicko-2: valore iniziale e partite "provvisorie" per modalità decisi (D9)
    RATING_INITIAL = 1500
    RATING_RD_INITIAL = 350
    RATING_VOLATILITY_INITIAL = 0.06
    GLICKO_TAU = 0.5
    RATING_PROVISIONAL_GAMES = 10

    # Account: nome utente deciso (D7), password provvisoria (D8); tentativi di login (P16)
    USERNAME_MIN = 3
    USERNAME_MAX = 20
    PASSWORD_MIN = 8
    LOGIN_MAX_ATTEMPTS = 5
    LOGIN_LOCK_SECONDS = 300

    # Amici, chat e inviti: limiti decisi (D26), scadenza degli inviti decisa (D27).
    # I messaggi tra amici non si cancellano mai (D24): niente giorni di conservazione.
    FRIENDS_MAX = 100
    CHAT_MAX_LENGTH = 1000
    CHAT_MIN_INTERVAL_SECONDS = 1
    INVITE_SECONDS = 60

    # Eventi in tempo reale (P32): per ogni scheda fino a EVENT_BURST eventi di fila, poi
    # EVENT_RATE_PER_SECOND al secondo; oltre, too_fast con retry_after. Una persona
    # che gioca non ci arriva mai.
    EVENT_BURST = 20
    EVENT_RATE_PER_SECOND = 10

    # Log e backup (conservazione provvisoria, D10)
    LOG_DIR = BASE_DIR / "logs"
    BACKUP_DIR = BASE_DIR / "backups"
    BACKUP_RETENTION_DAYS = 14


class DevelopmentConfig(BaseConfig):
    ENV_NAME = "development"
    DEBUG = True


class TestingConfig(BaseConfig):
    ENV_NAME = "testing"
    TESTING = True


class DemoConfig(BaseConfig):
    ENV_NAME = "demo"


CONFIGS = {c.ENV_NAME: c for c in (DevelopmentConfig, TestingConfig, DemoConfig)}


def load_config(name=None, environ=None):
    """Restituisce la configurazione scelta, completata con i valori del .env.

    `name` è development, testing o demo (se manca: APP_ENV, poi development).
    Un valore mancante o non valido ferma l'avvio con ConfigError.
    """
    env = os.environ if environ is None else environ
    name = name or env.get("APP_ENV") or "development"
    if name not in CONFIGS:
        raise ConfigError(f'APP_ENV="{name}" non valido: usa uno tra {", ".join(CONFIGS)}.')
    config = CONFIGS[name]()

    if config.TESTING:
        # I test non usano segreti veri, e girano sempre in locale sulla porta 5099.
        config.SECRET_KEY = "chiave-dei-test-non-segreta"
        config.HOST = "127.0.0.1"
        config.PORT = 5099
        db_name = env.get("DB_NAME_TEST") or "cinquecento_test"
        if not db_name.endswith("_test"):
            raise ConfigError(
                f'DB_NAME_TEST="{db_name}" non finisce con "_test": '
                "i test si rifiutano di usare un database che non è di test."
            )
    else:
        config.SECRET_KEY = _required(env, "SECRET_KEY")
        if len(config.SECRET_KEY) < SECRET_KEY_MIN_LENGTH:
            raise ConfigError(
                f"SECRET_KEY nel file .env è troppo corta (servono almeno "
                f"{SECRET_KEY_MIN_LENGTH} caratteri): generane una come spiegato in .env.example."
            )
        config.HOST = env.get("HOST") or "127.0.0.1"
        config.PORT = _port(env, "PORT", 5000)
        db_name = _required(env, "DB_NAME")

    config.DB_NAME = db_name
    config.SQLALCHEMY_DATABASE_URI = URL.create(
        "mysql+pymysql",
        username=env.get("DB_USER") or None,
        password=env.get("DB_PASSWORD") or None,
        host=env.get("DB_HOST") or "127.0.0.1",
        port=_port(env, "DB_PORT", 3306),
        database=db_name,
        query={"charset": "utf8mb4"},
    )

    config.LOG_LEVEL = (env.get("LOG_LEVEL") or "INFO").upper()
    if config.LOG_LEVEL not in LOG_LEVELS:
        raise ConfigError(f"LOG_LEVEL non valido: usa uno tra {', '.join(LOG_LEVELS)}.")
    return config


def _required(env, key):
    value = env.get(key)
    if not value:
        raise ConfigError(f"Manca {key} nel file .env: vedi .env.example.")
    return value


def _port(env, key, default):
    raw = env.get(key)
    if not raw:
        return default
    if not raw.isdigit() or not 1 <= int(raw) <= 65535:
        raise ConfigError(f'{key}="{raw}" non è una porta valida (un numero da 1 a 65535).')
    return int(raw)
