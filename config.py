"""Configurazioni dell'applicazione: sviluppo, test e demo.

I valori che cambiano da un PC all'altro (segreti, database, indirizzo) arrivano
dal file .env (modello in .env.example); tutto il resto è qui.
Le chiavi segnate "provvisorio, Dn" usano il valore consigliato per una domanda
ancora aperta in DA-DECIDERE.md: quando è decisa, si cambia solo il numero.

Questo file non importa niente del progetto (solo librerie): i test del runner lo
copiano da solo in un progetto finto. Il motore di gioco invece non lo importa mai
(P10): per questo i punteggi 150/300/500 stanno anche in app/game/engine/rules.py.

Cosa contiene:
    BASE_DIR                 la cartella del progetto
    ConfigError              l'errore di una configurazione mancante o sbagliata
    BaseConfig               i valori uguali per tutti, per esempio TURN_SECONDS = 15
    DevelopmentConfig        sviluppo (DEBUG acceso)
    TestingConfig            test (database cinquecento_test, porta 5099)
    DemoConfig               demo
    CONFIGS                  nome → classe, per esempio "testing" → TestingConfig
    load_config("testing")   la configurazione scelta, completata con il .env
    _value(env, "HOST", "127.0.0.1")   una variabile del .env, o il valore predefinito
    _required(env, "SECRET_KEY")       una variabile del .env che deve esserci
    _port(env, "PORT", 5000)           una porta del .env, controllata

DA DOVE ARRIVANO I DATI: dal file .env (letto qui sotto con load_dotenv) e dalle
variabili d'ambiente del sistema. load_config la chiamano create_app()
(app/__init__.py), gli script di scripts/ e i test; BaseConfig lo leggono anche
altri file per i loro numeri (per esempio app/blueprints/auth/forms.py).
"""

import os
from pathlib import Path
from typing import ClassVar

from dotenv import load_dotenv
from sqlalchemy.engine import URL

# __file__ è questo file; .resolve() il percorso completo; .parent la sua cartella
BASE_DIR = Path(__file__).resolve().parent

# Le variabili già impostate nel sistema hanno la precedenza sul file .env.
load_dotenv(BASE_DIR / ".env")

SECRET_KEY_MIN_LENGTH = 32
LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")


# Una classe di errore nuova che "eredita" da Exception: è un'eccezione con un nome
# suo, così chi la riceve (run.py, gli script) sa che è un problema di configurazione.
class ConfigError(Exception):
    """Configurazione mancante o non valida: l'avvio si ferma con questo messaggio.

    In parole semplici:
        raise ConfigError("Manca SECRET_KEY nel file .env: vedi .env.example.")
        run.py e gli script la prendono, stampano il messaggio ed escono.
    """


class BaseConfig:
    """I valori della configurazione uguali in sviluppo, test e demo.

    In parole semplici:
        BaseConfig.TURN_SECONDS   →  15
        Una classe usata come un elenco di valori con un nome (come una struct del C
        con i valori già scritti). app.config.from_object (app/__init__.py) copia
        nella configurazione di Flask tutti i nomi in maiuscolo. Le classi qui sotto
        "ereditano" questi valori e ne cambiano qualcuno.
    """

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
    # MySQL la chiuda per inattività. ClassVar[dict] dice (a ruff e all'editor) che
    # il dizionario è della classe, uguale per tutti, e non si cambia per ogni oggetto.
    SQLALCHEMY_ENGINE_OPTIONS: ClassVar[dict] = {"pool_pre_ping": True, "pool_recycle": 280}

    # Partita
    TARGET_SCORES = (150, 300, 500)
    TURN_SECONDS = 15  # P94: dal 04/10/2026, e il conto parte dopo le pause del tavolo (room.py)
    RECONNECT_SECONDS = 60
    TABLE_PHRASE_MIN_INTERVAL_SECONDS = 3  # frasi del tavolo: una ogni 3 secondi per giocatore (D24, P55)

    # Matchmaking (deciso, D16): intervallo di rating che si allarga col tempo.
    # P111 (05/10/2026, ok di Christian e Giuseppe): più veloce, prima era ±100, +50 ogni
    # 10 s, chiunque dopo 120 s (con 200 punti di differenza si aspettavano 20 s)
    MATCH_RANGE_START = 150
    MATCH_RANGE_STEP = 100
    MATCH_RANGE_STEP_SECONDS = 5
    MATCH_RANGE_MAX = 400
    MATCH_ANY_AFTER_SECONDS = 30

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

    # Log e backup (conservazione provvisoria, D10). La / tra due percorsi li unisce:
    # BASE_DIR / "logs" è la cartella logs dentro il progetto.
    LOG_DIR = BASE_DIR / "logs"
    BACKUP_DIR = BASE_DIR / "backups"
    BACKUP_RETENTION_DAYS = 14

    # Frontend React compilato (passo 1 della migrazione): None = app/static/dist.
    # Solo nei test si legge da SPA_DIST_DIR, la cartella fuori dal progetto dove
    # tests/conftest.py compila il frontend (app/blueprints/spa/routes.py, dist_dir).
    SPA_DIST_DIR = None


# Le tre configurazioni "ereditano" da BaseConfig (class X(BaseConfig)): hanno tutti i
# suoi valori, e cambiano solo quelli scritti qui.
class DevelopmentConfig(BaseConfig):
    """Sviluppo sul proprio PC: DEBUG acceso (errori dettagliati sul terminale)."""

    ENV_NAME = "development"
    DEBUG = True


