"""Controlli all'avvio: versione di Python e versione di MySQL.

Tutti i membri del gruppo usano le stesse versioni (DECISIONI.md): se non
corrispondono, l'avvio si ferma con un messaggio chiaro invece di dare errori strani dopo.
"""

import re
import sys

import sqlalchemy as sa


class StartupCheckError(RuntimeError):
    """Un controllo di avvio non è passato: il messaggio dice cosa fare."""


def check_python(required, version_info=None):
    """Accetta solo la versione `required` (major, minor) di Python, con qualunque patch."""
    version = tuple(version_info or sys.version_info)[:3]
    if version[:2] != tuple(required):
        raise StartupCheckError(
            f"Serve Python {_dotted(required)}, ma questo è Python {_dotted(version)}. "
            f"Crea la .venv con: py -{_dotted(required)} -m venv .venv"
        )


def check_mysql_version(version_text, required):
    """Accetta solo MySQL `required` (major, minor): VERSION() dà testi come '8.0.39-log'."""
    match = re.match(r"(\d+)\.(\d+)\.", version_text or "")
    if not match or (int(match[1]), int(match[2])) != tuple(required):
        raise StartupCheckError(
            f"Serve MySQL {_dotted(required)}, ma il server risponde con la versione "
            f'"{version_text}". Installa MySQL {_dotted(required)} (vedi README.md).'
        )


def check_mysql(url, required):
    """Si collega al server MySQL (senza scegliere un database) e ne controlla la versione."""
    # url.set(database=None) non toglie il database: set() ignora i valori None.
    engine = sa.create_engine(url._replace(database=None))
    try:
        with engine.connect() as conn:
            version_text = conn.execute(sa.text("SELECT VERSION()")).scalar()
    except sa.exc.OperationalError as exc:
        code = exc.orig.args[0] if exc.orig is not None and exc.orig.args else "?"
        raise StartupCheckError(
            f"Non riesco a collegarmi a MySQL su {url.host}:{url.port} con l'utente "
            f'"{url.username}" (errore MySQL {code}). Controlla che MySQL sia avviato e '
            "che DB_HOST, DB_PORT, DB_USER e DB_PASSWORD nel file .env siano giusti."
        ) from None
    finally:
        engine.dispose()
    check_mysql_version(version_text, required)


def _dotted(parts):
    return ".".join(str(p) for p in parts)
