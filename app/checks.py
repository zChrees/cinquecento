"""Controlli all'avvio: versione di Python e versione di MySQL.

Tutti i membri del gruppo usano le stesse versioni (DECISIONI.md): se non
corrispondono, l'avvio si ferma con un messaggio chiaro invece di dare errori strani dopo.

Cosa contiene:
    StartupCheckError                      l'errore di un controllo non passato
    check_python((3, 14))                  ferma l'avvio se Python non è 3.14
    check_mysql_version("8.0.39", (8, 0))  ferma l'avvio se il testo non è MySQL 8.0
    check_mysql(url, (8, 0))               si collega a MySQL e ne controlla la versione
    _dotted((3, 14))                       "3.14": i numeri di una versione con i punti

DA DOVE ARRIVANO I DATI: check_python la chiama create_app() (app/__init__.py) con
REQUIRED_PYTHON di config.py; check_mysql la chiama run.py con l'indirizzo del
database e REQUIRED_MYSQL, presi dalla configurazione (config.py e .env).
"""

import re
import sys

import sqlalchemy as sa


# "class StartupCheckError(RuntimeError)": una classe nuova di errore che "eredita" da
# RuntimeError, cioè è un RuntimeError con un nome suo: chi la riceve sa che è un
# controllo di avvio (run.py la prende e stampa il messaggio).
class StartupCheckError(RuntimeError):
    """Un controllo di avvio non è passato: il messaggio dice cosa fare.

    In parole semplici:
        raise StartupCheckError("Serve Python 3.14, ma questo è Python 3.12.1. ...")
        run.py la prende, stampa il messaggio ed esce.
    """


def check_python(required, version_info=None):
    """Accetta solo la versione `required` (major, minor) di Python, con qualunque patch.

    In parole semplici:
        check_python(required, version_info)
        required:     la versione che serve, per esempio (3, 14), da REQUIRED_PYTHON
        version_info: facoltativo, la versione da controllare, per esempio
                      (3, 14, 4, "final", 0); se manca è quella di questo Python
                      (sys.version_info). I test la passano per provare altre versioni.
        Con 3.14.4 non dice niente; con 3.12.1 lancia StartupCheckError con il
        comando per rifare la .venv.
    """
    if version_info is None:
        version_info = sys.version_info
    # version: i primi tre numeri, per esempio (3, 14, 4) ([:3] prende gli elementi 0, 1 e 2)
    version = tuple(version_info)[:3]
    if version[:2] != tuple(required):
        raise StartupCheckError(
            f"Serve Python {_dotted(required)}, ma questo è Python {_dotted(version)}. "
            f"Crea la .venv con: py -{_dotted(required)} -m venv .venv"
        )


def check_mysql_version(version_text, required):
    """Accetta solo MySQL `required` (major, minor): VERSION() dà testi come '8.0.39-log'.

    In parole semplici:
        check_mysql_version(version_text, required)
        version_text: il testo di SELECT VERSION(), per esempio "8.0.39-log"
        required:     la versione che serve, per esempio (8, 0)
        Con "8.0.39-log" non dice niente; con "8.4.0", con un testo che non comincia
        con due numeri e un punto, o con None, lancia StartupCheckError.
    """
    # match: il risultato dell'espressione regolare, None se il testo non comincia con
    # "numero.numero."; match[1] e match[2] sono i due numeri trovati (come testi)
    text = version_text
    if not text:
        text = ""
    match = re.match(r"(\d+)\.(\d+)\.", text)
    if not match or (int(match[1]), int(match[2])) != tuple(required):
        raise StartupCheckError(
            f"Serve MySQL {_dotted(required)}, ma il server risponde con la versione "
            f'"{version_text}". Installa MySQL {_dotted(required)} (vedi README.md).'
        )


def check_mysql(url, required):
    """Si collega al server MySQL (senza scegliere un database) e ne controlla la versione.

    In parole semplici:
        check_mysql(url, required)
        url:      l'indirizzo del database di SQLAlchemy, con utente, password, host,
                  porta e nome (SQLALCHEMY_DATABASE_URI della configurazione)
        required: la versione che serve, per esempio (8, 0)
        Se il collegamento non riesce lancia StartupCheckError con quello che va
        controllato nel .env (senza la password); altrimenti controlla la versione
        con check_mysql_version.
    """
    # url.set(database=None) non toglie il database: set() ignora i valori None.
    engine = sa.create_engine(url._replace(database=None))
    # try/except/finally: si prova il blocco try; con un OperationalError (MySQL
    # spento, password sbagliata, ...) si esegue except; finally si esegue sempre,
    # anche dopo un errore, e chiude i collegamenti aperti.
    try:
        # with: il collegamento si chiude da solo alla fine del blocco
        with engine.connect() as conn:
            version_text = conn.execute(sa.text("SELECT VERSION()")).scalar()
    except sa.exc.OperationalError as exc:
        # code: il numero dell'errore di MySQL (per esempio 1045, accesso negato), "?" se manca
        code = "?"
        if exc.orig is not None and exc.orig.args:
            code = exc.orig.args[0]
        # from None: l'errore nuovo non si porta dietro quello di SQLAlchemy, così
        # chi avvia il server legge solo il nostro messaggio
        raise StartupCheckError(
            f"Non riesco a collegarmi a MySQL su {url.host}:{url.port} con l'utente "
            f'"{url.username}" (errore MySQL {code}). Controlla che MySQL sia avviato e '
            "che DB_HOST, DB_PORT, DB_USER e DB_PASSWORD nel file .env siano giusti."
        ) from None
    finally:
        engine.dispose()
    check_mysql_version(version_text, required)


def _dotted(parts):
    """I numeri di una versione separati da un punto.

    In parole semplici:
        _dotted(parts)
        Per esempio _dotted((3, 14)) = "3.14", _dotted((3, 12, 1)) = "3.12.1".
        Serve ai messaggi di check_python e check_mysql_version.
    """
    texts = []
    for part in parts:
        texts.append(str(part))
    return ".".join(texts)