class TestingConfig(BaseConfig):
    """I test: TESTING acceso; load_config sceglie database e porta dei test."""

    ENV_NAME = "testing"
    TESTING = True


class DemoConfig(BaseConfig):
    """La demo (dal 19/10/2026 non c'è più, la configurazione resta): come BaseConfig."""

    ENV_NAME = "demo"


# CONFIGS: il nome (quello di APP_ENV) → la classe, per esempio "testing" → TestingConfig.
# _config_class ha il trattino basso davanti: è solo la variabile del ciclo, non un nome
# da importare.
CONFIGS = {}
for _config_class in (DevelopmentConfig, TestingConfig, DemoConfig):
    CONFIGS[_config_class.ENV_NAME] = _config_class


def load_config(name=None, environ=None):
    """Restituisce la configurazione scelta, completata con i valori del .env.

    `name` è development, testing o demo (se manca: APP_ENV, poi development).
    Un valore mancante o non valido ferma l'avvio con ConfigError.

    In parole semplici:
        load_config(name, environ)
        name:    facoltativo, "development", "testing" o "demo"; se manca (o è vuoto)
                 si usa APP_ENV, e se manca anche quello "development".
        environ: facoltativo, le variabili da leggere al posto di quelle del sistema
                 (un dizionario, per esempio {"APP_ENV": "demo", "SECRET_KEY": ...});
                 lo passano i test. Se manca: os.environ, con dentro anche il .env.
        Crea un oggetto della classe scelta e ci aggiunge segreto, indirizzo e
        porta, l'indirizzo del database (SQLALCHEMY_DATABASE_URI) e il livello dei
        log. Nei test segreto, indirizzo, porta e database sono quelli dei test, e
        un database che non finisce con "_test" ferma tutto.

        Restituisce: l'oggetto della configurazione, che create_app passa a Flask.
    """
    env = environ
    if env is None:
        env = os.environ
    if not name:
        name = env.get("APP_ENV")
    if not name:
        name = "development"
    if name not in CONFIGS:
        raise ConfigError(f'APP_ENV="{name}" non valido: usa uno tra {", ".join(CONFIGS)}.')
    # CONFIGS[name] è una classe; con le parentesi se ne crea un oggetto
    config = CONFIGS[name]()

    if config.TESTING:
        # I test non usano segreti veri, e girano sempre in locale sulla porta 5099.
        config.SECRET_KEY = "chiave-dei-test-non-segreta"
        config.HOST = "127.0.0.1"
        config.PORT = 5099
        config.SPA_DIST_DIR = _value(env, "SPA_DIST_DIR", None)
        db_name = _value(env, "DB_NAME_TEST", "cinquecento_test")
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
        config.HOST = _value(env, "HOST", "127.0.0.1")
        config.PORT = _port(env, "PORT", 5000)
        db_name = _required(env, "DB_NAME")

    config.DB_NAME = db_name
    # URL.create: l'indirizzo del database nella forma di SQLAlchemy
    # (mysql+pymysql://utente:password@host:porta/database?charset=utf8mb4);
    # un utente o una password vuoti diventano None, cioè "non c'è"
    config.SQLALCHEMY_DATABASE_URI = URL.create(
        "mysql+pymysql",
        username=_value(env, "DB_USER", None),
        password=_value(env, "DB_PASSWORD", None),
        host=_value(env, "DB_HOST", "127.0.0.1"),
        port=_port(env, "DB_PORT", 3306),
        database=db_name,
        query={"charset": "utf8mb4"},
    )

    config.LOG_LEVEL = _value(env, "LOG_LEVEL", "INFO").upper()
    if config.LOG_LEVEL not in LOG_LEVELS:
        raise ConfigError(f"LOG_LEVEL non valido: usa uno tra {', '.join(LOG_LEVELS)}.")
    return config


def _value(env, key, default):
    """Una variabile del .env, oppure `default` se manca o è vuota.

    In parole semplici:
        _value(env, key, default)
        Per esempio _value(env, "HOST", "127.0.0.1") è "0.0.0.0" se il .env dice
        HOST=0.0.0.0, e "127.0.0.1" se HOST manca o è HOST= (vuoto). La usa
        load_config.
    """
    value = env.get(key)
    if not value:
        return default
    return value


def _required(env, key):
    """Una variabile del .env che deve esserci (e non essere vuota).

    In parole semplici:
        _required(env, key)
        Per esempio _required(env, "DB_NAME") è "cinquecento_dev"; se DB_NAME manca
        lancia ConfigError "Manca DB_NAME nel file .env: vedi .env.example.".
    """
    value = env.get(key)
    if not value:
        raise ConfigError(f"Manca {key} nel file .env: vedi .env.example.")
    return value


def _port(env, key, default):
    """Una porta del .env: un numero da 1 a 65535, oppure `default` se manca.

    In parole semplici:
        _port(env, key, default)
        Per esempio _port(env, "PORT", 5000) è 5000 se PORT manca, 8080 con
        PORT=8080; con PORT=abc o PORT=70000 lancia ConfigError.
    """
    raw = env.get(key)
    if not raw:
        return default
    if not raw.isdigit() or int(raw) < 1 or int(raw) > 65535:
        raise ConfigError(f'{key}="{raw}" non è una porta valida (un numero da 1 a 65535).')
    return int(raw)
